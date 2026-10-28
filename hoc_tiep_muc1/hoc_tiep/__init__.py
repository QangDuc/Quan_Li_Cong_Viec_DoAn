"""hoc_tiep: học tiếp mức 1 = huấn luyện lại định kỳ CÓ KIỂM SOÁT từ dữ liệu vận hành.
Thành phần: FeedbackStore (kho phản hồi), ModelRegistry (phiên bản, quay lại), retrain_job.run (huấn luyện lại + so sánh + rào chắn),
RiskService (dự đoán có ghi nhật ký)."""
from .config import Config
from .feedback_store import FeedbackStore
from .model_registry import ModelRegistry
from .model_backend import HGBBackend, prepare_features
from .compare import paired_bootstrap, level_stats, pick_thresholds
from . import retrain_job
from .serving import RiskService
