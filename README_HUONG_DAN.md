# Bộ ML hoàn thiện (v3, sẵn sàng tích hợp): dự đoán rủi ro trễ hạn công việc giảng viên bằng TabPFN

**Bắt đầu nhanh:** `python run_all_tests.py` (kiểm thử), `cd service && python demo_predict.py` (demo), `service/README_TICH_HOP.md` (tích hợp vào web), `HOI_DAP_BAO_VE.md` (câu hỏi bảo vệ), `NHAT_KY_SUA_LOI.md` (mục F, G: các lỗi đã sửa ở v3).

Dữ liệu là **mô phỏng**; mọi chỉ số phản ánh khả năng học lại quy luật đã mô phỏng, **không phải hiệu quả trên dữ liệu thật**. Danh sách đầy đủ các lỗi đã sửa và cách kiểm chứng: `NHAT_KY_SUA_LOI.md`.

## 1. Kết quả chính (tập test v2, một seed)
| | Mô hình tĩnh | Mô hình động |
|---|---|---|
| Mô hình | TabPFN 9.2.0, 4 túi x 10.000 dòng ngữ cảnh | như bên trái |
| Số dòng test / tỉ lệ trễ | 24.908 / 21,72% | 32.228 / 24,26% |
| ROC-AUC [KTC 95%] | **0,8090** [0,797; 0,820] | **0,8356** [0,825; 0,846] |
| Brier / ECE | 0,1266 / 0,0075 | 0,1249 / 0,0051 |
| So với CatBoost (ΔAUC [KTC 95%]) | -0,0004 [-0,0022; +0,0014], ngang nhau | +0,0038 [+0,0018; +0,0056], có ý nghĩa, nhỏ |
| Ngưỡng [Thấp, Cao] | [0,23; 0,52] | [0,26; 0,42] |
| Nhóm Thấp: tỉ lệ trễ (mục tiêu <= 10%) | **10,04% (không đạt)**, Wilson 95% [9,60%; 10,50%] | **10,26% (không đạt)**, Wilson 95% [9,86%; 10,66%] |
| Nhóm Cao: độ chính xác (mục tiêu >= 60%) | 69,3% (đạt) | 67,5% (đạt) |

Không so AUC tĩnh với AUC động (khác tập test và khác tỉ lệ trễ). Ngưỡng chốt trên validation, không chỉnh sau khi xem test.

## 2. Cấu trúc gói
| Thư mục | Nội dung |
|---|---|
| `model/`, `model_dynamic/` | `risk_model.joblib` (ngữ cảnh TabPFN, bộ mã hóa, ngưỡng; **đã gỡ mô hình nhẹ `fast_models`**), `metrics.json`, dự đoán validation/test, nhật ký huấn luyện gốc `train_report.txt` (chứa **hai lần chạy nối tiếp**: lần cũ trên `v1b` rồi lần `v2`; còn dòng nhắc mô hình nhẹ vì là nhật ký gốc). `model/cpu_surrogate.json`: ngưỡng của động cơ demo (xem mục 4). |
| `colab_notebooks/` | `Colab_RETRAIN_v2.ipynb` (tái hiện đúng lần chạy đã cho kết quả trên, biên an toàn 0,01 cho cả hai mức), `..._seed43.ipynb`, `..._seed44.ipynb` (nhân bản với quy tắc ngưỡng chốt trước: Thấp 0,01, Cao 0,03). Mỗi bộ dữ liệu một thư mục kết quả riêng để log không trộn. |
| `training_scripts/` | Bộ sinh dữ liệu `gen_synthetic_data_v5.py`, `make_dataset_v2.py`, `train_model.py` (đã gỡ `--fast-cpu` và `--allow-fallback`; thêm `--safety-margin-high`), mô hình đối chứng, `export_3seeds_report.py` (tính toàn bộ từ dữ liệu), `calibrate_cpu_surrogate.py`. |
| `service/` | Dịch vụ suy luận FastAPI `ml_service.py`, dựng đặc trưng `app/ml_features.py`, kiểm thử (`test_*.py`), `demo_predict.py`, ca mẫu `sample_requests.json`, hướng dẫn `README_TICH_HOP.md`. |
| `hoc_tiep_mlops/` | Mô-đun học tiếp mức 1 và giám sát mức 2 (`monitor.py`), 15 kiểm thử, mô phỏng vận hành. Xem `README_HOC_TIEP.md`. |
| `reports_and_docs/` | Chương 4 (Word, đã sửa), báo cáo tĩnh/động, so sánh mô hình, báo cáo 3 seed, README dữ liệu. |
| `matrix_data/` | Ma trận tác vụ-nhân sự, danh mục loại việc và định mức giờ. |
| `SHA256SUMS.txt` | Mã băm các file mô hình; kiểm tra bằng `sha256sum -c SHA256SUMS.txt`. |

