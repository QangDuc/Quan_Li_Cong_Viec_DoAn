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


def get_ai_settings():
    env_local = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.local")
    data = {
        "provider": os.environ.get("AI_PROVIDER", "auto"),
        "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
        "gemini_model": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        "groq_api_key": os.environ.get("GROQ_API_KEY", ""),
        "groq_model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
    }
    if os.path.exists(env_local):
        try:
            with open(env_local, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip().lower(), v.strip()
                        if k == "ai_provider":
                            data["provider"] = v
                        elif k == "gemini_api_key":
                            data["gemini_api_key"] = v
                        elif k == "gemini_model":
                            data["gemini_model"] = v
                        elif k == "groq_api_key":
                            data["groq_api_key"] = v
                        elif k == "groq_model":
                            data["groq_model"] = v
        except Exception:
            pass
    return data


def save_ai_settings(provider, gemini_api_key=None, gemini_model=None, groq_api_key=None, groq_model=None):
    cur = get_ai_settings()
    if provider:
        cur["provider"] = provider
    if gemini_api_key is not None:
        cur["gemini_api_key"] = gemini_api_key
    if gemini_model:
        cur["gemini_model"] = gemini_model
    if groq_api_key is not None:
        cur["groq_api_key"] = groq_api_key
    if groq_model:
        cur["groq_model"] = groq_model

    env_local = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.local")
    try:
        with open(env_local, "w", encoding="utf-8") as f:
            f.write(f"AI_PROVIDER={cur['provider']}\n")
            f.write(f"GEMINI_API_KEY={cur['gemini_api_key']}\n")
            f.write(f"GEMINI_MODEL={cur['gemini_model']}\n")
            f.write(f"GROQ_API_KEY={cur['groq_api_key']}\n")
            f.write(f"GROQ_MODEL={cur['groq_model']}\n")
    except Exception:
        pass

    os.environ["AI_PROVIDER"] = cur["provider"]
    os.environ["GEMINI_API_KEY"] = cur["gemini_api_key"]
    os.environ["GEMINI_MODEL"] = cur["gemini_model"]
    os.environ["GROQ_API_KEY"] = cur["groq_api_key"]
    os.environ["GROQ_MODEL"] = cur["groq_model"]
    return cur
