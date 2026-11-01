# Bộ dữ liệu cố định `du_lieu_co_dinh_v2`

Dữ liệu **mô phỏng** (seed 42; 360 giảng viên, 6 Khoa, 5 năm) cho dự đoán rủi ro trễ hạn công việc giảng viên.
Sinh bằng `gen_synthetic_data_v5.py`, dựng bằng `make_dataset_v2.py` (cùng quy trình làm sạch và ma trận tác vụ–nhân sự đã sửa của `v1b`).
**Không phải dữ liệu thật**: mọi chỉ số huấn luyện trên bộ này chỉ phản ánh khả năng học lại quy luật đã mô phỏng.

## Điểm khác so với `du_lieu_co_dinh_v1b`
1. **Danh mục loại việc và giờ quy đổi dựa trên bảng định mức "Công tác khác" năm học 2023–2024** (file `Cong-tac-khac-nam-hoc.xlsx`, sheet `KL_CT#`):
   - `converted_workload` của 34 trong 55 loại việc (17 loại giữ khoảng giả định, 4 loại không quy đổi) = định mức giờ trong bảng × số đơn vị (số tín chỉ, số bài, số buổi, số ca...). **Đơn giá giờ lấy từ file; số đơn vị là giả định của bộ sinh.**
   - Thêm 16 loại việc có trong bảng (dự giờ, trực đề thi, trực phòng thí nghiệm, ngân hàng câu hỏi thi, dự trù vật tư, ban tổ chức/giám khảo cuộc thi sinh viên, đưa đoàn sinh viên, bồi dưỡng chuyên môn, hướng dẫn trợ giảng, soạn văn bản, website, CLB học thuật...).
   - "Tham gia họp Bộ môn/Khoa" được tách thành 5 loại theo `Sheet1`: Trực khoa, Họp Khoa, Họp Bộ môn, Họp giao ban, Tập huấn của Trường. **Chỉ tỉ lệ tương đối 7:4:7:4:2 lấy từ file** (một giảng viên, khoảng tháng 11/2023–6/2024); tổng tần suất là giả định. Cột "Trục khoa" trong file được hiểu là "Trực khoa" (giả định, có thể là lỗi đánh máy).
   - `data/task_catalog_norm.csv` ghi rõ từng loại việc: có căn cứ từ file định mức (kèm số mục và nguyên văn định mức), là giả định, hay không quy đổi. Tỉ lệ số dòng: 53,6% có căn cứ từ file; 41,2% giả định; 5,2% không quy đổi.
2. **Cơ chế sinh nhãn không đổi**: `converted_workload` không đi vào điểm số trễ hạn. Khác biệt về kết quả so với v1b chỉ đến từ cơ cấu loại việc, tải việc và hiệu chuẩn lại, không phải từ định mức giờ.
3. **Hiệu chuẩn tỉ lệ trễ theo nhóm giảng viên (persona) trên toàn bộ dữ liệu** (v4 dùng mẫu thử 30% giảng viên), nên tỉ lệ trễ từng nhóm bám mục tiêu khảo sát trong ±0,025 (lệch lớn nhất: nhóm P2 +0,022 và P4 +0,020).
4. Không dùng họ tên hay mã nhân viên nào trong file định mức; tên giảng viên là `Giảng viên giả lập NNN`.

## Quy mô và cách chia (theo `assigned_date`, phân vị 60% / 75%)
| | Dòng | Train | Validation | Test | Tỉ lệ trễ train / val / test |
|---|---|---|---|---|---|
| Tĩnh | 99.765 (54.539 việc) | 59.966 | 14.891 | 24.908 | 18,9% / 19,2% / 21,7% |
| Động (mốc 25% và 50%) | 129.116 | 77.520 | 19.368 | 32.228 | 21,0% / 22,0% / 24,3% |
Tỉ lệ trễ chung tĩnh 19,6%. **Tập test có tỉ lệ trễ cao hơn train khoảng 3 điểm phần trăm** (hiệu ứng theo năm đã có sẵn trong bộ sinh). Điều này có thể làm xác suất dự đoán trung bình thấp hơn thực tế ở test; ngưỡng vẫn chốt trên validation, không chỉnh sau khi xem test.
Dữ liệu động ít dòng hơn v1b vì các việc có thời hạn dưới 4 ngày (họp, coi thi, trực...) không có mốc kiểm tra 25%/50%.
AUC trần (oracle, biết cả yếu tố ẩn): 0,8261 trên tập test tĩnh; 0,8187 trên toàn bộ dữ liệu.

## Tệp
| File | Dùng cho |
|---|---|
| `data/ml_training_set_with_matrix.csv` | Mô hình TĨNH (lúc giao việc) |
| `data/ml_dynamic_set_clean_with_matrix.csv` | Mô hình ĐỘNG; ghép CÙNG đặc trưng ma trận với bảng tĩnh (khớp 100% theo task_id + lecturer_id) |
| `data/oracle_truth.csv` | Xác suất "thật" của bộ sinh, chỉ để kiểm chứng mô hình tĩnh |
| `data/task_personnel_matrix*.csv`, `task_personnel_matrix_meta.json` | Ma trận tác vụ–nhân sự dùng khi dự đoán việc mới |
| `data/task_catalog_norm.csv` | Nguồn giờ quy đổi của từng loại việc (mới ở v2) |
| `data/data_dictionary.csv`, `data/generation_report.json` | Từ điển cột và báo cáo sinh dữ liệu |
| `MANIFEST.json`, `verify_data.py` | SHA-256 từng file; `python verify_data.py` phải ra "TẤT CẢ KHỚP" |

## Lưu ý
- Đừng chỉnh sửa file. Cần dữ liệu khác thì tạo bộ mới tên khác (ví dụ `v3`).
- Số liệu của lần chạy B (`v1b`) và của bộ này **không trộn lẫn**: đây là hai bộ dữ liệu khác nhau, không so trực tiếp từng chỉ số như một cải thiện của mô hình.
- Dữ liệu động: biến tiến độ được tạo từ nhãn ẩn theo giả định (nhịp làm việc việc trễ ≈ 0,72 lần việc đúng hạn; việc trễ ít cập nhật tiến độ hơn: 18% so với 4%). Mức cải thiện của mô hình động phụ thuộc các giả định đó.
- File định mức chỉ cung cấp đơn giá giờ và danh mục công việc; **không có hạn nộp, không có trạng thái trễ hạn**, nên không thể dùng nó để kiểm chứng tỉ lệ trễ.
