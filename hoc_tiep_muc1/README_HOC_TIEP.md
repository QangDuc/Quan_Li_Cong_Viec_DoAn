# Học tiếp mức 1: huấn luyện lại định kỳ có kiểm soát

Gói `hoc_tiep/` cho phép mô hình cải thiện từ dữ liệu vận hành mà **không tự đổi ngầm**: mỗi lần huấn luyện lại tạo một *ứng viên*, so với mô hình đang chạy trên dữ liệu mà mô hình đó chưa thấy, và chỉ nâng cấp khi qua mọi rào chắn. Mọi phiên bản được giữ lại và quay lại được.
Đây là hướng "huấn luyện lại định kỳ có kiểm soát", không phải học từng mẫu (không dùng học trực tuyến, ADWIN hay chạy bóng; đó là mức 3).

## 1. Thành phần
| Tệp | Vai trò |
|---|---|
| `feedback_store.py` | Kho SQLite: dự đoán đã đưa ra (kèm đặc trưng **lúc giao việc**), kết quả thật khi hoàn thành, can thiệp. Chỉ giữ dự đoán đầu tiên của mỗi việc; không lưu nhãn trong đặc trưng. |
| `model_registry.py` | Phiên bản bất biến `v0001, v0002...`, con trỏ `CURRENT` đổi nguyên tử, `history.jsonl`, kiểm tra SHA-256 khi nạp, `rollback` nhiều bước. |
| `retrain_job.py` | `init_model` (tạo v0001), `run` (huấn luyện lại + so sánh + rào chắn), `gate` (các rào chắn chất lượng, dùng chung cho đường TabPFN). |
| `compare.py` | So cặp theo cụm giảng viên (ΔAUC, Δlogloss, ΔBrier, KTC 95%), thống kê mức cảnh báo, `pick_thresholds` (bản sao của `train_model`, có kiểm thử khớp). |
| `serving.py` | `RiskService.predict`: dùng `CURRENT`, tự ghi nhật ký, tự nạp lại khi `CURRENT` đổi. |
| `cli.py` | `init, predict, outcome, retrain [--dry-run], status, rollback, export, compare`. |
| `tests/test_hoc_tiep.py` | 11 kiểm thử (dữ liệu tổng hợp). `python tests/test_hoc_tiep.py` |
| `simulate_operation.py` | Mô phỏng vận hành 11 quý trên bộ `du_lieu_co_dinh_v2`. |

## 2. Luồng mỗi lần huấn luyện lại (`as_of` = ngày chạy)
1. Lấy việc **đã có nhãn tại `as_of`** (hoàn thành và đã ghi nhận). Việc chưa xong không có mặt: đó là độ trễ nhãn.
2. Chỉ việc **đã chín** (giao trước `as_of - maturity_days`, mặc định 120 ngày) được dùng cho cửa sổ kiểm tra. Lý do: trên bộ v2, thời gian giao → hoàn thành có trung vị 6 ngày nhưng P90 = 90 ngày và P95 = 170 ngày **[đo]**; việc mới giao mà đã xong sớm phần lớn đúng hạn, nên tỉ lệ trễ của việc "mới có nhãn" bị lệch thấp.
3. Cửa sổ so sánh (holdout, 90 ngày) chỉ gồm việc giao **sau dữ liệu cuối của mô hình hiện tại** để mô hình hiện tại chưa thấy.
4. Ứng viên: mô hình phụ huấn luyện trước cửa sổ chọn ngưỡng (90 ngày) → chọn ngưỡng Thấp/Trung bình/Cao bằng `pick_thresholds` (cùng mục tiêu: Thấp trễ ≤ 10%, Cao chính xác ≥ 60%); ứng viên huấn luyện đến hết trước holdout và dùng ngưỡng đó. **Không chỉnh ngưỡng hay cấu hình bằng holdout.**
5. Các rào chắn (`Config`):
   | Nhóm | Điều kiện để nâng cấp |
   |---|---|
   | Dữ liệu | ≥ 2.000 việc mới có nhãn và ≥ 200 việc trễ mới; holdout ≥ 2.000 dòng, ≥ 200 trễ, ≥ 30 giảng viên; tỉ lệ trễ dữ liệu mới trong [5%, 50%]; thiếu ≤ 5% cột đặc trưng |
   | Không kém | cận dưới KTC của ΔAUC ≥ −0,002; cận trên KTC của Δlogloss ≤ +0,002; AUC ứng viên ≥ 0,65 |
   | Tốt hơn | cận trên KTC của Δlogloss < 0 (tắt được bằng `require_significant_gain=False`) |
   | Mức cảnh báo | trên holdout, Thấp trễ ≤ 12% và Cao chính xác ≥ 55%, hoặc không kém mô hình hiện tại |
6. Quyết định (nâng cấp hay giữ, kèm từng lý do) được ghi vào `history.jsonl`. `--dry-run` chỉ in quyết định.

