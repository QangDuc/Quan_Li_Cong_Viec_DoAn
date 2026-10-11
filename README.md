# HUIT Task Risk Prediction & Assignment Optimization Service
> **Hệ thống Quản lý Công việc và Tối ưu hóa Phân công bằng Học máy tại Khoa CNTT - Trường Đại học Công Thương TP.HCM (HUIT)**  
> **Mã đề tài:** CNTT-KLCN184

---

## 1. Giới thiệu
Repository này chứa toàn bộ mã nguồn đóng gói **Dịch vụ Học máy (ML API Service)** phục vụ tích hợp trực tiếp vào hệ thống Web Quản lý công việc (ASP.NET Core Backend + SQL Server + React Frontend).

### Chức năng chính:
1. **Dự đoán rủi ro trễ hạn (`/api/predict`)**:
   - Nhận các thuộc tính phân công công việc (loại việc, độ phức tạp, thời hạn, áp lực deadline, lịch sử giảng viên...).
   - Trả về xác suất trễ hạn $P \in [0, 1]$, phân tầng mức cảnh báo (`Thấp`, `Trung bình`, `Cao`) dựa trên ngưỡng an toàn Wilson 95%.
   - Cung cấp **Top factors**: Chỉ rõ nguyên nhân làm tăng hoặc giảm rủi ro (Explainability) so với mức điển hình để Trưởng khoa/bộ môn dễ dàng ra quyết định.
2. **Tối ưu hóa phân công công việc (`/api/recommend-assignee`)**:
   - Đánh giá tự động một danh sách các giảng viên ứng viên trong bộ môn.
   - Sắp xếp và đề xuất giảng viên phù hợp nhất (rủi ro trễ hạn thấp nhất, đảm bảo cân bằng khối lượng công việc).
3. **Tra cứu ma trận tác vụ - nhân sự**:
   - Tự động liên kết và tra cứu hiệu suất lịch sử theo từng loại việc (`lecturer_task_late_rate`).

---

## 2. Cấu trúc thư mục

```
task_risk_service/
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md
├── test_service.py              # Script test nhanh các hàm dự đoán
├── model/
│   ├── risk_model.joblib        # Model đã huấn luyện (ngữ cảnh + encoder + baseline)
│   ├── metrics.json             # Báo cáo chỉ số AUC, Brier, ECE, ngưỡng rủi ro
│   └── train_report.txt         # Nhật ký huấn luyện và kiểm định
├── data/
│   └── task_personnel_matrix.csv# Ma trận tác vụ - nhân sự (lookup)
├── service/
│   ├── __init__.py
│   ├── config.py                # Cấu hình cổng, đường dẫn file, ngưỡng
│   ├── schemas.py               # Pydantic Request/Response DTOs
│   ├── predictor.py             # Inference engine (TabPFN + Calibrated Proxy + Explainability)
│   └── main.py                  # FastAPI Application Entrypoint
└── clients/
    └── csharp/                  # Thư viện tích hợp sẵn cho ASP.NET Core
        ├── TaskRiskModels.cs
        ├── TaskRiskPredictionClient.cs
        └── README_ASPNET_INTEGRATION.md
```

---

## 3. Hướng dẫn cài đặt & Khởi chạy

### Cách 1: Khởi chạy trực tiếp bằng Python
```bash
# 1. Tạo môi trường ảo (khuyến nghị)
python -m venv .venv
# Trên Windows:
.venv\Scripts\activate
# Trên Linux/macOS:
source .venv/bin/activate

# 2. Cài đặt thư viện
pip install -r requirements.txt

# 3. Chạy service FastAPI
uvicorn service.main:app --host 0.0.0.0 --port 8000 --reload
```
Sau khi chạy, mở trình duyệt truy cập:
- **Swagger UI Interactive Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Cách 2: Khởi chạy bằng Docker Compose
```bash
docker compose up -d --build
```

---

## 4. Đặc tả API tích hợp (API Specification)

