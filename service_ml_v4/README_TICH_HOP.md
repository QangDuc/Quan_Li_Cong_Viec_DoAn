# Hướng dẫn tích hợp dịch vụ dự đoán rủi ro trễ hạn vào web

Dữ liệu huấn luyện là **mô phỏng** (theo định mức giờ công tác của trường). Mọi chỉ số phản ánh khả năng học lại quy luật mô phỏng, không phải hiệu quả trên dữ liệu thật.

## 1. Kiến trúc
```
Web backend (FastAPI/SQLAlchemy)                         Dịch vụ ML (ml_service.py, cổng 8001)
 ml_client.predict_and_record_risk ──┐                    POST /predict  {features, explain}
   ml_extract.extract_features  ─────┤ build_features()   GET  /health
   (app/ml_features.py, academic.py) │  (58 trường)       Nạp model/risk_model.joblib + metrics.json
                                     └────────────────►   Động cơ: tabpfn (mặc định) | surrogate_hgb (demo CPU)
```
Backend tự dựng 58 trường đặc trưng (mô hình dùng 55) rồi gửi sang dịch vụ; dịch vụ chỉ mã hóa, suy luận và giải thích. Nếu dịch vụ lỗi, `ml_client` vẫn cho giao việc và ghi `RiskPrediction.status = failed`.

## 2. Các tệp cần đưa vào backend
| Tệp trong gói | Đặt vào backend | Ghi chú |
|---|---|---|
| `service/app/ml_features.py`, `service/app/academic.py` | `app/` | Dựng đặc trưng. `academic.py` dùng `app.config.ACADEMIC_YEAR_START` nếu có (mặc định `08-15`). |
| `service/ml_extract.py`, `service/ml_client.py` | `app/` | Đã import `app.models`, `app.config`: kiểm tra tên cột (mục 5). |
| `service/ml_service.py`, `model/`, `service/requirements.txt` | dịch vụ ML riêng | Có thể chạy cùng máy hoặc container (`Dockerfile.ml`). |
Cấu hình backend: `ML_SERVICE_URL=http://localhost:8001`, `ML_TIMEOUT_SECONDS` (xem mục 4).

## 3. Chạy dịch vụ
```
cd service
pip install -r requirements.txt
python demo_predict.py                          # thử nhanh 3 ca mẫu, không cần GPU
ML_ENGINE=surrogate_hgb uvicorn ml_service:app --port 8001    # bản demo CPU (AUC test 0,7991, engine_validated=false)
uvicorn ml_service:app --port 8001                            # TabPFN (cần tabpfn==9.2.0, trọng số, nên có GPU)
```
Biến môi trường: `ML_ENGINE` (tabpfn | surrogate_hgb), `ML_MODEL_DIR`, `TABPFN_DEVICE` (cuda | cpu), `MISSING_FEATURE_LIMIT` (mặc định 0,25).
Kiểm tra: `curl localhost:8001/health` phải có `status: ok`. Nếu `degraded`, đọc `load_error`.

## 4. Hợp đồng API
`POST /predict` — thân: `{"features": {<58 trường>}, "explain": true}`. `features` do `build_features()` trả về (xem `sample_requests.json`); trường thiếu gửi `null`.
Phản hồi 200: `probability` (0..1), `level` (Thấp | Trung bình | Cao), `uncertainty`, `top_factors` (danh sách chữ), `recommendation`, `low_confidence`, `model_version`, `engine`, `engine_validated`, `missing_features`, `unseen_categories`.
Mã lỗi: 503 mô hình chưa sẵn sàng (không âm thầm đổi mô hình), 422 sai cấu trúc, 500 lỗi nội bộ (chi tiết ở nhật ký dịch vụ).
Độ trễ: mỗi `/predict` có giải thích dùng khoảng 56 lượt suy luận. Ước tính từ nhật ký huấn luyện (chưa đo trên máy của bạn): vài giây trên GPU T4; TabPFN trên CPU có thể rất chậm. Khuyến nghị: `ML_TIMEOUT_SECONDS` từ 30 trở lên với TabPFN; hiện `ml_client` không gửi `explain`, nếu cần nhanh hãy gửi `"explain": false` ở màn hình xem trước. Với CPU, dùng `surrogate_hgb` (~140 ms/ca khi đo).
Một yêu cầu được xử lý tại một thời điểm (có khóa); chạy 1 worker uvicorn.

