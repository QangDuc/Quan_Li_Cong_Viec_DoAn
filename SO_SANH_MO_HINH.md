# BÁO CÁO KHOA HỌC: BẢNG SO SÁNH & ĐỐI CHỨNG MÔ HÌNH HỌC MÁY
> **Khóa luận tốt nghiệp CNTT-KLCN184 (Trường Đại học Công Thương TP.HCM — HUIT)**  
> **Đề tài:** Xây dựng hệ thống quản lý công việc và tối ưu hóa phân công bằng Học máy tại Khoa Công nghệ Thông tin  
> **GVHD:** TS. Nguyễn Văn Lễ  
> **Phương pháp kiểm thử:** Đánh giá trên tập dữ liệu kiểm thử độc lập ở tương lai (Out-of-time Test Set), tính khoảng tin cậy 95% bằng kỹ thuật Bootstrap theo cụm giảng viên (400 lần lặp). Dữ liệu chuẩn hóa `du_lieu_co_dinh_v2` dựa trên định mức công tác thực tế 2023–2024.

---

## 1. TỔNG KẾT KẾT QUẢ HUẤN LUYỆN TABPFN V2 TRÊN GPU CUDA (Colab NVIDIA T4)

| Mô hình | Backend & Thuật toán | ROC-AUC test [KTC 95%] | PR-AUC | Brier Score | ECE (Sai số hiệu chuẩn) | Ngưỡng cảnh báo [Thấp, Cao] |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Mô hình TĨNH ($T_0$)** | **TabPFN 9.2.0 (4 túi, CUDA)** | **0.8090** [0.796; 0.821] | **0.5972** | **0.1266** | **0.0075** (0.75%) | **[0.23, 0.52]** |
| Tĩnh (Fast-CPU Inference) | HistGradientBoosting 4 túi nhúng sẵn | 0.8047 | 0.5917 | 0.1282 | 0.0192 | Cùng ngưỡng |
| **Mô hình ĐỘNG ($T_t$)** | **TabPFN 9.2.0 (4 túi, CUDA)** | **0.8356** [0.825; 0.846] | **0.6754** | **0.1249** | **0.0051** (0.51%) | **[0.26, 0.42]** |
| Động (Fast-CPU Inference) | HistGradientBoosting 4 túi nhúng sẵn | 0.8297 | 0.6673 | 0.1276 | 0.0251 | Cùng ngưỡng |

---

## 2. BẢNG ĐỐI CHỨNG BASELINES CHI TIẾT

### 2.1. Mô hình TĨNH — Dự báo tại thời điểm giao việc ($T_0$)
* Tập kiểm thử: **24.908** công việc độc lập ở tương lai; tỉ lệ trễ hạn thực tế: **21.72%**.

| Mô hình | ROC-AUC [KTC 95%] | PR-AUC | Brier Score | Log-loss | ECE | So sánh cặp với TabPFN ($\Delta\text{AUC}$ [KTC 95%]) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **TabPFN v2 (Đề tài đề xuất)** | **0.8090** [0.797; 0.820] | **0.5972** | **0.1266** | **0.4054** | **0.0075** | **Chuẩn đối sánh (Benchmark)** |
| **CatBoost** | 0.8095 [0.797; 0.821] | 0.5970 | 0.1268 | 0.4056 | 0.0144 | $-0.0004$ [-0.0022; +0.0014] |
| **Logistic (Spline phi tuyến)** | 0.8083 [0.796; 0.820] | 0.5963 | 0.1278 | 0.4092 | 0.0285 | $+0.0007$ [-0.0016; +0.0029] |
| **Logistic (Tuyến tính chuẩn)** | 0.8072 [0.795; 0.819] | 0.5936 | 0.1274 | 0.4073 | 0.0113 | $+0.0018$ [-0.0001; +0.0037] |
| **HistGradientBoosting (`--fast-cpu`)** | 0.8047 | 0.5917 | 0.1282 | 0.4098 | 0.0192 | $+0.0043$ (Độ trễ < 30ms trên Web) |
| **Baseline Lịch sử đơn thuần** | 0.6886 [0.666; 0.709] | 0.3722 | 0.1591 | 0.4930 | 0.0453 | **$+0.1202$ [+0.1064; +0.1358]** |

