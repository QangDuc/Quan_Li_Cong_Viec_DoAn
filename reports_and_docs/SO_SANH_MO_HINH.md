# BÁO CÁO KHOA HỌC: BẢNG SO SÁNH & ĐỐI CHỨNG MÔ HÌNH HỌC MÁY
> **Khóa luận tốt nghiệp CNTT-KLCN184 (Trường Đại học Công Thương TP.HCM — HUIT)**  
> **Đề tài:** Xây dựng hệ thống quản lý công việc và tối ưu hóa phân công bằng Học máy tại Khoa Công nghệ Thông tin  
> **GVHD:** TS. Nguyễn Văn Lễ  
> **Phương pháp kiểm thử:** Đánh giá trên tập dữ liệu kiểm thử độc lập ở tương lai (Out-of-time Test Set), tính khoảng tin cậy 95% bằng kỹ thuật Bootstrap theo cụm giảng viên (400 lần lặp). Dữ liệu chuẩn hóa `du_lieu_co_dinh_v2` dựa trên định mức công tác thực tế 2023–2024.

---

## 1. Tổng kết kết quả huấn luyện TabPFN v2 (GPU CUDA, Colab T4)

| Mô hình | Backend | ROC-AUC test [KTC 95%] | PR-AUC | Brier | ECE | Ngưỡng [Thấp, Cao] |
|---|---|:---:|:---:|:---:|:---:|:---:|
| Tĩnh ($T_0$) | TabPFN 9.2.0 (4 túi, CUDA) | 0.8090 [0.797; 0.820] | 0.5972 | 0.1266 | 0.0075 | [0.23, 0.52] |
| Động ($T_t$) | TabPFN 9.2.0 (4 túi, CUDA) | 0.8356 [0.825; 0.846] | 0.6754 | 0.1249 | 0.0051 | [0.26, 0.42] |

Dữ liệu là **mô phỏng**; chỉ số phản ánh khả năng học lại quy luật đã mô phỏng, không phải hiệu quả trên dữ liệu thật. Hai mô hình dùng tập test khác nhau (24.908 và 32.228 dòng, tỉ lệ trễ khác nhau) nên **không so trực tiếp AUC tĩnh với AUC động**. Mục tiêu nhóm Thấp (trễ <= 10%) không đạt trên test ở cả hai mô hình; mục tiêu nhóm Cao (chính xác >= 60%) đạt.

---

## 2. Bảng đối chứng chi tiết

### 2.1. Mô hình tĩnh: dự báo tại thời điểm giao việc
* Tập test: **24.908** công việc; tỉ lệ trễ thực tế **21.72%**.

| Mô hình | ROC-AUC [KTC 95%] | PR-AUC | Brier | Log-loss | ECE | TabPFN trừ mô hình này ($\Delta$AUC [KTC 95%]) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| TabPFN v2 | 0.8090 [0.797; 0.820] | 0.5972 | 0.1266 | 0.4054 | 0.0075 | (chuẩn) |
| CatBoost | 0.8095 [0.797; 0.821] | 0.5970 | 0.1268 | 0.4056 | 0.0144 | -0.0004 [-0.0022; +0.0014] |
| Logistic (spline) | 0.8083 [0.796; 0.820] | 0.5963 | 0.1278 | 0.4092 | 0.0285 | +0.0007 [-0.0016; +0.0029] |
| Logistic (tuyến tính) | 0.8072 [0.795; 0.819] | 0.5936 | 0.1274 | 0.4073 | 0.0113 | +0.0018 [-0.0001; +0.0037] |
| Baseline lịch sử | 0.6886 [0.666; 0.709] | 0.3722 | 0.1591 | 0.4930 | 0.0453 | +0.1202 [+0.1064; +0.1358] |

TabPFN **ngang CatBoost** về AUC (khoảng tin cậy chứa 0) và cao hơn nhẹ hai mô hình logistic nhưng khoảng tin cậy cũng chứa 0; ưu điểm rõ nhất là ECE thấp hơn.

Mức cảnh báo (ngưỡng [0.23; 0.52] chốt trên validation, không chỉnh sau khi xem test):

