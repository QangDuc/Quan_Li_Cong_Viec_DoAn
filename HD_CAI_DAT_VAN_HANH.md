# Hướng dẫn Cài đặt & Vận hành Hệ thống Quản lý Công việc Khoa CNTT

> **Khóa luận tốt nghiệp CNTT-KLCN184 (HUIT, 2026–2027)**  
> **Đề tài:** Xây dựng hệ thống quản lý công việc và tối ưu hóa phân công bằng Học máy tại Khoa Công nghệ Thông tin  
> **GVHD:** TS. Nguyễn Văn Lễ

---

## 1. Kiến trúc Hệ thống

1. **Backend API (`backend/app/main.py` — Port 8000):** Xử lý xác thực JWT, phân quyền 3 vai trò (`admin`, `manager`, `lecturer`), giao việc cá nhân/nhóm, cập nhật tiến độ `%`, xin và phê duyệt gia hạn, import kế hoạch năm, ánh xạ danh mục cấp Trường, chỉnh sửa định mức giờ chuẩn quy đổi theo **Thông tư 20/2020/TT-BGDĐT**, thống kê học kỳ/năm học và xuất báo cáo Excel (`.xlsx`).
2. **ML Inference Service (`backend/ml_service.py` — Port 8001 & tích hợp trực tiếp):** Nạp mô hình `model/risk_model.joblib` (`TabPFN v2`, 4 túi $\times$ 10.000 dòng ngữ cảnh), trích xuất đủ **58 đặc trưng** từ CSDL SQL Server (`backend/app/ml_extract.py`) và trả về xác suất trễ hạn, mức nguy cơ (`Thấp < 22%`, `Trung bình 22% – 44%`, `Cao ≥ 44%`), khuyến nghị hành động cùng các yếu tố giải thích tiếng Việt. Khi dịch vụ ML tắt hoặc quá thời gian chờ, luồng giao việc vẫn hoạt động bình thường.
3. **Cơ sở dữ liệu (`Microsoft SQL Server` — Database `qlcv`):** Gồm 13 bảng quan hệ lưu trữ cấu trúc 4 Bộ môn (`K01..K04`), 35 loại công việc chuyên môn (3 mức quy mô/loại), danh mục cấp Trường, lịch học vụ và nhật ký đối chiếu dự báo Học máy.
4. **Giao diện Web (`frontend/` — React 19 + TypeScript + Vite — Port 5173):** Thiết kế tinh gọn gồm 4 phân hệ nghiệp vụ hằng ngày:
   - `Công việc & Duyệt gia hạn`
   - `Giao việc mới`
   - `Báo cáo & Hồ sơ Giảng viên`
   - `Kế hoạch năm & Định mức giờ chuẩn` (kèm `Quản trị Tài khoản` cho Admin)

---

## 2. Các bước Cài đặt & Khởi chạy trên Windows (LocalDB)

### Bước 1: Khởi tạo SQL Server LocalDB
Mở **PowerShell** tại thư mục gốc `Quan_Li_Cong_Viec_DoAn`:

```powershell
# Khởi động LocalDB
sqllocaldb start MSSQLLocalDB

# Tạo database qlcv nếu chưa có
sqlcmd -S "(localdb)\MSSQLLocalDB" -Q "IF DB_ID('qlcv') IS NULL CREATE DATABASE qlcv;"
```

### Bước 2: Cài đặt thư viện Python và nạp dữ liệu mẫu
```powershell
# Tạo môi trường ảo (nếu chưa tạo)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Cài đặt thư viện
pip install -r requirements.txt
pip install fastapi uvicorn pydantic sqlalchemy alembic pyodbc pyjwt bcrypt python-multipart openpyxl httpx pytest

# Tạo bảng và nạp dữ liệu mẫu (bao gồm Hồ sơ 1 năm của giảng viên GV0101)
cd backend
..\.venv\Scripts\python.exe -m app.seed --reset
cd ..
```

### Bước 3: Chạy Backend và Frontend
Mở 2 cửa sổ PowerShell:

- **Terminal 1 (Backend FastAPI — Port 8000):**
```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Terminal 2 (Frontend React — Port 5173):**
```powershell
cd frontend
npm install
npm run dev
```

Sau khi khởi chạy, mở trình duyệt tại địa chỉ: **`http://localhost:5173`**

---

## 3. Chạy bằng Docker Compose

```bash
docker compose up --build -d
```
- Giao diện Web: `http://localhost:5173`
- Backend API & Swagger UI: `http://localhost:8000/docs`
- ML Service Health Check: `http://localhost:8001/health`

---

## 4. Tài khoản Đăng nhập Mẫu

| Tên đăng nhập | Mật khẩu | Vai trò | Mô tả |
|---|---|---|---|
| `truongkhoa` | `Manager@123` | Trưởng Khoa (`manager`) | Toàn quyền giao việc, duyệt gia hạn, sửa bảng định mức giờ chuẩn, xem báo cáo toàn Khoa |
| `gv_k01_1` | `Lecturer@123` | Giảng viên (`lecturer`) | Hồ sơ mẫu 1 năm học (ThS. Nguyễn Minh Khoa – `GV0101`, 18 công việc qua HK1, HK2, Hè) |
| `tbm_k01` | `Manager@123` | Trưởng Bộ môn (`manager`) | Quản lý công việc và xem dự báo rủi ro thuộc Bộ môn Công nghệ Phần mềm (`K01`) |
| `admin` | `Admin@123` | Quản trị viên (`admin`) | Quản lý người dùng, phân quyền và cấu hình danh mục hệ thống |

---

## 5. Kiểm thử Hệ thống & Xây dựng bản Production

```powershell
# 1. Chạy 7 bài kiểm thử tự động Backend & ML Features (Pytest)
cd backend
..\.venv\Scripts\python.exe -m pytest tests/ -v

# 2. Kiểm tra đóng gói bản dựng Frontend Production
cd ..\frontend
npm run build
```
