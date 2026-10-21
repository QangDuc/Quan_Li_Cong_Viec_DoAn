# Hệ thống Quản lý Công việc và Tối ưu hóa Phân công bằng Học máy tại Khoa CNTT
> **Khóa luận tốt nghiệp Cử nhân ngành CNTT — Năm học 2026–2027**  
> **Trường Đại học Công Thương TP.HCM (HUIT) — Khoa Công nghệ Thông tin**  
> **Mã đề tài:** `CNTT-KLCN184`  
> **Đề tài:** *Xây dựng hệ thống quản lý công việc và tối ưu hóa phân công bằng Học máy tại Khoa Công nghệ Thông tin*  
> **GVHD:** TS. Nguyễn Văn Lễ

---

## 1. Giới thiệu tổng quan
Dự án bao gồm **Hệ thống Web Quản lý Công việc Khoa CNTT** (FastAPI + SQL Server + React/TypeScript) tích hợp trực tiếp **Module Học máy Dự báo Nguy cơ Trễ hạn (`TabPFN v2`)**:

- **Nghiệp vụ Quản lý Công việc Khoa CNTT:**
  - Phân quyền 3 vai trò (`Admin`, `Manager` – Trưởng Khoa / Trưởng Bộ môn, `Lecturer` – Giảng viên).
  - Giao việc cá nhân/nhóm, theo dõi tiến độ `%`, tự động quét nhắc hạn công việc sắp đến hạn ($\le 5$ ngày) và quá hạn.
  - Xin gia hạn và phê duyệt gia hạn công việc (tự động cập nhật hạn mới và tính lại dự báo rủi ro).
  - Import kế hoạch năm học từ CSV, ánh xạ danh mục công việc cấp Trường, thống kê theo Năm học / Học kỳ (`HK1`, `HK2`, `Học kỳ Hè`) và xuất báo cáo Excel (`.xlsx`) đa trang tính.
  - **Định mức giờ chuẩn quy đổi theo Thông tư 20/2020/TT-BGDĐT:** Chuẩn hóa khung 270 giờ chuẩn giảng dạy/năm (135 giờ/học kỳ) và bảng quy đổi 35 loại công việc theo 3 mức quy mô (`nhỏ`, `chuẩn`, `lớn`), cho phép Trưởng Khoa / Admin chỉnh sửa trực tiếp trên giao diện Web.
- **Module Học máy (`TabPFN v2`):**
  - Sử dụng **58 đặc trưng** từ hồ sơ giảng viên, tải công việc đang mở, áp lực thời hạn và **Ma trận Tác vụ – Nhân sự (Task–Personnel Matrix)**.
  - Bagging đa túi (4 túi $\times$ 10.000 dòng ngữ cảnh), đạt **Test AUC = 0.8200**, **PR-AUC = 0.6054**, **Brier Score = 0.1367**, **ECE = 0.0211**.
  - Phân tầng 3 mức nguy cơ theo ngưỡng hiệu chuẩn Wilson 95% **`[0.22, 0.44]`** (`Thấp < 22%`, `Trung bình 22% – 44%`, `Cao ≥ 44%`) kèm giải thích nguyên nhân bằng tiếng Việt và cơ chế tự động đối chiếu độ chính xác sau khi công việc hoàn thành 100%.

---

## 2. Cấu trúc thư mục dự án

