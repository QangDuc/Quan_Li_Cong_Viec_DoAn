# Nhật ký sửa lỗi (bản đã sửa của `BO_ML_HOAN_THIEN_V2_MOI_NHAT`)

Mỗi mục ghi: lỗi, nơi sửa, cách kiểm chứng. [đo] = đã chạy và có số liệu; [chưa kiểm chứng] = chưa chạy được trong môi trường kiểm tra (không có GPU, không có trọng số TabPFN).

## A. Gỡ mô hình nhẹ (`fast_models`, `--fast-cpu`)
| Việc | Chi tiết | Kiểm chứng |
|---|---|---|
| Gỡ `fast_models` khỏi hai bundle | `model/risk_model.joblib` 3,00 MB → 2,15 MB; `model_dynamic/risk_model.joblib` 3,74 MB → 2,46 MB. Xóa khóa `fast_cpu` trong hai `metrics.json`. | [đo] ngữ cảnh, bộ mã hóa, ngưỡng, đặc trưng giữ nguyên (băm mảng trước và sau); `SHA256SUMS.txt` |
| Gỡ khỏi mã huấn luyện | `train_model.py`: bỏ `--fast-cpu`, `--allow-fallback`, `fit_fast_fallback`, nhánh HGB trong dự đoán, giải thích và lưu bundle. `--fast-cpu-tabpfn` (TabPFN rút gọn ngữ cảnh) đổi tên thành `--cpu-light`, chưa đánh giá chất lượng. Thiếu `tabpfn` thì **dừng** với thông báo rõ. | [đo] 22/22 chỗ vá khớp đúng 1 lần; huấn luyện tĩnh và động, `predict --explain` chạy đúng bằng mô-đun `tabpfn` **giả lập** (chỉ kiểm tra dây nối); thiếu tabpfn thì dừng; cờ cũ bị từ chối |
| Notebook | Dựng lại 3 notebook (v2, seed 43, seed 44) không còn mô hình nhẹ; thư mục kết quả riêng cho từng bộ dữ liệu; bảng mức cảnh báo in 2 chữ số (10,04% không còn bị làm tròn thành "10,0%"). Hai notebook cũ (`Colab_TRAIN_FULL_tabpfn`, `Colab_du_doan_tre_han_tabpfn`) bị loại. | [đo] mọi script nhúng biên dịch được |
| Báo cáo | Bỏ các dòng và mục về mô hình nhẹ trong `BAO_CAO.md` (tĩnh, động), `BANG_README.md`, `SO_SANH_MO_HINH.md`, chương 4. | [đo] không còn tham chiếu |
| Còn lại cố ý | Bộ lọc phòng thủ trong `slim()`; backend HGB của `hoc_tiep` (chỉ để mô phỏng và kiểm thử học tiếp); động cơ `surrogate_hgb` (chọn chủ động) của dịch vụ; nhật ký gốc `train_report.txt`. | xem README |