| Mức | Số việc | % số việc | Tỉ lệ trễ thực tế |
|---|---|---|---|
| Thấp | 17.172 | 68.9% | 10.04% (KHÔNG đạt mục tiêu <= 10%; Wilson 95% [9.60%; 10.50%]) |
| Trung bình | 4.927 | 19.8% | 35.30% |
| Cao | 2.809 | 11.3% | 69.31% (đạt mục tiêu >= 60%) |

### 2.2. Mô hình động: tái đánh giá theo % tiến độ
* Tập test: **32.228** dòng trạng thái; tỉ lệ trễ thực tế **24.26%**.

| Mô hình | ROC-AUC [KTC 95%] | PR-AUC | Brier | Log-loss | ECE | TabPFN trừ mô hình này ($\Delta$AUC [KTC 95%]) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| TabPFN v2 | 0.8356 [0.825; 0.846] | 0.6754 | 0.1249 | 0.4005 | 0.0051 | (chuẩn) |
| Logistic (spline) | 0.8344 [0.824; 0.844] | 0.6735 | 0.1268 | 0.4065 | 0.0318 | +0.0013 [-0.0006; +0.0032] |
| Logistic (tuyến tính) | 0.8331 [0.822; 0.844] | 0.6700 | 0.1264 | 0.4053 | 0.0158 | +0.0025 [+0.0006; +0.0044] |
| CatBoost (đầy đủ tiến độ) | 0.8318 [0.821; 0.843] | 0.6682 | 0.1268 | 0.4058 | 0.0154 | +0.0038 [+0.0018; +0.0056] |
| CatBoost (bỏ 7 cột tiến độ) | 0.8064 [0.794; 0.818] | 0.6184 | 0.1368 | 0.4313 | 0.0139 | +0.0292 [+0.0252; +0.0335] (gộp khác biệt mô hình và đặc trưng, xem mục 3) |
| Baseline lịch sử | 0.6912 [0.668; 0.713] | 0.4055 | 0.1735 | 0.5291 | 0.0694 | +0.1441 [+0.1273; +0.1612] |

TabPFN cao hơn CatBoost và logistic tuyến tính một cách có ý nghĩa thống kê (khoảng tin cậy không chứa 0) nhưng chênh lệch nhỏ (+0.0038 và +0.0025); so với logistic spline khoảng tin cậy chứa 0.

Mức cảnh báo (ngưỡng [0.26; 0.42]):

| Mức | Số việc | % số việc | Tỉ lệ trễ thực tế |
|---|---|---|---|
| Thấp | 22.161 | 68.8% | 10.26% (KHÔNG đạt mục tiêu <= 10%; Wilson 95% [9.86%; 10.66%]) |
| Trung bình | 3.672 | 11.4% | 33.52% |
| Cao | 6.395 | 19.8% | 67.49% (đạt mục tiêu >= 60%) |

---

## 3. Giá trị của biến tiến độ (ablation trên cùng một mô hình)

* So sánh **CatBoost có và không có 7 cột tiến độ** trên cùng tập động: $\Delta$AUC = 0.8318 - 0.8064 = **+0.0254** [+0.0216; +0.0294] (bootstrap theo cụm giảng viên, 400 lần).
* Con số +0.0292 (TabPFN so với CatBoost không tiến độ) gộp cả khác biệt về mô hình lẫn về đặc trưng nên **không dùng để đo riêng** đóng góp của tiến độ.
* **Điều kiện đi kèm:** trong bộ dữ liệu mô phỏng, biến tiến độ được tạo từ nhãn ẩn (nhịp làm việc của việc trễ khoảng 0.72 lần; việc trễ ít cập nhật tiến độ hơn: 18% so với 4%). Mức cải thiện phụ thuộc các giả định này, không phải bằng chứng trên dữ liệu thật.

---

## 4. Đánh giá theo phân khúc nghiệp vụ (mô hình động, tập test n = 32.228)

| Phân khúc | Số mẫu | Baseline lịch sử | Logistic (tuyến tính) | Logistic (spline) | CatBoost | TabPFN |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Mùa cao điểm học vụ | 15.732 | 0.698 | 0.847 | 0.848 | 0.845 | 0.849 |
| Công việc có độ phức tạp cao | 11.591 | 0.696 | 0.826 | 0.827 | 0.826 | 0.830 |
| Khoa K01 | 5.379 | 0.710 | 0.834 | 0.840 | 0.832 | 0.840 |
| Khoa K04 | 5.617 | 0.711 | 0.843 | 0.840 | 0.841 | 0.844 |
| Mốc tiến độ 25% | 16.722 | 0.691 | 0.826 | 0.827 | 0.824 | 0.828 |
| Mốc tiến độ 50% | 15.506 | 0.691 | 0.840 | 0.842 | 0.839 | 0.843 |