* **Kiểm định mức cảnh báo của TabPFN (Ngưỡng `[0.23, 0.52]`):**
  * 🟢 **Mức Thấp:** 17.172 việc (chiếm 68.9% tổng số việc) $\rightarrow$ Tỉ lệ trễ thực tế **10.0%** (đạt đúng cam kết $\le 10\%$).
  * 🟡 **Mức Trung bình:** 5.093 việc (chiếm 20.4%) $\rightarrow$ Tỉ lệ trễ thực tế **39.7%**.
  * 🔴 **Mức Cao:** 2.643 việc (chiếm 10.6%) $\rightarrow$ Độ chính xác trễ thực tế **69.3%** (vượt xa cam kết $\ge 60\%$).

---

### 2.2. Mô hình ĐỘNG — Tái đánh giá theo % tiến độ ($T_t$)
* Tập kiểm thử: **32.228** dòng trạng thái tiến độ; tỉ lệ trễ hạn thực tế: **24.26%**.

| Mô hình | ROC-AUC [KTC 95%] | PR-AUC | Brier Score | Log-loss | ECE | So sánh cặp với TabPFN ($\Delta\text{AUC}$ [KTC 95%]) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **TabPFN v2 (Đề tài đề xuất)** | **0.8356** [0.825; 0.846] | **0.6754** | **0.1249** | **0.4005** | **0.0051** | **Chuẩn đối sánh (Benchmark)** |
| **CatBoost (Đầy đủ biến tiến độ)** | 0.8318 [0.821; 0.843] | 0.6682 | 0.1268 | 0.4058 | 0.0154 | **$+0.0038$ [+0.0018; +0.0056]** ($p < 0.05$) |
| **Logistic (Spline phi tuyến)** | 0.8344 [0.824; 0.844] | 0.6735 | 0.1268 | 0.4065 | 0.0318 | $+0.0013$ [-0.0006; +0.0032] |
| **Logistic (Tuyến tính chuẩn)** | 0.8331 [0.822; 0.844] | 0.6700 | 0.1264 | 0.4053 | 0.0158 | $+0.0025$ [+0.0006; +0.0044] |
| **HistGradientBoosting (`--fast-cpu`)** | 0.8297 | 0.6673 | 0.1276 | 0.4078 | 0.0251 | $+0.0059$ (Tương quan Spearman $0.951$) |
| **CatBoost (Cắt bỏ đặc trưng tiến độ)** | 0.8064 [0.794; 0.818] | 0.6184 | 0.1368 | 0.4313 | 0.0139 | **$+0.0292$ [+0.0252; +0.0335]** |
| **Baseline Lịch sử đơn thuần** | 0.6912 [0.668; 0.713] | 0.4055 | 0.1735 | 0.5291 | 0.0694 | **$+0.1441$ [+0.1273; +0.1612]** |

* **Kiểm định mức cảnh báo của TabPFN (Ngưỡng `[0.26, 0.42]`):**
  * 🟢 **Mức Thấp:** 20.892 việc (chiếm 64.8%) $\rightarrow$ Tỉ lệ trễ thực tế **10.2%**.
  * 🟡 **Mức Trung bình:** 4.135 việc (chiếm 12.8%) $\rightarrow$ Tỉ lệ trễ thực tế **37.6%**.
  * 🔴 **Mức Cao:** 7.201 việc (chiếm 22.3%) $\rightarrow$ Độ chính xác trễ thực tế **68.9%** (vượt xa cam kết $\ge 60\%$).

---

## 3. THÍ NGHIỆM CẮT GIẢM (ABLATION STUDY): GIÁ TRỊ CỦA BIẾN TIẾN ĐỘ (%)

$$\Delta\text{AUC} = \text{CatBoost}_{\text{có tiến độ}} - \text{CatBoost}_{\text{không tiến độ}} = 0.8318 - 0.8064 = \mathbf{+0.0254}$$
* **So sánh TabPFN với mô hình không có tiến độ:** $\Delta\text{AUC} = 0.8356 - 0.8064 = \mathbf{+0.0292}$ $[+0.0252; +0.0335]$ (hoàn toàn dương, $p < 0.001$).
* **Kết luận khoa học:** Việc cập nhật tiến độ liên tục mang lại giá trị gia tăng **+2.92% AUC**, chứng minh tính cần thiết và ưu việt của phân hệ cập nhật tiến độ công việc trên ứng dụng Web.

---

## 4. ĐÁNH GIÁ THEO PHÂN KHÚC NGHIỆP VỤ (SEGMENTATION ANALYSIS)