## B. Dịch vụ `ml_service.py`
| Lỗi | Sửa | Kiểm chứng |
|---|---|---|
| Chế độ CPU huấn luyện lại 4 mô hình HGB lúc khởi động, im lặng thay TabPFN; "OOB AUC = 0,837" không có cơ sở | Mặc định chạy TabPFN; không nạp được thì `degraded` và trả 503. HGB chỉ bật bằng `ML_ENGINE=surrogate_hgb`, gắn nhãn `engine_validated=false`. Bỏ câu "OOB AUC". | [đo] AUC test v2 của động cơ HGB = **0,7991** (TabPFN 0,8090); AUC trên chính dữ liệu huấn luyện 0,97 |
| Dùng phiên bản TabPFN mặc định của gói thay vì phiên bản lưu trong bundle | `create_default_for_version(ModelVersion(bundle["tabpfn_version"]))` như `train_model.make_tabpfn` | [chưa kiểm chứng] với TabPFN thật; [đo] dây nối bằng mô-đun giả lập |
| Chữ khuyến nghị ghi cứng ngưỡng 22% và 44% (bundle dùng 23% và 52%) | Lấy ngưỡng từ bundle (hoặc `cpu_surrogate.json` cho động cơ HGB) | [đo] `test_ml_service.py` |
| Ngưỡng của TabPFN áp cho HGB: nhóm Thấp trễ 10,8% | `calibrate_cpu_surrogate.py` chọn ngưỡng riêng trên validation (biên 0,01 và 0,03) | [đo] ngưỡng [0,20; 0,53]; trên validation nhóm Thấp trễ 8,13%; test v2 (đã xem trước đó nên chỉ minh họa): Thấp 66,2% số việc trễ 9,92%, Cao 8,9% số việc chính xác 70,9% |
| Giải thích liệt kê trường không gửi ("= thiếu") như yếu tố rủi ro | Bỏ qua trường không được gửi; thiếu quá 25% trường thì `low_confidence`, có ghi chú và danh sách `missing_features` | [đo] `test_ml_service.py` |
| `/health` báo AUC "N/A" | Đọc đúng `metrics.json` (`test.roc_auc`) | [đo] |
| Chạy độc lập hỏng (`No module named 'backend'`) | `uvicorn.run(app)`; test dùng `import ml_service`; `ML_MODEL_DIR` ghi đè đường dẫn | [đo] |
| Lỗi nội bộ trả chi tiết ngoại lệ cho client | Trả thông báo chung, chi tiết ghi vào nhật ký | |
| `requirements.txt` không ghim `tabpfn`, có `catboost` thừa | Ghim `tabpfn==9.2.0`, `torch>=2.5` (theo metadata gói), bỏ `catboost` | [đo] metadata `tabpfn 9.2.0`: Python >= 3.10 |

## C. `monitor.py` (báo động giả)
Bản cũ dùng ngưỡng cố định và `min_samples = 30`. Đo bằng mô phỏng (nhãn sinh từ chính xác suất thật của TabPFN, tức hiệu chuẩn hoàn hảo): cửa sổ 30 việc bị cảnh báo 100%, 300 việc 94%, 1.000 việc 29%, 3.000 việc 0,7%. Bản mới: cảnh báo dựa trên khoảng Wilson (cam kết mức Thấp và Cao) và z-test độ lệch hiệu chuẩn, `min_samples = 1000`, ECE chỉ báo cáo. [đo] báo động giả tối đa 0,7% ở cửa sổ từ 1.000 việc; phát hiện 100% khi lệch 4 điểm phần trăm trở lên, 61% khi lệch 2 điểm (cửa sổ 3.000 việc). `hoc_tiep` đồng bộ với bản có biên an toàn riêng cho mức Cao; **15/15 kiểm thử đạt** trong môi trường sạch (`scikit-learn 1.6.1`).

