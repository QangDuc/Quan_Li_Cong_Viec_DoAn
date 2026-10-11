import os
from pathlib import Path

# Thư mục gốc của service
BASE_DIR = Path(__file__).resolve().parent.parent

# Đường dẫn model và dữ liệu
MODEL_PATH = os.getenv("MODEL_PATH", str(BASE_DIR / "model" / "risk_model.joblib"))
METRICS_PATH = os.getenv("METRICS_PATH", str(BASE_DIR / "model" / "metrics.json"))
MATRIX_PATH = os.getenv("MATRIX_PATH", str(BASE_DIR / "data" / "task_personnel_matrix.csv"))

# Cấu hình thiết bị và môi trường
DEVICE = os.getenv("DEVICE", "auto")
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

# Ngưỡng mặc định (nếu không có trong file model)
DEFAULT_THRESHOLDS = [0.22, 0.44]
LEVEL_NAMES = ["Thấp", "Trung bình", "Cao"]