```text
.
├── README.md                          # Hướng dẫn tổng quan, cài đặt và vận hành
├── HD_CAI_DAT_VAN_HANH.md             # Tài liệu hướng dẫn cài đặt & vận hành chi tiết
├── requirements.txt                   # Thư viện Python cho Backend & ML
├── docker-compose.yml                 # Cấu hình chạy toàn hệ thống bằng Docker Compose
├── Dockerfile.backend                 # Dockerfile cho Backend FastAPI (Port 8000)
├── Dockerfile.ml                      # Dockerfile cho ML Service (Port 8001)
├── features.py                        # Định nghĩa 58 đặc trưng và hàm trích xuất
├── train_model.py                     # Script huấn luyện và suy luận mô hình TabPFN v2
├── build_task_personnel_matrix.py     # Xây dựng ma trận tác vụ - nhân sự
├── clean_data.py                      # Tiền xử lý và làm sạch dữ liệu
├── compare_models.py                  # Đối sánh TabPFN v2 với CatBoost, LightGBM, XGBoost
├── report_levels.py                   # Phân tích ngưỡng cảnh báo [0.22, 0.44]
├── model/
│   ├── risk_model.joblib              # Mô hình TabPFN v2 đã huấn luyện
│   ├── metrics.json                   # Kết quả đánh giá thực nghiệm trên tập Val/Test
│   ├── train_report.txt               # Báo cáo chi tiết phiên huấn luyện
│   └── bao_cao_muc_canh_bao.json      # Thống kê phân tầng mức cảnh báo rủi ro
├── data/
│   ├── task_personnel_matrix.csv      # Ma trận tác vụ - nhân sự chi tiết
│   ├── task_personnel_matrix_wide.csv # Ma trận tác vụ - nhân sự dạng rộng
│   └── data_dictionary.csv            # Từ điển mô tả 58 đặc trưng
├── backend/
│   ├── ml_service.py                  # Microservice suy luận ML độc lập (Port 8001)
│   ├── app/                           # Mã nguồn Backend FastAPI (Port 8000)
│   │   ├── main.py                    # Điểm vào ứng dụng FastAPI
│   │   ├── models.py                  # Lược đồ 13 bảng CSDL SQLAlchemy
│   │   ├── seed.py                    # Khởi tạo CSDL, định mức Thông tư 20/2020 & Hồ sơ 1 năm
│   │   ├── ml_extract.py              # Trích xuất 58 đặc trưng trực tiếp từ SQL Server
│   │   ├── routers_auth.py            # API Xác thực JWT & Quản lý người dùng
│   │   ├── routers_tasks.py           # API Giao việc, Tiến độ %, Gia hạn & Dự báo ML
│   │   ├── routers_reports.py         # API Thống kê, Hồ sơ 1 năm, Kế hoạch năm & Xuất Excel
│   │   └── routers_common.py          # API Danh mục loại việc, Định mức giờ chuẩn & Thông báo
│   └── tests/                         # Bộ kiểm thử tự động Pytest (Unit & Integration tests)
└── frontend/                          # Ứng dụng giao diện Web (React 19 + TypeScript + Tailwind CSS)
```

---

## 3. Hướng dẫn Cài đặt và Chạy Hệ thống trên Windows (Khuyến nghị)

### Bước 1: Khởi động CSDL Microsoft SQL Server LocalDB
Mở **PowerShell** tại thư mục gốc của dự án và chạy:

```powershell
# 1. Khởi động dịch vụ SQL Server LocalDB
sqllocaldb start MSSQLLocalDB

# 2. Tạo cơ sở dữ liệu 'qlcv' (nếu chưa tồn tại)
sqlcmd -S "(localdb)\MSSQLLocalDB" -Q "IF DB_ID('qlcv') IS NULL CREATE DATABASE qlcv;"
```

### Bước 2: Cài đặt môi trường Python (`.venv`) và nạp dữ liệu mẫu
```powershell
# 1. Tạo và kích hoạt môi trường ảo Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Cài đặt đầy đủ thư viện
pip install -r requirements.txt
pip install fastapi uvicorn pydantic sqlalchemy alembic pyodbc pyjwt bcrypt python-multipart openpyxl httpx pytest

# 3. Khởi tạo 13 bảng CSDL, bảng định mức Thông tư 20/2020/TT-BGDĐT và Hồ sơ công tác 1 năm
cd backend
..\.venv\Scripts\python.exe -m app.seed --reset
cd ..
```

### Bước 3: Chạy Backend API (Port 8000) và Frontend Web (Port 5173)
Mở 2 cửa sổ PowerShell song song:

