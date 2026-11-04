"""Cấu hình đọc từ biến môi trường (xem .env.example ở thư mục gốc)."""
import os
from urllib.parse import quote_plus


def _env(key, default=None):
    v = os.environ.get(key)
    return default if v is None or v == "" else v


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SQLITE_FILE = os.path.join(BASE_DIR, "qlcv.db")
_DEFAULT_SQLITE = f"sqlite:///{_SQLITE_FILE.replace(os.sep, '/')}"
_DEFAULT_ODBC = "Driver={ODBC Driver 17 for SQL Server};Server=(localdb)\\MSSQLLocalDB;Database=qlcv;Trusted_Connection=yes;"

# Ưu tiên biến môi trường; nếu file qlcv.db tồn tại thì mặc định dùng SQLite để chạy tức thì
_default_db = _DEFAULT_SQLITE if os.path.exists(_SQLITE_FILE) else ("mssql+pyodbc:///?odbc_connect=" + quote_plus(_DEFAULT_ODBC))
DATABASE_URL = _env("DATABASE_URL", _default_db)

JWT_SECRET = _env("JWT_SECRET", "doi-khoa-bi-mat-nay-khi-trien-khai")
JWT_EXPIRE_MINUTES = int(_env("JWT_EXPIRE_MINUTES", "480"))

ML_SERVICE_URL = _env("ML_SERVICE_URL", "http://127.0.0.1:8001")
ML_TIMEOUT_SECONDS = float(_env("ML_TIMEOUT_SECONDS", "4"))          # quá thời gian -> lưu "chưa có dự đoán", tính lại nền
ML_RETRY_INTERVAL_SECONDS = int(_env("ML_RETRY_INTERVAL_SECONDS", "60"))
ML_BACKGROUND_TIMEOUT_SECONDS = float(_env("ML_BACKGROUND_TIMEOUT_SECONDS", "120"))

REMINDER_DAYS = [int(x) for x in _env("REMINDER_DAYS", "3,1").split(",")]   # nhắc trước hạn (ngày)
SCHEDULER_INTERVAL_SECONDS = int(_env("SCHEDULER_INTERVAL_SECONDS", "300"))
SCHEDULER_ENABLED = _env("SCHEDULER_ENABLED", "1") == "1"

ACADEMIC_YEAR_START = _env("ACADEMIC_YEAR_START", "08-15")   # tháng-ngày bắt đầu tuần 1 năm học
CORS_ORIGINS = [x.strip() for x in _env("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080").split(",")]
LOG_LEVEL = _env("LOG_LEVEL", "INFO")