## D. Chương 4 (Word) và tài liệu
| # | Lỗi | Sửa |
|---|---|---|
| 1 | Bảng 4.2 sai số nhóm Trung bình và Cao; "10,0% Đạt ≤ 10%" | Tính lại từ dự đoán: Thấp 17.172 (68,9%) trễ **10,04% không đạt**; Trung bình 4.927 (19,8%) trễ 35,3%; Cao 2.809 (11,3%) trễ 69,3% đạt. Cũng sửa `BAO_CAO.md` và `SO_SANH_MO_HINH.md` (bảng động sai tương tự: nay Thấp 22.161 trễ 10,26%; Trung bình 3.672 trễ 33,5%; Cao 6.395 trễ 67,5%) |
| 2 | Mục 4.1.2 dùng số và ngày của bộ cũ (75.017, 18.755, 24.994, 34.700; đến 08/04/2026) | Số của `v2`: 59.966, 14.891, 24.908, 32.228; train đến 04/01/2027, validation đến 18/08/2027 |
| 3 | "Tiến độ đóng góp +2,92% AUC" lẫn tác động của mô hình | Đóng góp riêng: CatBoost có và không có tiến độ **+0,0254 [+0,0216; +0,0294]** [đo]; nêu rõ giả định của bộ sinh |
| 4 | "Vượt trội" so với Logistic (ΔAUC +0,0018, khoảng tin cậy chứa 0); "p < 0,001" (chưa tính p); "triệt tiêu hoàn toàn rò rỉ"; "tối ưu", "tăng vọt", "xuất sắc" | Diễn đạt lại theo khoảng tin cậy; bỏ p-value; "không phát hiện rò rỉ trong các kiểm tra đã làm" (đặc trưng ma trận trùng khớp 100%; `hist_*` chưa kiểm chứng độc lập hoàn toàn) |
| 5 | Bảng 4.4 không ghi là mô hình động; "Vượt trội" khi chênh 0,004 chưa kiểm định | Ghi rõ mô hình động, n = 32.228; bỏ nhãn "Vượt trội" và "Tăng vọt" |
| 6 | Mục 4.5: mô phỏng dùng HGB nhưng không nêu; "bảo vệ" chưa chứng minh; "ECE thấp nhất toàn hệ thống" (S2 bằng S3) | Nêu rõ HGB, dữ liệu mô phỏng, một lần chạy, chưa tích hợp web; S2 giữ khoảng một nửa mức cải thiện của S1; nêu độ lệch hiệu chuẩn sau nâng cấp |
| 7 | Mục 4.6: "TabPFN 28–35 ms" thực ra là động cơ HGB; "58 đặc trưng" | Ghi đúng động cơ (AUC test 0,7991), đo độc lập khoảng 14 ms (CPU 1 nhân); dịch vụ dựng 58 trường, mô hình dùng 55; tuyên bố "7 passed" ghi rõ chưa kiểm chứng (mã kiểm thử không có trong gói) |
| 8 | Mục 4.1.1: phiên bản Python 3.13.15 | 3.13.16 (theo `metrics.json`); phần cứng Colab ghi rõ do tác giả khai báo (không có trong nhật ký) |
| 9 | Kết luận 4.7 quá mức | Viết lại theo số đo; thêm mục "Về độ tái lập" |
| 10 | README: "ROC-AUC = 0,817"; nhắc `quality_gates.py`, lệnh `ingest`, `drain` không có thật; "58 đặc trưng" | `README_HUONG_DAN.md` viết lại. 0,817 là AUC nhóm "mùa cao điểm"; AUC tổng 0,809 |
| 11 | `BAO_CAO_3_SEEDS.md`: "CatBoost luôn cao nhất" (sai: seed 44 logistic 0,8158 cao hơn CatBoost 0,8154); câu kết luận ghi cứng trong script; khẳng định "chứng minh không rò rỉ hay overfit" | `export_3seeds_report.py` viết lại, mọi số và nhận xét tính từ dữ liệu; báo cáo tạo lại (CPU, 3 seed, kèm trần oracle). Dữ liệu seed 43 và 44 cùng kết quả mô hình đối chứng được tái tạo độc lập |
| 12 | Đóng gói: 19 file `.pyc`; `train_model.py` ở `training_scripts` là bản cũ không tạo ra kết quả | Xóa `.pyc`; `train_model.py` nay thống nhất ở `training_scripts/`, `hoc_tiep_mlops/` và trong notebook (so sánh nội dung: giống nhau) |

## E. Chưa làm được hoặc cần bạn chạy
* TabPFN thật trong dịch vụ (cần `tabpfn==9.2.0`, trọng số, GPU) và thời gian suy luận của nó.
* TabPFN trên seed 43 và 44 (notebook đã sẵn sàng, khoảng 1 đến 2 giờ GPU mỗi bộ).
* Kiểm thử backend `test_ml_features.py` (mã không nằm trong gói).
* Chương 4: các hình (ROC, hiệu chuẩn) không đổi vì không có đường cong mô hình nhẹ; phần cứng Colab chưa kiểm chứng được.

