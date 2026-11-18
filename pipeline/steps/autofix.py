"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict

import yaml

from ..common import ERROR, parse_yolo_line


def fix(ds, issues, cfg):
    errors = [issue for issue in issues if issue.severity == ERROR]
    changes = []

    def record(image, line, action, before, after):
        changes.append(dict(image=image, line=line, action=action, before=before, after=after))

    remove_codes = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}
    removed = {issue.image for issue in errors
               if issue.code in remove_codes or issue.code.startswith("DUP_IMAGE_")}
    for stem in sorted(removed):
        paths = [path for path in ds.image_files() if path.stem == stem]
        label_path = ds.label_path(stem)
        if label_path.exists():
            paths.append(label_path)
        if paths:
            before = ", ".join(str(path.relative_to(ds.root)) for path in paths)
            for path in paths:
                path.unlink()
            record(stem, None, "remove_image", before, "")

    if any(issue.code == "BAD_CLASS_NAME" for issue in errors):
        data = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) if ds.yaml_path.exists() else {}
        data = data or {}
        if data.get("names") != cfg["classes"]:
            before = str(data.get("names", {}))
            data["names"] = list(cfg["classes"])
            ds.yaml_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
            record("data.yaml", None, "rename_classes", before, str(data["names"]))

    by_image = defaultdict(lambda: defaultdict(set))
    missing = set()
    drop_codes = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
    for issue in errors:
        if issue.image in removed:
            continue
        if issue.code == "MISSING_LABEL_FILE":
            if issue.image not in missing and not ds.label_path(issue.image).exists():
                record(issue.image, None, "needs_label", "(không có file)", "chuyển người gán")
                missing.add(issue.image)
        elif issue.line is not None and issue.code in drop_codes | {"BOX_OUT_OF_IMAGE"}:
            by_image[issue.image][issue.line].add(issue.code)

    for stem, line_codes in by_image.items():
        path = ds.label_path(stem)
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        output = []
        changed = False
        for number, text in enumerate(lines, 1):
            codes = line_codes.get(number, set())
            after = text
            action = None
            if codes & drop_codes:
                action, after = "drop_line", ""
            elif "BOX_OUT_OF_IMAGE" in codes:
                try:
                    cls, x, y, w, h = parse_yolo_line(text)
                except (ValueError, OverflowError):
                    action, after = "drop_line", ""
                else:
                    left, top = max(0.0, x - w / 2), max(0.0, y - h / 2)
                    right, bottom = min(1.0, x + w / 2), min(1.0, y + h / 2)
                    if right <= left or bottom <= top:
                        action, after = "drop_line", ""
                    elif (left, top, right, bottom) != (x - w / 2, y - h / 2, x + w / 2, y + h / 2):
                        values = ((left + right) / 2, (top + bottom) / 2, right - left, bottom - top)
                        after = f"{cls} " + " ".join(format(value, ".12g") for value in values)
                        action = "clip_box"
            if action:
                record(stem, number, action, text, after)
                changed = True
            if action != "drop_line":
                output.append(after)
        if changed:
            path.write_text("\n".join(output) + ("\n" if output else ""), encoding="utf-8")
    return changes
