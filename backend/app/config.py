"""Cấu hình đọc từ biến môi trường (xem .env.example ở thư mục gốc)."""
import os
from urllib.parse import quote_plus


def _env(key, default=None):
    v = os.environ.get(key)
    return default if v is None or v == "" else v


# Mặc định: SQL Server LocalDB trên máy phát triển Windows. Docker Compose ghi đè bằng DATABASE_URL.
_DEFAULT_ODBC = "Driver={ODBC Driver 17 for SQL Server};Server=(localdb)\\MSSQLLocalDB;Database=qlcv;Trusted_Connection=yes;"
DATABASE_URL = _env("DATABASE_URL", "mssql+pyodbc:///?odbc_connect=" + quote_plus(_DEFAULT_ODBC))

JWT_SECRET = _env("JWT_SECRET", "doi-khoa-bi-mat-nay-khi-trien-khai")
JWT_EXPIRE_MINUTES = int(_env("JWT_EXPIRE_MINUTES", "480"))

ML_SERVICE_URL = _env("ML_SERVICE_URL", "http://localhost:8001")
ML_TIMEOUT_SECONDS = float(_env("ML_TIMEOUT_SECONDS", "4"))          # quá thời gian -> lưu "chưa có dự đoán", tính lại nền
ML_RETRY_INTERVAL_SECONDS = int(_env("ML_RETRY_INTERVAL_SECONDS", "60"))
ML_BACKGROUND_TIMEOUT_SECONDS = float(_env("ML_BACKGROUND_TIMEOUT_SECONDS", "120"))

REMINDER_DAYS = [int(x) for x in _env("REMINDER_DAYS", "3,1").split(",")]   # nhắc trước hạn (ngày)
SCHEDULER_INTERVAL_SECONDS = int(_env("SCHEDULER_INTERVAL_SECONDS", "300"))
SCHEDULER_ENABLED = _env("SCHEDULER_ENABLED", "1") == "1"

ACADEMIC_YEAR_START = _env("ACADEMIC_YEAR_START", "08-15")   # tháng-ngày bắt đầu tuần 1 năm học
CORS_ORIGINS = [x.strip() for x in _env("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080").split(",")]
LOG_LEVEL = _env("LOG_LEVEL", "INFO")