## F. Đợt rà soát 2026-11-01: lệch train/serve và độ bền dịch vụ
| Lỗi | Sửa | Kiểm chứng |
|---|---|---|
| `workload_next_14d`: dịch vụ loại việc quá hạn, bộ sinh (dòng 453) cộng cả việc quá hạn | `load_features` dùng `load14` gồm việc có hạn <= hôm nay + 14 | [đo] `service/test_feature_parity.py` |
| Giai đoạn/học kỳ suy theo tuần lệch bộ sinh 5,7% số ngày (62/1095), `peak_season` lệch 18 ngày | `academic.calendar_features` dùng bảng theo ngày giống bộ sinh (`period_by_date`, `semester_by_date`) | [đo] 0 ngày lệch trên 4 năm |
| `deadline_month_end` = 4 ngày cuối tháng (kể cả cuối tuần), bộ sinh = ngày làm việc cuối tháng | đổi đúng quy tắc; còn lệch nhỏ nếu hạn tình cờ trùng ngày đó | [đo] test tương đương |
| `academic.py` import `app.config` làm test độc lập không chạy | `try/except ImportError`, mặc định 08-15 | [đo] `test_ml_features.py` 4 đạt |
| Dịch vụ: không khóa luồng; giá trị phân loại lạ bị coi là thiếu không báo; giải thích luôn chạy | `threading.Lock`; trường `unseen_categories` + hạ độ tin cậy; tham số `explain` (mặc định true) | [đo] `test_ml_service.py` |
| `Dockerfile.ml`: sao chép thừa, không ghi chú CPU/GPU | gọn lại, 1 worker, ghi chú | chưa build image |
| `pick_thresholds`: ngưỡng Thấp nhảy qua chỗ vi phạm khi nhiễu | dừng ở lần vi phạm đầu | [đo] ngưỡng validation tính lại trùng [0,23; 0,52] và [0,26; 0,42] |
Chưa sửa/kiểm: TabPFN thật, độ trễ thật, notebook Colab còn bản cũ của `pick_thresholds` (dán lại từ `train_model.py`), mô hình chưa huấn luyện lại sau sửa đặc trưng (bundle không đổi).

## G. Đối chiếu đầy đủ đặc trưng (2026-11-01, `service/test_feature_parity_full.py`)
Sinh 24 giảng viên x 3 năm bằng chính bộ sinh, dựng lại đầu vào thô từng dòng, so 58 đặc trưng của `build_features` với tập huấn luyện (2.500 dòng).
| Lỗi tìm thêm | Sửa |
|---|---|
| `hist_late_last5` lệch 23,6% dòng: dịch vụ lấy 5 việc xong gần nhất theo thứ tự HOÀN THÀNH, bộ sinh theo thứ tự GIAO | sắp theo `assigned_at` (hòa thì `task_id`); `ml_extract.py` truyền thêm hai trường này [cần xác nhận tên cột vì thiếu `models.py`] |
| `late_last_30d` lệch 2,6%: dịch vụ so `>` thời điểm, bộ sinh so ngày `>=` | so theo ngày, gồm biên |
Kết quả sau sửa: 56/58 đặc trưng khớp 100%; `deadline_month_end` lệch 1,6% (hạn không bị dồn nhưng tình cờ rơi vào ngày làm việc cuối tháng; không tránh được vì cờ gốc là kết quả ngẫu nhiên); `complexity_num`, `priority_num` tính lúc huấn luyện nên không có trong CSV (đã kiểm riêng trong test_ml_features).
Hiệu chuẩn (Platt, isotonic) trên validation: làm ECE test xấu đi (0,0075 -> 0,027) vì tỉ lệ trễ validation 19,2% thấp hơn test 21,7%; không đưa vào dịch vụ.

