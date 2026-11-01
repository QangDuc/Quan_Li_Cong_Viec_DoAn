"""Backend TabPFN cho học tiếp (cùng giao diện với HGBBackend: fit / predict).
"Huấn luyện" TabPFN = chọn các túi dòng ngữ cảnh + bộ mã hóa (không cập nhật trọng số) nên rất rẻ; chi phí nằm ở suy luận
(chọn ngưỡng trên cửa sổ validation và so sánh trên holdout) và cần GPU.
Gói mô hình là dict THUẦN (numpy/dict), không chứa đối tượng TabPFN, nên dịch vụ ml_service nạp được mà không cần import hoc_tiep.
Cần train_model.py cạnh gói (có sẵn) để dùng đúng engineer/mã hóa/chọn ngữ cảnh của lần huấn luyện gốc."""
import numpy as np
import pandas as pd

try:
    import train_model as _T
except Exception:      # pragma: no cover
    _T = None


class TabPFNBackend:
    name = "tabpfn"

    def __init__(self, n_bags=4, version="v2", params=None, pred_batch=4000, device="auto", max_context=None):
        if _T is None:
            raise RuntimeError("Thiếu train_model.py (đặt cạnh gói hoc_tiep) để dùng backend TabPFN")
        self.n_bags, self.version, self.pred_batch = n_bags, version, pred_batch
        self.params = params or dict(_T.PARAM_GRID[0])
        self.device, self.max_context = device, max_context
        self._clf = {}                                   # bộ phân loại TabPFN dựng lười, KHÔNG lưu vào gói

    def _configure(self):
        _T.TABPFN_VERSION, _T.N_BAGS, _T.DEVICE, _T.MAX_CONTEXT, _T.CONTEXT_MODE = self.version, self.n_bags, self.device, self.max_context, "random"

    def fit(self, X, y, seed=0):
        """X phải sắp theo thời gian (cũ -> mới), như train_model.fit_model."""
        self._configure()
        m = _T.fit_model(X.reset_index(drop=True), y, params=self.params, seed=seed)
        m["baseline"] = _T.baseline_values(X)
        return {k: m[k] for k in ("model_name", "tabpfn_version", "features", "hyperparams", "encoder", "contexts", "cat_idx", "seed", "baseline")}

    def _clfs(self, m):
        key = id(m)
        if key not in self._clf:
            self._configure()
            out = []
            for k, (Xc, yc) in enumerate(m["contexts"]):
                c = _T.make_tabpfn(m["hyperparams"], m["cat_idx"], seed=m.get("seed", 0) + k)
                c.fit(Xc, yc)
                out.append(c)
            self._clf = {key: (m, out)}                  # giữ tham chiếu m (tránh id bị tái dùng); chỉ giữ mô hình vừa dùng gần nhất (tiết kiệm GPU)
        return self._clf[key][1]

    def predict(self, bundle, X):
        m = bundle["pipeline"]
        Xe = _T.apply_encoder(m["encoder"], X.reindex(columns=m["features"]))
        clfs = self._clfs(m)
        per_bag = []
        for c in clfs:
            ps = [c.predict_proba(Xe.iloc[i:i + self.pred_batch].values)[:, 1] for i in range(0, len(Xe), self.pred_batch)]
            per_bag.append(np.concatenate(ps) if ps else np.zeros(0))
        return np.clip(np.vstack(per_bag).mean(axis=0), 1e-4, 1 - 1e-4)


def import_service_bundle(registry, path, now=None, reason="nhập mô hình TabPFN đã huấn luyện"):
    """Đăng ký mô hình đang chạy (model/risk_model.joblib do train_model.py tạo) làm phiên bản đầu của kho."""
    import joblib
    s = joblib.load(path)
    pipe = {k: s[k] for k in ("model_name", "tabpfn_version", "features", "hyperparams", "encoder", "contexts", "cat_idx", "seed", "baseline")}
    meta = s.get("meta") or {}
    b = dict(backend="tabpfn", pipeline=pipe, features=list(s["features"]), thresholds=list(s["thresholds"]), thresholds_met_on_val=True,
             data_end=meta.get("data_end"), n_train=int(meta.get("n_rows", 0)), levels=s.get("levels"), meta=meta)
    v = registry.register(b, dict(kind="import", source=str(path), n_train=b["n_train"]), now=now)
    registry.promote(v, reason, now=now)
    return v


def get_backend(name, **kw):
    if name == "tabpfn":
        return TabPFNBackend(**kw)
    from .model_backend import HGBBackend
    return HGBBackend()