## 3. Cách dùng
```
python -m hoc_tiep.cli init     --base data/ml_training_set_with_matrix.csv --registry registry --cutoff 2025-12-31
python -m hoc_tiep.cli predict  --registry registry --store feedback.db --input viec_moi.csv --output ket_qua.csv
python -m hoc_tiep.cli outcome  --store feedback.db --input ket_qua_that.csv     # task_id,lecturer_id,completed_date,is_late
python -m hoc_tiep.cli retrain  --registry registry --store feedback.db --base data/ml_training_set_with_matrix.csv --as-of 2026-07-01 --dry-run
python -m hoc_tiep.cli rollback --registry registry --reason "..."
```
Đặt `train_model.py` cạnh gói (có sẵn) để dùng đúng `engineer`/`restore_dups` của dịch vụ; không có thì gói dùng bản sao tối thiểu và kết quả có thể lệch nhẹ.

## 4. Kết quả mô phỏng vận hành [đo, 1 bộ dữ liệu mô phỏng, 1 lần chạy, mô hình HistGradientBoosting trên CPU]
M� hình đầu chỉ học việc **hoàn thành trước 2026-01-01** (34.789 việc, trễ 17,0%); 2026Q1–2028Q3 (11 quý, 63.023 việc, trễ 20,6%) dự đoán bằng phiên bản đang chạy rồi huấn luyện lại cuối mỗi quý. Mọi dự đoán được đánh giá bằng phiên bản đã đưa ra dự đoán đó.
| Chiến lược | AUC | Logloss | Brier | ECE | Dự đoán TB (thật 0,206) | Thấp: % số việc / tỉ lệ trễ | Cao: % số việc / chính xác | Số phiên bản đã dùng |
|---|---|---|---|---|---|---|---|---|
| S0 giữ nguyên | 0,7821 | 0,4179 | 0,1299 | 0,0217 | 0,187 | 61,3% / 9,3% | 5,4% / 74,8% | 1 |
| S1 huấn luyện lại mỗi quý, nâng cấp vô điều kiện | 0,7927 | 0,4090 | 0,1269 | 0,0215 | 0,185 | 65,5% / 9,6% | 8,4% / 70,1% | 11 |
| S2 có kiểm soát (rào chắn mặc định) | 0,7875 | 0,4131 | 0,1287 | 0,0186 | 0,199 | 60,2% / 9,1% | 6,5% / 69,2% | 4 |
| S3 có kiểm soát, chỉ cần "không kém" | 0,7875 | 0,4131 | 0,1287 | 0,0186 | 0,199 | 60,7% / 9,2% | 6,5% / 69,2% | 5 |
So với S0 (cặp theo cụm giảng viên, 300 lần lấy mẫu): S1 ΔAUC +0,0106 [+0,0082; +0,0128], Δlogloss −0,0089 [−0,0106; −0,0070]; S2 ΔAUC +0,0054 [+0,0037; +0,0070], Δlogloss −0,0048 [−0,0062; −0,0032].
Cả bốn chiến lược đạt mục tiêu mức cảnh báo (Thấp ≤ 10%, Cao ≥ 60%) khi gộp cả giai đoạn.

**Đọc kết quả cho đúng:**
- Huấn luyện lại định kỳ cải thiện có ý nghĩa thống kê nhưng nhỏ (AUC +0,005 đến +0,011) trên dữ liệu mô phỏng này.
- **Trong mô phỏng này, rào chắn giữ lại khoảng một nửa mức cải thiện của cách nâng cấp vô điều kiện** (S2 +0,0054 so với S1 +0,0106) và dùng ít phiên bản hơn (4 so với 11). Dữ liệu mô phỏng sạch, không có lỗi dữ liệu hay hỏng pipeline, nên mô phỏng **không đo được lợi ích bảo vệ** của rào chắn; phần đó chỉ có kiểm thử đơn vị (mục 6).
- Chưa thể huấn luyện lại hữu ích trước 2026-07: cần đợi việc mới "chín" và đủ cửa sổ so sánh (quyết định 2026-04-01 bị từ chối vì holdout rỗng).
- Nhiều lần bị từ chối ở 2027–2028 do ứng viên "kém hơn" mô hình đang chạy trên holdout (cận dưới ΔAUC đến −0,0096). **Chưa xác định nguyên nhân** (chưa thử nghiệm giả thuyết nào).
- Rào chắn kiểm tra quá khứ gần, nên **không bảo vệ trước lệch xảy ra sau khi nâng cấp**: S2 dự đoán cao hơn thực tế khoảng 2,5–3,6 điểm phần trăm ở 2026Q4–2027Q2 (0,223–0,231 so với 0,194–0,201) sau khi nâng cấp lên v0002. Cần giám sát hiệu chuẩn theo tháng (mức 2).
- Mô hình mô phỏng là HGB, **không phải TabPFN**; chưa đo hành vi này với TabPFN.
- Một lỗi đã gặp và sửa trong mã mô phỏng: ghép nhãn theo `task_id` làm sai nhãn vì việc nhóm có nhiều giảng viên; khóa đúng là `(task_id, lecturer_id)`. AUC của S0 đã đối chiếu độc lập bằng huấn luyện trực tiếp (0,7821).