## 3. Huấn luyện lại
1. Tải `du_lieu_co_dinh_v2.zip` (hoặc bản seed) lên Colab cùng notebook tương ứng, chọn GPU T4, `MODE='quick'` kiểm tra luồng rồi `'full'`. Dữ liệu và `verify_data.py` không nằm trong gói này.
2. Nếu TabPFN không dùng được, `train_model.py` **dừng** (không có chế độ thay thế bằng mô hình khác).
3. Kiểm tra `metrics.json`: `main_model = tabpfn`, `device = cuda`, `meta.versions` đủ; ghi đúng kết quả `target_check`, không chỉnh ngưỡng sau khi xem test.

## 4. Dịch vụ suy luận
```
cd service
pip install -r requirements.txt
python test_ml_service.py                  # 3 kịch bản, không cần GPU/TabPFN thật
uvicorn ml_service:app --port 8001         # động cơ mặc định: TabPFN (GPU nếu có; CPU có thể chậm, chưa đo)
ML_ENGINE=surrogate_hgb uvicorn ml_service:app --port 8001     # bản demo CPU, KHÔNG phải TabPFN
```
* Nếu không nạp được TabPFN, `/health` trả `degraded` và `/predict` trả 503 kèm lý do (không âm thầm đổi mô hình).
* `surrogate_hgb` chỉ bật khi chủ động chọn: 4 bộ HistGradientBoosting huấn luyện trên các túi ngữ cảnh lúc khởi động. AUC test v2 = **0,7991** (TabPFN 0,8090). Ngưỡng riêng trong `cpu_surrogate.json` (chọn trên validation). Phản hồi ghi `engine_validated=false`. Có thể xóa hẳn khối `_load_surrogate` nếu không cần demo.
* Phản hồi thêm các trường `engine`, `engine_validated`, `missing_features`; `low_confidence` cũng bật khi thiếu hơn 25% trường đầu vào.
* Dịch vụ dùng đúng phiên bản TabPFN lưu trong bundle (`create_default_for_version`), không dùng phiên bản mặc định của gói.
* **Chưa kiểm chứng:** chạy TabPFN thật trong dịch vụ (cần `tabpfn==9.2.0`, trọng số mô hình, GPU khuyến nghị) và thời gian suy luận của nó.

## 5. Hạn chế cần ghi vào báo cáo
* Dữ liệu mô phỏng, một seed cho TabPFN; mô hình đối chứng CPU nhân bản trên 3 seed (xem `BAO_CAO_3_SEEDS.md`): mức chênh giữa ba mô hình nhỏ, thứ hạng không nhất quán.
* Tĩnh: TabPFN ngang CatBoost; ưu điểm rõ nhất là ECE thấp hơn. Động: hơn CatBoost +0,0038 AUC.
* Biến tiến độ trong bộ sinh được tạo từ nhãn ẩn, nên mức tăng AUC (+0,0254 [+0,0216; +0,0294] khi so CatBoost có và không có tiến độ) phụ thuộc giả định.
* Mô-đun học tiếp mới được mô phỏng với mô hình HGB, chưa tích hợp vào web; `.joblib` là pickle, chỉ nạp file từ nguồn tin cậy và đúng `scikit-learn==1.6.1`.
