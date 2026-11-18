# Báo cáo Day 09 — Ngô Trí Anh, 2A202604053

## 1. Kết luận trước

**Hold**. Pipeline nhận 205/224 ảnh, loại 19/224 ảnh ở cửa vào và xuất bản nháp 205 ảnh vào `submission/export/clean_v1/`. Sau sửa tự động và duyệt mô phỏng 80 ảnh, còn 0 lỗi bắt buộc, nhưng 38/205 ảnh (18,54%) còn cảnh báo chưa duyệt, vượt ngưỡng giữ 10%. Số liệu lấy từ `submission/reports/01_intake.csv` và `08_summary.json`.

## 2. Lỗi và phân việc

Bảng lấy từ `02_error_list_v1.csv`. Mẫu số của lỗi cửa vào là 224 ảnh, của QC là 205 ảnh đã nhận. Số dòng/cảnh báo là số issue, có thể cùng nằm trên một ảnh.

| Mã lỗi | Số issue / số ảnh | Ai xử lý và lý do |
|---|---:|---|
| CORRUPT_IMAGE | 2 / 2 | Máy loại ảnh không đọc được |
| BAD_SIZE | 3 / 3 | Máy loại ảnh dưới kích thước quy định |
| DUP_IMAGE_EXACT | 8 / 8 | Máy loại bản trùng byte |
| DUP_IMAGE_NEAR | 2 / 2 | Máy loại bản gần trùng theo pHash |
| LEAK_TEST | 4 / 4 | Máy loại ảnh trùng kho test/val |
| BAD_CLASS_NAME | 2 / 1 file YAML | Máy chuẩn hoá tên lớp |
| BAD_CLASS_ID | 6 dòng / 6 | Máy xoá dòng có ID ngoài danh sách |
| BAD_FORMAT | 3 dòng / 3 | Máy xoá dòng sai định dạng |
| BOX_ZERO | 4 dòng / 4 | Máy xoá box không có diện tích |
| DUP_BOX | 7 dòng / 7 | Máy xoá box lặp |
| BOX_OUT_OF_IMAGE | 8 dòng / 8 | Máy cắt box vào biên ảnh |
| MISSING_LABEL_FILE | 6 / 6 | Người gán nhãn, máy ghi needs_label |
| BOX_TINY | 6 dòng / 4 | Người xem vật nhỏ có cần giữ |
| BOX_HUGE | 3 dòng / 3 | Người xem box lớn có hợp lý |
| EMPTY_LABEL | 12 / 12 | Người xác nhận ảnh nền hoặc thiếu nhãn |
| CLASS_RARE | 4 / mức dataset | Người đánh giá phân bố lớp |
| POSSIBLE_FALSE_POS | 29 dòng / 27 | Người xác nhận box có vật thật |
| POSSIBLE_LOOSE_BOX | 28 / 24 | Người kiểm độ khít của box |
| POSSIBLE_MISSING | 53 / 52 | Người kiểm vật bị thiếu box |
| POSSIBLE_WRONG_CLASS | 18 / 18 | Người kiểm ý nghĩa lớp |

`03_fixes.csv` ghi 35 hành động gồm 20 drop_line, 8 clip_box, 1 rename_classes và 6 needs_label. Hàng đợi có 125 ảnh, ưu tiên bằng tổng trọng số lỗi, nhân thêm (1 + conf) cho cảnh báo có confidence và cộng điểm sửa box. `img_0020` đứng đầu với 11,524 điểm do vừa xoá dòng vừa có cảnh báo thiếu box/sai lớp. Tiếp theo là 6 ảnh thiếu file nhãn, mỗi ảnh 10 điểm. Người duyệt mô phỏng xem 80/125 ảnh, bao phủ 94/123 cảnh báo ngữ nghĩa ở 74/103 ảnh có cảnh báo ngữ nghĩa trong v2. Đây là số cảnh báo được xem, chưa phải số lỗi thật được xác nhận.

## 3. Calibration (2 ngưỡng)

Đã sweep 9 ngưỡng pHash và 7 ngưỡng confidence trên 39 ảnh. Chi tiết TP/FP/FN trong `submission/calibration/calibration.json` và `calibration_report.md`. P/R là precision/recall trên calib.

| Tham số | Khởi đầu → chọn | P/R trước → sau | Đánh đổi |
|---|---|---|---|
| duplicates.phash_dist | 2 → 4 | Gần trùng 1,00/0,50 → 1,00/0,667 (TP 3/6 → 4/6, FP 0). Trùng byte giữ 3/3, FP 0. | Giá trị nhỏ nhất bắt thêm một ca, 6–14 không cải thiện. Ưu tiên độ tin cậy vì ảnh bị cờ sẽ bị loại. |
| second_opinion.conf | 0,25 → 0,6 | Sai lớp 0,556/0,833 → 0,625/0,833. Thiếu box 0,50/1,00 → 0,571/1,00. Box lỏng 0,286/0,40 → 0,20/0,20. | Giữ TP sai lớp 5/6 và thiếu box 8/8, giảm FP tương ứng 4 → 3 và 8 → 6. Chấp nhận TP box lỏng giảm 2/5 → 1/5. |