### 4.1. Dự đoán rủi ro phân công đơn lẻ
- **Endpoint:** `POST /api/predict`
- **Request Body (JSON):**
```json
{
  "task_id": "T056584",
  "lecturer_id": "GV226",
  "faculty": "CNTT",
  "department": "K05 - Công nghệ phần mềm",
  "task_type": "Chấm thi cuối kỳ",
  "priority": "Cao",
  "complexity": "Cao",
  "available_days": 5,
  "estimated_effort_hours": 20,
  "active_tasks": 14,
  "overdue_open_tasks": 1,
  "hist_late_rate": 0.35,
  "hist_count": 120
}
```
- **Response (JSON):**
```json
{
  "task_id": "T056584",
  "lecturer_id": "GV226",
  "risk_probability": 0.875,
  "risk_level": "Cao",
  "risk_uncertainty": 0.025,
  "top_factors": "Tăng rủi ro (so với mức điển hình): số việc đang mở = 14; tỉ lệ trễ lịch sử = 0.35; độ phức tạp = Cao",
  "notes": null
}
```

### 4.2. Gợi ý giảng viên tối ưu nhất để giao việc
- **Endpoint:** `POST /api/recommend-assignee`
- **Request Body (JSON):**
```json
{
  "task": {
    "task_id": "T099881",
    "task_type": "Hướng dẫn khóa luận/đồ án tốt nghiệp",
    "priority": "Cao",
    "complexity": "Cao",
    "available_days": 10,
    "estimated_effort_hours": 30
  },
  "candidate_lecturers": [
    { "lecturer_id": "GV001", "lecturer_name": "ThS. Nguyễn Văn A", "department": "CNPM", "active_tasks": 2, "overdue_open_tasks": 0 },
    { "lecturer_id": "GV002", "lecturer_name": "TS. Trần Thị B", "department": "CNPM", "active_tasks": 15, "overdue_open_tasks": 2 }
  ]
}
```
- **Response (JSON):**
```json
{
  "task_id": "T099881",
  "recommended_candidates": [
    {
      "rank": 1,
      "lecturer_id": "GV001",
      "lecturer_name": "ThS. Nguyễn Văn A",
      "department": "CNPM",
      "risk_probability": 0.165,
      "risk_level": "Thấp",
      "recommendation_note": "Ứng viên rất phù hợp: rủi ro trễ thấp, khối lượng công việc hiện tại đảm bảo."
    },
    {
      "rank": 2,
      "lecturer_id": "GV002",
      "lecturer_name": "TS. Trần Thị B",
      "department": "CNPM",
      "risk_probability": 0.892,
      "risk_level": "Cao",
      "recommendation_note": "Không khuyến khích: nguy cơ trễ cao do áp lực việc mở hoặc lịch sử hiệu suất."
    }
  ]
}
```

---

## 5. Hướng dẫn tích hợp với ASP.NET Core Backend
Mã nguồn C# mẫu đã được chuẩn bị sẵn tại thư mục:  
`clients/csharp/`
1. Copy file `TaskRiskModels.cs` và `TaskRiskPredictionClient.cs` vào project Web API của bạn.
2. Đăng ký client trong `Program.cs`:
   ```csharp
   builder.Services.AddHttpClient<ITaskRiskPredictionClient, TaskRiskPredictionClient>(client => {
       client.BaseAddress = new Uri(builder.Configuration["MlService:BaseUrl"] ?? "http://localhost:8000");
   });
   ```
3. Xem hướng dẫn chi tiết tại [README_ASPNET_INTEGRATION.md](clients/csharp/README_ASPNET_INTEGRATION.md).

---

## 6. Hướng dẫn đẩy lên GitHub Repository của bạn

Sau khi tạo một repository mới trên tài khoản GitHub của bạn (ví dụ `https://github.com/QangDuc/task-risk-prediction-service.git`), hãy chạy các lệnh sau trong thư mục này:

```bash
# 1. Thêm remote origin
git remote add origin https://github.com/QangDuc/<ten-repo-cua-ban>.git

# 2. Đặt nhánh chính là main
git branch -M main

# 3. Đẩy code lên GitHub
git push -u origin main
```
