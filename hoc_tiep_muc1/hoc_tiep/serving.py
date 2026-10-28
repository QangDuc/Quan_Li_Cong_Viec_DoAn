import pandas as pd

from .compare import levels_array
from .model_backend import HGBBackend, prepare_features


class RiskService:
    """Lớp dự đoán dùng phiên bản CURRENT của kho; tự ghi nhật ký dự đoán vào kho phản hồi."""
    def __init__(self, registry, store, backend=None):
        self.registry, self.store, self.backend = registry, store, backend or HGBBackend()
        self._v = self._b = None

    def _bundle(self):
        v = self.registry.current()
        if v != self._v:                         # tự nạp lại khi CURRENT đổi (nâng cấp hoặc quay lại)
            self._b, self._v = self.registry.load(v), v
        return self._v, self._b

    def predict(self, df, kind="static", log=True, now=None):
        v, b = self._bundle()
        p = self.backend.predict(b, prepare_features(df, b["features"]))
        lv = levels_array(p, b["thresholds"])
        if log:
            self.store.log_predictions(df, p, lv, v, kind, predicted_at=now)
        out = pd.DataFrame({"task_id": df["task_id"].values, "lecturer_id": df["lecturer_id"].values, "risk_probability": p, "level": lv, "model_version": v})
        return out

    def record_outcomes(self, df, recorded_at=None):
        return self.store.record_outcomes(df, recorded_at)