## 5. Đường dùng cho TabPFN (chưa tự động, chưa kiểm chứng)
Gói tự huấn luyện lại, đăng ký phiên bản và quay lại cho mô hình HGB. TabPFN cần GPU nên làm bán tự động:
1. `export` các việc có nhãn từ kho phản hồi, ghép với dữ liệu nền cùng cấu trúc cột.
2. Huấn luyện trên Colab bằng `train_model.py` như lần B → thu được `predictions` của ứng viên.
3. Lấy dự đoán của mô hình hiện tại trên **cùng các dòng holdout** (việc giao sau dữ liệu cuối của mô hình hiện tại, đã chín).
4. `python -m hoc_tiep.cli compare --input du_doan.csv --thr-current a,b --thr-candidate c,d` (cột `y, p_current, p_candidate, lecturer_id`) áp đúng các rào chắn chất lượng; đạt thì thay `model/` trong dịch vụ và ghi lại thủ công.
Chưa có: đăng ký phiên bản TabPFN trong kho, quay lại tự động cho TabPFN.

## 6. Kiểm thử đơn vị (dữ liệu tổng hợp) đã chứng minh
Kho phản hồi tôn trọng `as_of` và thời điểm ghi nhận (không rò nhãn tương lai), giữ dự đoán đầu tiên, không lưu nhãn trong đặc trưng; loại việc đã can thiệp khi `intervention_policy="exclude"`; kho phiên bản không ghi đè, phát hiện file bị sửa, quay lại nhiều bước và dịch vụ tự nạp lại; so cặp cho Δ = 0 khi hai mô hình giống nhau; từ chối khi thiếu dữ liệu hoặc tỉ lệ trễ bất thường; nâng cấp khi quy luật thật sự đổi; không nâng cấp khi hai mô hình ngang nhau; chạy khô không đổi gì; danh mục chưa gặp và giá trị thiếu không làm lỗi dự đoán.

## 7. Rủi ro và việc chưa làm
- **Can thiệp làm lệch nhãn**: nếu người quản lý can thiệp vào việc nguy cơ cao, kết quả sau can thiệp ít trễ hơn và mô hình học rằng việc như vậy ít rủi ro. Gói ghi nhận can thiệp và mặc định loại các việc đó (`exclude`), nhưng việc này làm dữ liệu huấn luyện lệch về phía việc nguy cơ thấp. Giải pháp tốt hơn cần quyết định tổ chức: giữ một nhóm đối chứng ngẫu nhiên không can thiệp. **Chưa mô phỏng** (không có mô hình nhân quả của can thiệp trong bộ sinh).
- **Độ trễ nhãn** (mục 2) và việc không bao giờ hoàn thành (không có nhãn) vẫn làm dữ liệu mới lệch về việc xong sớm.
- **Quyền riêng tư**: kho giữ mã giảng viên và đặc trưng từng việc; dùng mã giả danh, giới hạn quyền đọc file `.db`, định kỳ xóa dữ liệu cũ theo quy định của trường.
- **An toàn tệp mô hình**: `.joblib` là pickle; SHA-256 chỉ phát hiện sửa đổi sau khi đăng ký (không chứng minh nguồn gốc). Chỉ nạp từ thư mục kho do bạn kiểm soát; ghim scikit-learn (phiên bản huấn luyện được ghi trong `meta.json`, nạp lệch sẽ cảnh báo).
- **Đồng thời**: SQLite một người ghi; không có khóa cho hai `retrain` chạy cùng lúc.
- **Chưa tích hợp vào `task_risk_service`** vì chưa có mã của dịch vụ. Cần: (a) thay đường nạp mô hình cố định bằng `ModelRegistry.load()`/`RiskService`; (b) gọi `log_predictions` sau mỗi dự đoán (đặc trưng phải là bản đã tính **lúc giao việc**, gồm cả đặc trưng ma trận); (c) thêm điểm ghi kết quả (`record_outcomes`) khi việc hoàn thành; (d) lập lịch `retrain` (ví dụ cuối quý) và hiển thị phiên bản đang chạy.
- Chưa có: giám sát lệch phân phối và hiệu chuẩn theo tháng, lập lịch, mô hình động (`kind='dyn25'/'dyn50'` được lưu nhưng chưa mô phỏng), học trực tuyến theo mẫu.
- Siêu tham số HGB cố định (`DEFAULT_HGB`); việc chọn siêu tham số là việc ngoại tuyến, không làm trong mỗi lần huấn luyện lại.