Trong mọi phân khúc, chênh lệch giữa TabPFN và các mô hình đối chứng không quá 0.008 và chưa được kiểm định thống kê. AUC ở mốc 50% cao hơn mốc 25% (0.843 so với 0.828), phù hợp với giả định của bộ mô phỏng về tín hiệu tiến độ; chưa kiểm định. Nhóm giảng viên mới (249 dòng) không tính được AUC (quá ít mẫu).

---

## 5. Mô phỏng vận hành học tiếp 11 quý (2026Q1 đến 2028Q3)

Mô phỏng dùng mô hình **HistGradientBoosting trên CPU (không phải TabPFN)**, dữ liệu mô phỏng, một lần chạy, trên 63.023 công việc. Mô-đun học tiếp (`hoc_tiep`) **chưa được tích hợp vào hệ thống web**.

| Chiến lược | ROC-AUC | Log-loss | Brier | ECE | Thấp: trễ thực tế | Cao: chính xác | Số phiên bản đã dùng |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| S0: giữ nguyên | 0.7821 | 0.4179 | 0.1299 | 0.0217 | 9.3% | 74.8% | 1 |
| S1: học lại mỗi quý, nâng cấp vô điều kiện | 0.7927 | 0.4090 | 0.1269 | 0.0215 | 9.6% | 70.1% | 11 |
| S2: có kiểm soát (rào chắn mặc định) | 0.7875 | 0.4131 | 0.1287 | 0.0186 | 9.1% | 69.2% | 4 |
| S3: có kiểm soát, chỉ cần "không kém" | 0.7875 | 0.4131 | 0.1287 | 0.0186 | 9.2% | 69.2% | 5 |

* So với S0: S1 $\Delta$AUC = +0.0106 [+0.0082; +0.0128]; S2 $\Delta$AUC = +0.0054 [+0.0037; +0.0070], $\Delta$logloss = -0.0048.
* **Rào chắn giữ lại khoảng một nửa mức cải thiện** của nâng cấp vô điều kiện (S2 so với S1) và dùng ít phiên bản hơn (4 so với 11). Dữ liệu mô phỏng sạch, không có lỗi dữ liệu hay hỏng pipeline, nên mô phỏng **không đo được lợi ích bảo vệ** của rào chắn; phần này chỉ được kiểm chứng bằng kiểm thử đơn vị.
* S2 và S3 có ECE thấp nhất (0.0186). Sau khi nâng cấp lên phiên bản thứ hai, S2 dự đoán trung bình cao hơn thực tế 2.5 đến 3.6 điểm phần trăm ở 2026Q4 đến 2027Q2: rào chắn dựa trên dữ liệu quá khứ không ngăn được lệch xảy ra sau khi nâng cấp, nên cần giám sát hiệu chuẩn (mô-đun `monitor.py`).

---

## 6. Kiến trúc

```mermaid
flowchart TD
    subgraph HUẤN LUYỆN (Google Colab, GPU)
        A["Dữ liệu v2 (99.765 dòng tĩnh / 129.116 dòng động)"] --> B["TabPFN 9.2.0, 4 túi ngữ cảnh x 10.000 dòng"]
        B --> C["risk_model.joblib (ngữ cảnh, bộ mã hóa, ngưỡng)"]
    end
    subgraph DỊCH VỤ SUY LUẬN
        C --> D["FastAPI ml_service (động cơ TabPFN mặc định)"]
        D -.->|tùy chọn demo, KHÔNG đánh giá| D2["Động cơ thay thế surrogate_hgb (AUC test 0.7991)"]
        D --> F["Giao diện Web"]
    end
    subgraph HỌC TIẾP (mô-đun hoc_tiep, chưa tích hợp vào web)
        G["Kho phản hồi SQLite"] --> H["Retrain job và rào chắn"]
        H --> I["Kho phiên bản và quay lại"]
        G --> J["Giám sát hiệu chuẩn (monitor.py)"]
    end
```