- **Cửa sổ 1 — Chạy Backend FastAPI (Port 8000):**
```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*(Tùy chọn: Nếu muốn chạy thêm ML Microservice tách rời ở cổng `8001`, chạy `.\.venv\Scripts\python.exe -m uvicorn backend.ml_service:app --host 127.0.0.1 --port 8001` từ thư mục gốc. Nếu không bật cổng 8001, Backend cổng 8000 sẽ tự động nạp mô hình trực tiếp để dự báo).*

- **Cửa sổ 2 — Chạy Frontend React/Vite (Port 5173):**
```powershell
cd frontend
npm install
npm run dev
```

Mở trình duyệt truy cập: **`http://localhost:5173`** (Tài liệu Swagger API tại: `http://127.0.0.1:8000/docs`).

---

## 4. Chạy bằng Docker Compose (Một lệnh duy nhất)

Nếu máy đã cài đặt **Docker Desktop**:
```bash
docker compose up --build -d
```
Hệ thống tự động khởi chạy 4 container:
- `huit_sqlserver` (SQL Server 2022): cổng `1433`
- `huit_ml_service` (TabPFN v2 ML Service): cổng `8001`
- `huit_backend_api` (FastAPI Backend + tự động seed CSDL): cổng `8000`
- `huit_frontend_ui` (Giao diện Web React): cổng `5173` (`http://localhost:5173`)

---

## 5. Tài khoản Đăng nhập Kiểm thử (Hỗ trợ chọn nhanh trên màn hình Đăng nhập)

| Tài khoản | Mật khẩu | Vai trò | Họ tên & Đơn vị | Chức năng kiểm thử chính |
|---|---|---|---|---|
| `truongkhoa` | `Manager@123` | Trưởng Khoa (`manager`) | TS. Nguyễn Văn Lễ (Khoa CNTT) | Giao việc mới kèm gợi ý ML, duyệt gia hạn, sửa định mức giờ chuẩn, xem thống kê toàn Khoa & hồ sơ 1 năm của mọi giảng viên |
| `gv_k01_1` | `Lecturer@123` | Giảng viên (`lecturer`) | ThS. Nguyễn Minh Khoa (`GV0101` – Bộ môn CNPM) | **Hồ sơ công tác mẫu 1 năm (18 đầu việc)**: cập nhật tiến độ `%`, xin gia hạn, xem 370 giờ chuẩn quy đổi cá nhân |
| `tbm_k01` | `Manager@123` | Trưởng Bộ môn (`manager`) | PGS.TS. Hoàng Văn Minh (Bộ môn CNPM – K01) | Giao việc, duyệt gia hạn và theo dõi rủi ro trễ hạn trong phạm vi Bộ môn K01 |
| `admin` | `Admin@123` | Quản trị viên (`admin`) | Quản trị Hệ thống | Quản lý danh sách tài khoản, tạo người dùng mới, cấu hình danh mục và định mức giờ chuẩn |

---

## 6. Kiểm thử Tự động & Sử dụng Mô hình Học máy qua CLI

### 6.1. Chạy bộ kiểm thử tự động (Unit & Integration Tests)
```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests/ -v
```
*(Toàn bộ 7/7 bài kiểm thử kiểm chứng đăng nhập JWT, cô lập phân quyền RBAC, hồ sơ 1 năm giảng viên, trích xuất đủ 58 đặc trưng và suy luận ML chạy xanh 100%).*

### 6.2. Chạy dự đoán Học máy độc lập từ dòng lệnh (CLI)
Để chạy dự đoán hàng loạt cho một tệp công việc mới `viec_moi.csv` dựa trên dữ liệu lịch sử `lecturer_task_data.csv`:
```powershell
# 1. Làm sạch dữ liệu đầu vào ở chế độ inference
.\.venv\Scripts\python.exe clean_data.py --input viec_moi.csv --output viec_moi_clean.csv --inference

# 2. Gắn đặc trưng lịch sử và ma trận tác vụ - nhân sự (truyền tệp lịch sử gốc có cột is_late vào --data)
.\.venv\Scripts\python.exe build_task_personnel_matrix.py --data ./data/lecturer_task_data.csv --enrich viec_moi_clean.csv --out ./data --inference

# 3. Chạy dự đoán xác suất rủi ro kèm giải thích top factors
.\.venv\Scripts\python.exe train_model.py predict --model ./model/risk_model.joblib --input ./data/viec_moi_clean_with_matrix.csv --output ket_qua.csv --explain
```