FALSE_POS giữ TP 5/5, FP 11 vì dùng fp_conf cố định. Ngưỡng conf 0,7–0,8 giảm recall thiếu box. Sau calibration, ảnh còn cảnh báo giảm từ 60/205 (29,27%) xuống 38/205 (18,54%), kết luận vẫn Hold.

Calib nhỏ có thể gây chọn sai ngưỡng. pHash 16 bắt 5/6 ca gần trùng với FP 0 trên calib, nhưng trên raw báo 7 gần trùng và 11 rò rỉ, so với 2 và 4 ở ngưỡng 4. Kiểm tra trực quan cặp img_0011/img_0008, khoảng cách 16, cho thấy cảnh tennis và trượt tuyết khác nhau. Hai cặp ở ngưỡng 4, img_0076/img_0042 và img_0143/img_0037, có cùng cảnh. Vì vậy chọn 4 dù bỏ sót 2/6 ca gần trùng trên calib.

## 4. Cửa chặn và điểm mù

Đã chạy `.venv/Scripts/python.exe -m pipeline.run --budget 0 --work work/run_nb --reports work/rep_nb --export-dir work/exp_nb`. Kết quả Rework, mã thoát 20, còn 6 lỗi thiếu file nhãn trên 205 ảnh, reviewed = 0, exported = null. Đã kiểm tra `work/exp_nb/clean_v1` không tồn tại. Bằng chứng được sinh trong `work/rep_nb/08_summary.json` và `07_error_list_v3.csv`.

Hai điểm mù có bằng chứng. (1) pHash 4 bỏ sót biến đổi mạnh, cặp img_0186/img_0061 có cùng cảnh khi xem nhưng khoảng cách 10. Tăng ngưỡng lại có nguy cơ gộp sai như cặp tennis/trượt tuyết. (2) Checker ở conf 0,6 chỉ bắt 1/5 ca box lỏng và 5/6 ca sai lớp trên calib. Đạt cú pháp và qua model vẫn có thể còn lỗi ngữ nghĩa. Calib từ nhãn người, raw từ nhãn model nên recall calib không đại diện đầy đủ cho raw.

## 5. Train raw vs clean

Đã train trên Colab với yolo26n.pt, 20 epoch, batch 16, imgsz 640, hai seed 0 và 1 cho mỗi biến thể, cùng tập val và test. Số ảnh trong bảng là số ảnh của bộ train được dựng, raw có thể bị Ultralytics bỏ qua ảnh/nhãn hỏng khi nạp.

| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean | 205 | 2 | 0.700 ± 0.030 | 0.486 ± 0.013 | 0.715 ± 0.073 | 0.615 ± 0.017 |

Chênh mAP50 (clean − raw) = **-0.025**.

Clean có mAP50 trung bình thấp hơn raw khoảng 0,025, trong khi độ lệch chuẩn của clean là 0,030. Giá trị 0,000 của raw là số đã làm tròn. Với chỉ hai seed, chưa đủ cơ sở kết luận chênh lệch ổn định hoặc clean tốt hơn raw.

Hai giả thuyết cần kiểm tra. (1) Raw có 4/224 ảnh bị cờ LEAK_TEST do trùng kho test/val, có thể làm điểm đánh giá lạc quan. Có thể đo lại với bản raw đã loại riêng các ảnh rò rỉ, giữ các điều kiện train còn lại giống nhau. (2) Clean chỉ có 205 ảnh so với 224 ảnh raw và vẫn còn 38/205 ảnh có cảnh báo chưa duyệt. Giảm dữ liệu và lỗi nhãn còn lại có thể làm giảm chất lượng. Có thể so sánh thêm bản cùng tập ảnh với nhãn được duyệt đầy đủ, đồng thời tăng số seed để đo độ nhiễu. Các thí nghiệm này chưa được thực hiện.

## 6. Quyết định và ghi chú AI

Giữ **Hold** cho bản nháp. Với 205 ảnh, cần còn tối đa 20 ảnh có cảnh báo chưa duyệt để tỉ lệ dưới 10%, tức cần xử lý thêm ít nhất 18/38 ảnh hiện còn cảnh báo mà không phát sinh lỗi mới. Ngân sách 80 ảnh của lab đã dùng hết, nên ghi nhận nhu cầu duyệt bổ sung cho vòng xử lý sau và giữ các quy tắc dự án khi đánh giá lần chạy này.

- Prompt chính yêu cầu AI đọc GUIDE.md, docstring và test để viết 4 module theo đầu vào YOLO, quy tắc, đầu ra Issue/log và phạm vi thao tác trên dataset làm việc.
- AI chạy đủ 79 test, thử thêm dòng có hai lỗi, dòng trống giữ số dòng và nhiều dự đoán trên một ảnh. Đã xem các cặp ảnh trùng, chạy pipeline thực tế và kiểm tra gate với ngân sách 0. Các check đọc dữ liệu, autofix ghi/xoá trong dataset được truyền vào, pipeline dùng bản sao trong work.
- Lần đầu AI ghi code qua PowerShell làm mất dấu tiếng Việt trong thông báo. AI sửa cách ghi UTF-8 và kiểm tra lại nội dung.