## 5. Việc PHẢI xác nhận trước khi chạy thật
1. **Tên cột ngày giao** trong `models.Task` / `models.TaskAssignment`: `ml_extract.py` lấy `a.task.assigned_at` (hoặc `a.assigned_at` / `a.created_at`), khớp với cột `Task.assigned_at` và `TaskAssignment.task_id` trong `app/models.py` của backend.
2. **Giờ công của việc đang mở** (`effort_hours` trong `ml_extract`): trong dữ liệu mô phỏng là `estimated_effort_hours` (giờ công ước lượng); web phải truyền cùng ý nghĩa.
3. **`expected_duration_days`** (thời lượng điển hình): web phải lấy từ danh mục loại việc, cùng thang với dữ liệu huấn luyện (xem `matrix_data/task_catalog_norm.csv`).
4. **Giá trị phân loại**: `department_ml`, `task_type`, `assignment_channel`... phải khớp danh sách lúc huấn luyện. Giá trị lạ không gây lỗi nhưng được coi là thiếu; dịch vụ báo ở `unseen_categories` và hạ `low_confidence`.
5. **Lịch năm học** `ACADEMIC_YEAR_START` (mặc định 15/08, giả định của bộ sinh).

## 6. Hiển thị trên giao diện (khuyến nghị)
- Hiện `level`, `probability` (làm tròn %), `recommendation`, `top_factors`.
- Hiện nhãn "Bản demo" khi `engine_validated = false`; hiện cảnh báo khi `low_confidence = true` (giảng viên mới, thiếu trường, hoặc giá trị lạ).
- Lưu `model_version` cùng mỗi dự đoán (đã có trong `RiskPrediction`) để truy vết.
- Dự đoán chỉ là gợi ý; không dùng để đánh giá giảng viên.

## 7. Kiểm thử
`python ../run_all_tests.py` (gốc gói) chạy: dịch vụ, tương đương đặc trưng với bộ sinh (56/58 đặc trưng khớp 100%, `deadline_month_end` lệch ~1,6% và là giới hạn đã biết), dựng đặc trưng và học tiếp.
Kiểm thử end-to-end trên web: giao 3 việc tương ứng 3 ca mẫu, kỳ vọng mức Thấp, Trung bình, Cao.

## 8. Học tiếp tự động (TabPFN + GPU, hằng quý)
Đã có chế độ tự động: job theo lịch huấn luyện lại, so sánh có rào chắn, nâng cấp, dịch vụ tự nạp lại và tự quay lại nếu lỗi. Hướng dẫn đầy đủ ở `hoc_tiep_mlops/README_HOC_TIEP.md` mục 8. Tóm tắt phần web:
1. Chép `service/hoc_tiep_hook.py` vào `app/`; đặt `HOC_TIEP_DB` và `HOC_TIEP_PATH` cho backend (`ml_client.py` đã gọi `log_prediction` sau mỗi dự đoán thành công).
2. Gọi `hoc_tiep_hook.record_outcome(...)` khi phân công hoàn thành và `record_intervention(...)` khi quản lý can thiệp (backend của bạn, nơi xử lý hoàn thành việc).
3. Dịch vụ ML chạy với `ML_REGISTRY_DIR` và `ML_ADMIN_TOKEN`; `/health` thêm trường `registry_version`.
4. Hai quý đầu để `--mode dry-run`, sau đó mới `--mode auto`; điều chỉnh rào chắn theo lượng việc thật của khoa.