## H. Học tiếp tự động cho TabPFN (2026-11-01)
Thêm: `tabpfn_backend.py`, `auto_job.py`, lệnh `import-tabpfn`, `retrain-auto`, tùy chọn `--config`; dịch vụ nạp từ kho (`ML_REGISTRY_DIR`), tự nạp lại, `/reload`; `hoc_tiep_hook.py`; 6 kiểm thử mới (TabPFN giả).
Lỗi tìm thấy khi làm: (1) `cli monitor` báo NameError (các dòng in chi tiết của `compare` nằm nhầm trong nhánh `monitor`), `cli compare` chỉ in ĐẠT/KHÔNG ĐẠT: đã sửa; (2) `compare.pick_thresholds` còn bản cũ (nhảy qua chỗ vi phạm): đồng bộ với `train_model.py`; (3) /health không kích hoạt nạp lại nên job sẽ hết giờ và quay lại nhầm: /health giờ gọi `reload()` ở chế độ kho.
Giới hạn: TabPFN thật chưa chạy; rào chắn mặc định theo quy mô mô phỏng, cần hạ cho một khoa nhỏ (xem README_HOC_TIEP mục 8).

## G. Đối chiếu với bản cũ `BO_ML_HOAN_THIEN_V2_MOI_NHAT` và dọn nốt
Dữ liệu (`matrix_data/`, `predictions_*.csv`, các bảng trong `reports_and_docs`) giống hệt giữa hai bản; `metrics.json` chỉ mất khóa `fast_cpu`. Chương 4 bản cũ vẫn dùng số của bộ dữ liệu trước, bản này đã thay.
| Lỗi còn sót | Sửa | Kiểm chứng |
|---|---|---|
| `model/bao_cao_muc_canh_bao.json` là kết quả của bộ dữ liệu cũ (ngưỡng 0,22/0,44; AUC 0,8198; tổng 24.994), có từ bản cũ và chưa ai sửa | Tạo lại từ `model/metrics.json` (cùng cấu trúc khóa, thêm `_ghi_chu`) | [đo] bảng mức cảnh báo tính lại từ `predictions_test.csv` trùng `metrics.json` (17.172 / 4.927 / 2.809) |
| Chú thích "mô hình nhẹ CPU" trong `train_model.py` (2 bản) và 3 notebook | Đổi thành "chạy trên CPU" | [đo] biên dịch được, hai bản `train_model.py` vẫn giống nhau, notebook đọc được bằng JSON |
| "58 đặc trưng" trong `ml_extract.py` và `README_TICH_HOP.md` dễ lẫn với 55 đặc trưng mô hình dùng | Ghi "58 trường (mô hình dùng 55)" | |
| Số trong chương 4 gõ tay, không có gì phát hiện khi lệch | `kiem_tra_so_lieu_chuong4.py` (94 kiểm tra), thêm vào `run_all_tests.py` | [đo] bản mới 94/94 đạt; chạy trên docx bản cũ báo 25 lỗi |

Giới hạn của `kiem_tra_so_lieu_chuong4.py`: chỉ kiểm tra số kỳ vọng có mặt trong văn bản, không kiểm tra đúng ô hay đúng câu; số ngoài danh sách chưa được kiểm tra. Các file kết quả chỉ lưu 5 chữ số thập phân nên 5 giá trị hòa ở chữ số cuối (ví dụ 0,37225) được chấp nhận cả hai cách làm tròn.
Còn lại, chưa xử lý: khoảng tin cậy AUC của TabPFN có hai giá trị hơi khác nhau giữa `metrics.json` ([0,7962; 0,8205]) và `so_sanh_cap.json` ([0,7966; 0,8204]) do hai lần bootstrap; chương 4 dùng giá trị sau. Chưa tìm nguyên nhân 8/11 lần học tiếp bị từ chối trong mô phỏng.