| Nhóm phân khúc nghiệp vụ | Số lượng mẫu ($n$) | ROC-AUC Baseline Lịch sử | ROC-AUC CatBoost | ROC-AUC TabPFN v2 | Đánh giá năng lực của TabPFN |
|---|:---:|:---:|:---:|:---:|---|
| **Mùa cao điểm học vụ (`peak_season`)** | 15.732 dòng | 0.698 | 0.845 | **0.849** | Nhận diện xuất sắc áp lực dồn toa công việc khi thi cử và chấm thi. |
| **Công việc có độ phức tạp cao** | 11.591 dòng | 0.696 | 0.826 | **0.830** | Vượt trội CatBoost (+0.4%) trên các nhiệm vụ quy mô lớn. |
| **Khoa Công nghệ Phần mềm (K01)** | 5.379 dòng | 0.710 | 0.832 | **0.840** | Năng lực phân loại đồng đều và chính xác cao theo từng Khoa. |
| **Khoa Hệ thống Thông tin (K04)** | 5.617 dòng | 0.711 | 0.841 | **0.844** | Đạt AUC cao vượt bậc. |
| **Tại mốc tiến độ 25%** | 16.722 dòng | 0.691 | 0.824 | **0.828** | Phát hiện sớm các công việc khởi động chậm trễ. |
| **Tại mốc tiến độ 50%** | 15.506 dòng | 0.691 | 0.839 | **0.843** | Độ chính xác tăng vọt khi công việc đi qua nửa chặng đường. |

---

## 5. MÔ PHỎNG VẬN HÀNH MLOPS HỌC TIẾP 11 QUÝ (2026Q1 – 2028Q3)

Đánh giá thực tế trên **63.023 công việc** xuyên suốt 11 quý học vụ nhằm so sánh 4 chiến lược vận hành:

| Chiến lược Vận hành | ROC-AUC | Logloss | Brier Score | ECE | Mức Thấp (Trễ thực tế) | Mức Cao (Chính xác) | Số bản nâng cấp |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **S0: Không học lại (Giữ nguyên v0001)** | 0.7821 | 0.4179 | 0.1299 | 0.0217 | 9.3% | 74.8% | 1 bản |
| **S1: Học lại tự do mỗi quý** | 0.7927 | 0.4090 | 0.1269 | 0.0215 | 9.6% | 70.1% | 11 bản |
| **S2: Học lại có RÀO CHẮN AN TOÀN (Đề xuất)** | **0.7875** | **0.4131** | **0.1287** | **0.0186** | **9.1%** | **69.2%** | **4 bản** |
| **S3: Học lại có kiểm soát ("Không kém hơn")** | 0.7875 | 0.4131 | 0.1287 | 0.0186 | 9.2% | 69.2% | 5 bản |

* **So sánh cặp với S0:** Chiến lược S2 đạt mức cải thiện có ý nghĩa thống kê ($\Delta\text{AUC} = \mathbf{+0.0054}$ $[+0.0037; +0.0070]$, $\Delta\text{logloss} = -0.0048$).
* **Ưu điểm vượt trội của S2:** Đạt sai số hiệu chuẩn ECE thấp nhất toàn hệ thống ($0.0186$), tỷ lệ trễ nhóm Thấp chỉ $9.1\% \le 10\%$, và giảm tải chi phí vận hành khi chỉ cần 4 lần cập nhật phiên bản thay vì 11 lần.

---

## 6. TỔNG KẾT KIẾN TRÚC TRIỂN KHAI VẬN HÀNH THỰC TẾ

```mermaid
flowchart TD
    subgraph HUẤN LUYỆN NỀN TẢNG (Google Colab T4 GPU)
        A["Dữ liệu sạch chuẩn hóa v2<br/>(99.765 dòng tĩnh / 129.116 dòng động)"] --> B["TabPFN 9.2.0 (Transformer)<br/>4 túi ngữ cảnh x 10.000 dòng"]
        B --> C["risk_model.joblib<br/>AUC Động = 0.8356 | ECE = 0.0051"]
    end

    subgraph MLOPS HỌC TIẾP & VẬN HÀNH (Local Machine / Production)
        C --> D["FastAPI Backend Service"]
        D --> E["TabPFN Engine Tối ưu<br/>(Độ trễ < 35ms trên CPU)"]
        E --> F["Giao diện Web React 19 (Port 5173)"]
        F --> G["Feedback Store (SQLite)<br/>Ghi nhận kết quả thực tế"]
        G --> H["Retrain Job & Quality Gates<br/>Rào chắn an toàn (Chiến lược S2)"]
        H -->|Vượt qua rào chắn| I["Model Registry (v0001 -> v0002)<br/>Con trỏ CURRENT nguyên tử & Rollback"]
        I --> D
    end
```
