# Mô hình Học máy Dự đoán Rủi ro Trễ hạn & Tối ưu hóa Phân công
> **Khóa luận tốt nghiệp Cử nhân ngành CNTT — Năm học 2026–2027**  
> **Trường Đại học Công Thương TP.HCM (HUIT) — Khoa Công nghệ Thông tin**  
> **Mã đề tài:** `CNTT-KLCN184`  
> **Đề tài:** *Xây dựng hệ thống quản lý công việc và tối ưu hóa phân công bằng Học máy tại Khoa Công nghệ Thông tin*  
> **GVHD:** ThS./TS. Nguyễn Văn Lễ

---

## 1. Giới thiệu mô hình
Repository này lưu trữ toàn bộ **mã nguồn, mô hình đã huấn luyện và dữ liệu ma trận đặc trưng** phục vụ module Học máy (Machine Learning) của đồ án:

- **Kiến trúc chính:** `TabPFN v2` (Tabular Foundation Model dựa trên Transformer với cơ chế In-Context Learning).
- **Kỹ thuật mở rộng:** Bagging đa túi (4 túi $\times$ 10.000 dòng ngữ cảnh), kết hợp lấy trung bình xác suất để tăng độ ổn định và giảm phương sai.
- **Ma trận đặc trưng tác vụ – nhân sự (Task–Personnel Matrix):** Tổng hợp lịch sử tương tác giữa từng giảng viên và từng loại công việc (`lecturer_task_late_rate`, làm mịn Laplace smoothing và cơ chế prior cấp Bộ môn khi cold-start).
- **Phân tầng mức cảnh báo:** Ngưỡng được xác định tự động trên tập Validation với biên an toàn Wilson 95% (chia thành 3 mức: `Thấp`, `Trung bình`, `Cao`).
- **Khả năng giải thích (Explainability):** Bóc tách đóng góp của các yếu tố chính làm tăng / giảm rủi ro (**Top factors**) so với mức điển hình.

---

## 2. Cấu trúc thư mục

```
.
├── README.md
├── requirements.txt                   # Thư viện Python cần thiết
├── train_model.py                     # Script HUẤN LUYỆN và DỰ ĐOÁN (TabPFN)
├── build_task_personnel_matrix.py     # Xây dựng & bổ sung ma trận tác vụ - nhân sự
├── clean_data.py                      # Làm sạch dữ liệu và tiền xử lý inference
├── compare_models.py                  # So sánh TabPFN với CatBoost & Logistic Regression
├── report_levels.py                   # Tái tạo bảng báo cáo mức cảnh báo rủi ro
├── model/
│   ├── risk_model.joblib              # Mô hình đã huấn luyện (ngữ cảnh + bộ mã hóa + baseline)
│   ├── metrics.json                   # Báo cáo các chỉ số định lượng (AUC, Brier, ECE, phân đoạn)
│   ├── train_report.txt               # Nhật ký chi tiết của phiên huấn luyện
│   └── bao_cao_muc_canh_bao.json      # Bảng phân phối và độ chính xác theo 3 mức cảnh báo
└── data/
    ├── task_personnel_matrix.csv      # Ma trận tác vụ - nhân sự chi tiết
    ├── task_personnel_matrix_wide.csv # Bảng ma trận dạng rộng (dùng cho báo cáo/heatmap)
    └── data_dictionary.csv            # Từ điển dữ liệu mô tả các đặc trưng
```

---

## 3. Cài đặt môi trường

```bash
# Khuyến nghị dùng Python 3.10 trở lên
pip install -r requirements.txt
```

---

## 4. Hướng dẫn sử dụng mô hình

### 4.1. Chạy dự đoán trực tiếp từ dòng lệnh (CLI)
Để dự đoán cho danh sách công việc mới (ví dụ `viec_moi.csv`):

```bash
# 1. Tiền xử lý dữ liệu mới
python clean_data.py --input viec_moi.csv --output viec_moi_clean.csv --inference

# 2. Gắn đặc trưng từ ma trận tác vụ - nhân sự
python build_task_personnel_matrix.py --data ./data/task_personnel_matrix.csv --enrich viec_moi_clean.csv --out ./data --inference

# 3. Chạy dự đoán xác suất rủi ro kèm giải thích top factors
python train_model.py predict --model ./model/risk_model.joblib --input ./data/viec_moi_clean_with_matrix.csv --output ket_qua.csv --explain
```

### 4.2. Nạp mô hình trong mã nguồn Python (dành cho thành viên tích hợp Backend)
Thành viên xây dựng backend chỉ cần nạp file `.joblib` và gọi dự đoán:

```python
import joblib
import pandas as pd

# 1. Nạp mô hình
bundle = joblib.load("model/risk_model.joblib")

# Xem ngưỡng cảnh báo
thresholds = bundle["thresholds"]  # [0.22, 0.44]
print("Ngưỡng rủi ro:", thresholds)

# Xem các đặc trưng yêu cầu
print("Danh sách đặc trưng mô hình:", bundle["features"])
```

---

## 5. Kết quả thực nghiệm trên tập Test (Độc lập theo thời gian)

| Chỉ số đánh giá | Kết quả | Ý nghĩa học thuật |
|---|:---:|---|
| **ROC-AUC** | **0.820** | Khả năng phân biệt công việc trễ hạn đạt mức Rất tốt |
| **PR-AUC** | **0.605** | Độ chính xác trung bình trên tập mất cân bằng nhãn |
| **Brier Score** | **0.115** | Sai số bình phương trung bình của xác suất dự đoán |
| **ECE (Expected Calibration Error)** | **0.021** | Độ lệch hiệu chuẩn cực thấp (xác suất dự đoán rất sát thực tế) |
| **Bootstrap 95% CI** | **[0.807 – 0.830]** | Khoảng tin cậy theo cụm giảng viên |

### Phân tầng mức cảnh báo trên tập Test:
* **Mức Thấp** ($P \le 0.22$): Chiếm **74.9%** số việc, tỉ lệ trễ thực tế chỉ **9.5%** (đạt mục tiêu $\le 10\%$).
* **Mức Trung bình** ($0.22 < P < 0.44$): Chiếm **13.8%** số việc, tỉ lệ trễ thực tế **35.1%**.
* **Mức Cao** ($P \ge 0.44$): Chiếm **11.3%** số việc, tỉ lệ trễ thực tế lên tới **69.6%** (đạt mục tiêu cảnh báo chính xác $\ge 60\%$).
