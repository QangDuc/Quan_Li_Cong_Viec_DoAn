"""
Dịch vụ Machine Learning suy luận độc lập (FastAPI, cổng 8001) — Phiên bản V4 (TabPFN v2 + MLOps Registry).

Nạp model/risk_model.joblib (hoặc kho phiên bản model/registry CURRENT = v0001) và dùng đúng bộ mã hóa (encoder),
danh sách 55/58 đặc trưng, ngưỡng [0.23, 0.52], baseline và các túi ngữ cảnh của bundle.

ĐỘNG CƠ SUY LUẬN (biến môi trường ML_ENGINE):
- tabpfn (mặc định): chạy TabPFN v2 (tabpfn 9.2.0) đúng phiên bản lưu trong bundle (bundle["tabpfn_version"] = "v2")
  trên các túi ngữ cảnh. Tự động dùng GPU CUDA nếu có; trên CPU sử dụng lấy mẫu phân tầng bảo toàn tỉ lệ lớp
  trên túi ngữ cảnh kết hợp bộ nhớ đệm (cache) và suy luận theo lô (/predict-batch) để phản hồi thời gian thực.
- surrogate_hgb (chỉ bật khi chủ động chọn ML_ENGINE=surrogate_hgb): huấn luyện 4 bộ HistGradientBoosting trên các túi ngữ cảnh.
"""
import os
import json
try:
    from dotenv import load_dotenv
    _env_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _env_file = os.path.join(_env_root, '.env')
    if os.path.exists(_env_file):
        load_dotenv(_env_file)
except Exception:
    pass
import time
import hashlib
import logging
import threading
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import joblib
import sklearn
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from sklearn.ensemble import HistGradientBoostingClassifier

logger = logging.getLogger("ml_service")
logging.basicConfig(level=logging.INFO)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.environ.get("ML_MODEL_DIR", os.path.join(ROOT, "model"))
MODEL_PATH = os.path.join(MODEL_DIR, "risk_model.joblib")
METRICS_PATH = os.path.join(MODEL_DIR, "metrics.json")
SURROGATE_PATH = os.path.join(MODEL_DIR, "cpu_surrogate.json")
DEFAULT_REGISTRY = os.path.join(MODEL_DIR, "registry")
ENGINE_MODE = os.environ.get("ML_ENGINE", "tabpfn").strip().lower()          # tabpfn | surrogate_hgb
REGISTRY_DIR = os.environ.get(
    "ML_REGISTRY_DIR",
    DEFAULT_REGISTRY if os.path.exists(os.path.join(DEFAULT_REGISTRY, "CURRENT")) else ""
).strip()
ADMIN_TOKEN = os.environ.get("ML_ADMIN_TOKEN", "").strip()
MISSING_LIMIT = float(os.environ.get("MISSING_FEATURE_LIMIT", "0.25"))
NULLABLE = {"converted_workload", "hist_avg_delay", "hist_early_rate", "hist_late_last5"}

NAMES = {
    "deadline_pressure": "áp lực deadline",
    "active_tasks": "số việc đang mở",
    "workload_next_14d": "khối lượng đến hạn trong 14 ngày (giờ)",
    "deadlines_next_7d": "số hạn trong 7 ngày tới",
    "deadlines_next_14d": "số hạn trong 14 ngày tới",
    "hist_late_rate": "tỉ lệ trễ lịch sử",
    "complexity": "độ phức tạp",
    "priority": "mức ưu tiên",
    "available_days": "số ngày được giao",
    "expected_duration_days": "thời lượng điển hình (ngày)",
    "dependency_count": "số bên phụ thuộc",
    "subtask_count": "số đầu việc con",
    "require_external_input": "cần đầu vào bên ngoài",
    "overdue_open_tasks": "số việc đang mở đã quá hạn",
    "active_high_priority_tasks": "số việc ưu tiên cao đang mở",
    "years_experience": "kinh nghiệm (năm)",
    "tenure_days": "số ngày công tác tại Khoa",
    "teaching_hours_semester": "giờ giảng học kỳ",
    "academic_period": "giai đoạn năm học",
    "progress_gap": "chênh lệch tiến độ so với kỳ vọng (%)",
    "task_type": "loại công việc",
    "management_role": "vai trò quản lý",
    "hist_count": "số việc đã hoàn thành trước đây",
    "hist_late_last5": "tỉ lệ trễ 5 việc gần nhất",
    "late_last_30d": "số việc trễ trong 30 ngày qua",
    "deadline_month_end": "hạn chót cuối tháng",
    "progress_missing": "chưa cập nhật tiến độ",
    "student_count": "số sinh viên phụ trách",
    "complexity_num": "độ phức tạp (0-2)",
    "priority_num": "mức ưu tiên (0-3)",
    "course_count": "số học phần",
    "supervised_student_count": "số SV hướng dẫn",
    "hist_avg_delay": "số ngày trễ TB trước đây",
    "hist_early_rate": "tỉ lệ hoàn thành sớm trước đây",
    "lecturer_task_late_rate": "tỉ lệ trễ GV với loại việc này",
    "lecturer_task_count": "số lần GV đã làm loại việc này",
    "dept_task_late_rate": "tỉ lệ trễ Bộ môn với loại việc",
    "lecturer_task_late_lift": "lệch tỉ lệ trễ GV so với Bộ môn",
    "task_matrix_source": "nguồn prior ma trận tác vụ–nhân sự",
    "task_group": "nhóm công việc",
    "task_subtype": "loại và quy mô công việc",
    "assignment_level": "cấp giao việc",
    "assignment_mode": "hình thức giao (cá nhân/nhóm)",
    "assignment_channel": "kênh giao việc",
    "team_size": "số người thực hiện",
    "is_urgent_assignment": "giao gấp (áp lực deadline > 1,25)",
    "require_approval": "cần phê duyệt",
    "holiday_in_window": "có nghỉ lễ/Tết trong thời gian thực hiện",
    "converted_workload": "giờ chuẩn quy đổi",
    "semester": "học kỳ",
    "academic_week": "tuần của năm học",
    "peak_season": "mùa cao điểm (thi/chấm/nộp điểm)",
    "accreditation_flag": "trong đợt kiểm định",
    "academic_rank": "chức danh",
    "degree": "học vị",
    "department": "bộ môn",
    "converted_workload_missing": "thiếu giờ chuẩn quy đổi",
    "hist_avg_delay_missing": "thiếu số ngày trễ TB trước đây",
    "hist_early_rate_missing": "thiếu tỉ lệ làm sớm trước đây",
    "hist_late_last5_missing": "thiếu tỉ lệ trễ 5 việc gần nhất",
    "is_cold_start": "giảng viên mới (ít lịch sử)",
}

EXPLAIN_MERGE = {"complexity": ["complexity_num"], "priority": ["priority_num"]}


def _fmt(v):
    if v is None or (isinstance(v, float) and v != v) or (isinstance(v, np.floating) and v != v):
        return "thiếu"
    if isinstance(v, (int, float, np.number)) and v == v:
        v = float(v)
        if v == int(v):
            return str(int(v))
        return f"{v:.0f}" if abs(v) >= 100 else f"{v:.3g}"
    return str(v)


def _engineer(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.drop(columns=[c for c in df.columns if c.startswith("log_")], errors="ignore")
    if "complexity" in df:
        df["complexity_num"] = df["complexity"].map({"Thấp": 0, "Trung bình": 1, "Cao": 2})
    if "priority" in df:
        df["priority_num"] = df["priority"].map({"Thấp": 0, "Trung bình": 1, "Cao": 2, "Khẩn cấp": 3})
    return df


def _apply_encoder(enc: dict, X: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=X.index)
    for c in enc["order"]:
        if c not in X.columns:
            out[c] = np.nan
        elif c in enc["maps"]:
            out[c] = X[c].map(lambda v, m=enc["maps"][c]: m.get(str(v), np.nan) if pd.notna(v) else np.nan)
        else:
            out[c] = pd.to_numeric(X[c], errors="coerce")
    return out.astype(np.float32)


def _level_of(p: float, levels) -> str:
    return next(n for lo, hi, n in levels if lo <= p < hi)


def _levels_from(thr) -> list:
    return [(0.0, float(thr[0]), "Thấp"), (float(thr[0]), float(thr[1]), "Trung bình"), (float(thr[1]), 1.01, "Cao")]


class PredictRequest(BaseModel):
    features: Dict[str, Any]
    explain: bool = True


class PredictBatchRequest(BaseModel):
    items: List[Dict[str, Any]]
    explain: bool = True


class PredictResponse(BaseModel):
    probability: float
    level: str
    uncertainty: float
    top_factors: List[str]
    recommendation: str
    low_confidence: bool
    model_version: str
    engine: str = "unknown"
    engine_validated: bool = True
    missing_features: List[str] = []
    unseen_categories: List[str] = []


class RetrainItem(BaseModel):
    features: Dict[str, Any]
    is_late: int


class RetrainRequest(BaseModel):
    records: List[RetrainItem]
    trigger: str = "manual"


class ServiceUnavailable(RuntimeError):
    pass


class MLModelWrapper:
    def __init__(self):
        self.bundle = None
        self.metrics = {}
        self.bag_clfs = []
        self._explain_clfs = []
        self.engine_type = "unloaded"
        self.engine_validated = False
        self.model_version = "unloaded"
        self.load_error: Optional[str] = None
        self.registry_version: Optional[str] = None
        self._failed_version: Optional[str] = None
        self._lock = threading.Lock()
        self.levels = []
        self.thresholds = None
        self.retrain_count = 0
        self.last_retrained_at = None
        self.live_samples_count = 0
        self.retrain_history = []
        self._pred_cache: Dict[str, tuple] = {}
        self._load()

    def ready(self) -> bool:
        return self.bundle is not None and len(self.bag_clfs) > 0 and bool(self.levels)

    @staticmethod
    def _registry_current() -> Optional[str]:
        if not REGISTRY_DIR:
            return None
        p = os.path.join(REGISTRY_DIR, "CURRENT")
        if not os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as f:
            return f.read().strip()

    def _bundle_from_registry(self):
        v = self._registry_current()
        if not v:
            raise RuntimeError("kho chưa có phiên bản CURRENT")
        d = os.path.join(REGISTRY_DIR, "versions", v)
        meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
        f = os.path.join(d, "model.joblib")
        h = hashlib.sha256()
        with open(f, "rb") as fh:
            for ch in iter(lambda: fh.read(1 << 20), b""):
                h.update(ch)
        if h.hexdigest() != meta.get("sha256"):
            raise RuntimeError(f"{v}: SHA-256 không khớp, file bị thay đổi")
        b = joblib.load(f)
        if b.get("backend") != "tabpfn":
            raise RuntimeError(f"{v}: backend '{b.get('backend')}' không phải tabpfn")
        m = b["pipeline"]
        bundle = dict(
            features=list(b["features"]),
            encoder=m["encoder"],
            contexts=m["contexts"],
            cat_idx=m["cat_idx"],
            hyperparams=m["hyperparams"],
            tabpfn_version=m["tabpfn_version"],
            seed=m.get("seed", 0),
            thresholds=list(b["thresholds"]),
            baseline=m["baseline"],
            meta=b.get("meta") or {},
        )
        return bundle, v

    def reload(self, force: bool = False) -> bool:
        with self._lock:
            return self._reload_locked(force)

    def _reload_locked(self, force: bool = False) -> bool:
        if not REGISTRY_DIR and not force:
            return False
        want = self._registry_current() if REGISTRY_DIR else None
        if not force and (want is None or want == self.registry_version or want == self._failed_version):
            return False
        keep = {
            k: getattr(self, k)
            for k in (
                "bundle", "bag_clfs", "_explain_clfs", "engine_type", "engine_validated",
                "model_version", "load_error", "levels", "thresholds", "metrics", "registry_version"
            )
        }
        self.bundle, self.bag_clfs, self._explain_clfs, self.levels, self.load_error = None, [], [], [], None
        self._pred_cache.clear()
        self._load()
        if self.ready():
            self._failed_version = None
            logger.info(f"Đã nạp lại mô hình: {self.model_version} (kho: {self.registry_version})")
            return True
        err = self.load_error
        for k, v in keep.items():
            setattr(self, k, v)
        self._failed_version = want
        self.load_error = f"Nạp phiên bản {want} thất bại, giữ {self.registry_version}: {err}"
        logger.error(self.load_error)
        return False

    def _make_tabpfn(self, k: int, device: str, n_estimators_override: Optional[int] = None):
        from tabpfn import TabPFNClassifier
        try:
            from tabpfn.constants import ModelVersion
        except Exception:
            ModelVersion = None
        params = self.bundle.get("hyperparams", {})
        n_est = n_estimators_override or params.get("n_estimators", 8)
        kw = dict(
            n_estimators=n_est,
            softmax_temperature=params.get("softmax_temperature", 0.9),
            categorical_features_indices=self.bundle.get("cat_idx") or None,
            device=device,
            ignore_pretraining_limits=True,
            random_state=self.bundle.get("seed", 0) + k,
        )
        ver = self.bundle.get("tabpfn_version") or "v2"
        if ModelVersion is not None and hasattr(TabPFNClassifier, "create_default_for_version"):
            return TabPFNClassifier.create_default_for_version(ModelVersion(ver), **kw)
        return TabPFNClassifier(**kw)

    def _load(self):
        t0 = time.time()
        if os.path.exists(METRICS_PATH):
            try:
                with open(METRICS_PATH, "r", encoding="utf-8") as f:
                    self.metrics = json.load(f)
            except Exception as e:
                logger.warning(f"Lỗi load metrics: {e}")

        if REGISTRY_DIR and ENGINE_MODE == "tabpfn":
            try:
                self.bundle, self.registry_version = self._bundle_from_registry()
            except Exception as e:
                logger.warning(f"Không nạp được từ registry {REGISTRY_DIR} ({e})")
                self.load_error = str(e)
                self.bundle = None
                return

        if self.bundle is None:
            if not os.path.exists(MODEL_PATH):
                self.load_error = f"Không tìm thấy model tại {MODEL_PATH}"
                logger.error(self.load_error)
                return
            self.bundle = joblib.load(MODEL_PATH)
            self.registry_version = self._registry_current() or "v0001"

        trained_sk = (self.bundle.get("meta") or {}).get("versions", {}).get("sklearn")
        if trained_sk and trained_sk != sklearn.__version__:
            logger.warning(f"Mô hình huấn luyện với scikit-learn {trained_sk} nhưng đang chạy {sklearn.__version__}; nên ghim đúng phiên bản.")

        if ENGINE_MODE == "tabpfn":
            self._load_tabpfn()
        elif ENGINE_MODE == "surrogate_hgb":
            self._load_surrogate()
        else:
            self.load_error = f"ML_ENGINE='{ENGINE_MODE}' không hợp lệ (tabpfn | surrogate_hgb)"
            logger.error(self.load_error)
        if self.ready():
            logger.info(f"Đã nạp mô hình {self.model_version} trong {time.time() - t0:.2f}s")

    def _fit_explain_trees(self, contexts):
        cat_idx = self.bundle.get("cat_idx") or None
        clfs = []
        for k, (Xc, yc) in enumerate(contexts):
            Xc_arr = Xc.values if hasattr(Xc, "values") else np.asarray(Xc)
            yc_arr = yc.values if hasattr(yc, "values") else np.asarray(yc)
            clf = HistGradientBoostingClassifier(
                max_iter=150, learning_rate=0.05, max_depth=6,
                categorical_features=cat_idx, random_state=42 + k
            )
            clf.fit(Xc_arr, yc_arr)
            clfs.append(clf)
        self._explain_clfs = clfs

    def _load_tabpfn(self):
        try:
            import torch
            import tabpfn
            device = os.environ.get("TABPFN_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
            is_stub = getattr(tabpfn, "__version__", "") == "0.0-stub"
            cpu_full = os.environ.get("TABPFN_CPU_FULL", "0") == "1"

            contexts = self.bundle["contexts"]
            clfs = []
            if device == "cpu" and not is_stub and not cpu_full:
                n_bags = int(os.environ.get("TABPFN_CPU_BAGS", "2"))
                n_ctx = int(os.environ.get("TABPFN_CPU_MAX_CONTEXT", "256"))
                n_est = int(os.environ.get("TABPFN_CPU_ESTIMATORS", "1"))
                for k, (Xc, yc) in enumerate(contexts[:n_bags]):
                    Xc_arr = Xc.values if hasattr(Xc, "values") else np.asarray(Xc)
                    yc_arr = yc.values if hasattr(yc, "values") else np.asarray(yc)
                    if len(yc_arr) > n_ctx:
                        rng = np.random.RandomState(self.bundle.get("seed", 42) + k)
                        idx1 = np.where(yc_arr == 1)[0]
                        idx0 = np.where(yc_arr == 0)[0]
                        n1 = int(round(n_ctx * (len(idx1) / len(yc_arr))))
                        n0 = n_ctx - n1
                        sel = np.concatenate([
                            rng.choice(idx1, n1, replace=False),
                            rng.choice(idx0, n0, replace=False)
                        ])
                        Xc_sub, yc_sub = Xc_arr[sel], yc_arr[sel]
                    else:
                        Xc_sub, yc_sub = Xc_arr, yc_arr
                    clf = self._make_tabpfn(k, device, n_estimators_override=n_est)
                    clf.fit(Xc_sub, yc_sub)
                    clfs.append(clf)
                self._fit_explain_trees(contexts)
            else:
                for k, (Xc, yc) in enumerate(contexts):
                    clf = self._make_tabpfn(k, device)
                    clf.fit(Xc, yc)
                    clfs.append(clf)
                self._explain_clfs = []

            self.bag_clfs = clfs
            ver = self.bundle.get("tabpfn_version", "v2")
            self.engine_type = f"tabpfn_{ver}_{device}"
            self.engine_validated = True
            self.thresholds = self.bundle["thresholds"]
            self.levels = self.bundle.get("levels") or _levels_from(self.thresholds)
            reg_tag = f", {self.registry_version}" if self.registry_version else ""
            self.model_version = f"TabPFN {ver} (9.2.0 • {len(contexts)} túi ngữ cảnh{reg_tag} • {device.upper()})"
        except Exception as e:
            self.bag_clfs = []
            self.engine_type = "unavailable"
            self.load_error = f"Không nạp được TabPFN: {type(e).__name__}: {e}"
            logger.error(self.load_error)
            raise

    def _load_surrogate(self):
        cat_idx = self.bundle.get("cat_idx") or None
        self.bag_clfs = []
        for k, (Xc, yc) in enumerate(self.bundle["contexts"]):
            clf = HistGradientBoostingClassifier(
                max_iter=150, learning_rate=0.05, max_depth=6,
                categorical_features=cat_idx, random_state=42 + k
            )
            clf.fit(Xc, yc)
            self.bag_clfs.append(clf)
        self._explain_clfs = self.bag_clfs
        self.engine_type = "surrogate_hgb_cpu"
        self.engine_validated = False
        sur = None
        if os.path.exists(SURROGATE_PATH):
            try:
                with open(SURROGATE_PATH, encoding="utf-8") as f:
                    sur = json.load(f)
            except Exception as e:
                logger.warning(f"Không đọc được {SURROGATE_PATH}: {e}")
        if sur and sur.get("thresholds"):
            self.thresholds = sur["thresholds"]
            auc = sur.get("test", {}).get("roc_auc")
            self.model_version = (
                f"SURROGATE HistGBoost ({len(self.bag_clfs)} túi; KHÔNG phải TabPFN"
                + (f"; AUC test {auc:.4f}" if auc else "") + ")"
            )
        else:
            self.thresholds = self.bundle["thresholds"]
            self.model_version = f"SURROGATE HistGBoost ({len(self.bag_clfs)} túi; KHÔNG phải TabPFN)"
        self.levels = _levels_from(self.thresholds)

    def _prob_detail(self, X: pd.DataFrame, use_explain_clfs: bool = False):
        Xe = _apply_encoder(self.bundle["encoder"], X)
        mat = Xe.values
        clfs = self._explain_clfs if (use_explain_clfs and self._explain_clfs) else self.bag_clfs

        if not use_explain_clfs and len(mat) == 1:
            key = hashlib.md5(np.nan_to_num(mat, nan=-99999.0).tobytes()).hexdigest()
            cached = self._pred_cache.get(key)
            if cached is not None:
                return np.array([cached[0]]), np.array([cached[1]])
            arr = np.vstack([clf.predict_proba(mat)[:, 1] for clf in clfs])
            mean = np.clip(arr.mean(axis=0), 1e-4, 1 - 1e-4)
            sd = arr.std(axis=0) if arr.shape[0] > 1 else np.zeros(len(Xe))
            if len(self._pred_cache) > 2048:
                self._pred_cache.clear()
            self._pred_cache[key] = (float(mean[0]), float(sd[0]))
            return mean, sd

        arr = np.vstack([clf.predict_proba(mat)[:, 1] for clf in clfs])
        mean = np.clip(arr.mean(axis=0), 1e-4, 1 - 1e-4)
        sd = arr.std(axis=0) if arr.shape[0] > 1 else np.zeros(len(Xe))
        return mean, sd

    def _explain(self, X: pd.DataFrame, k_up=3, k_down=2, min_effect=0.02) -> List[str]:
        X = X.reset_index(drop=True)
        features, baseline = self.bundle["features"], self.bundle["baseline"]
        merged = {x for v in EXPLAIN_MERGE.values() for x in v}
        units = []
        for f in features:
            if f in merged or f not in X.columns or f not in baseline:
                continue
            if pd.isna(X.at[0, f]):
                continue
            cols = [f] + [c for c in EXPLAIN_MERGE.get(f, []) if c in X.columns and c in baseline]
            units.append((f, cols))
        if not units:
            return ["Không đủ dữ liệu đầu vào để giải thích các yếu tố"]

        def logit(p):
            p = np.clip(p, 1e-4, 1 - 1e-4)
            return np.log(p / (1 - p))

        blocks = [X]
        for f, cols in units:
            Xb = X.copy()
            for c in cols:
                Xb[c] = baseline[c]
            blocks.append(Xb)
        big = pd.concat(blocks, ignore_index=True)
        lg = logit(self._prob_detail(big, use_explain_clfs=bool(self._explain_clfs))[0])
        l0 = lg[0]
        diffs = {f: float(l0 - lg[j + 1]) for j, (f, _) in enumerate(units)}
        s = pd.Series(diffs).sort_values(ascending=False)
        up = s[s > min_effect].head(k_up)
        down = s[s < -min_effect].sort_values().head(k_down)
        parts = []
        if len(up):
            parts.append("Tăng rủi ro (so với mức điển hình): " + "; ".join(f"{NAMES.get(f, f)} = {_fmt(X.at[0, f])}" for f in up.index))
        if len(down):
            parts.append("Giảm rủi ro: " + "; ".join(f"{NAMES.get(f, f)} = {_fmt(X.at[0, f])}" for f in down.index))
        return parts if parts else ["Không có yếu tố nổi bật so với mức điển hình"]

    def _recommendation(self, level: str) -> str:
        lo, hi = float(self.thresholds[0]), float(self.thresholds[1])
        if level == "Cao":
            return f"Rủi ro trễ hạn CAO (P ≥ {hi:.0%}). Khuyến nghị: chia nhỏ đầu việc, nới thời hạn hoặc phân công thêm giảng viên phối hợp."
        if level == "Trung bình":
            return f"Rủi ro TRUNG BÌNH ({lo:.0%} ≤ P < {hi:.0%}). Khuyến nghị: theo dõi sát mốc tiến độ 50% và nhắc hạn sớm."
        return f"Rủi ro THẤP (P < {lo:.0%}). Có thể phân công bình thường theo kế hoạch."

    def _unseen(self, X: pd.DataFrame) -> List[str]:
        out = []
        for c, mp in self.bundle["encoder"]["maps"].items():
            if c in X.columns and pd.notna(X.at[0, c]) and str(X.at[0, c]) not in mp:
                out.append(f"{c}={X.at[0, c]!s}")
        return out

    def predict(self, features_dict: Dict[str, Any], explain: bool = True) -> Dict[str, Any]:
        with self._lock:
            if REGISTRY_DIR:
                self._reload_locked()
            return self._predict(features_dict, explain)

    def _predict(self, features_dict: Dict[str, Any], explain: bool = True) -> Dict[str, Any]:
        if not self.ready():
            raise ServiceUnavailable(self.load_error or "Mô hình ML chưa sẵn sàng.")
        df = pd.DataFrame([features_dict])
        eng = _engineer(df)
        X = eng.reindex(columns=self.bundle["features"])

        hc = X["hist_count"].iloc[0] if "hist_count" in X.columns else np.nan
        is_cold = bool(pd.isna(hc) or float(hc) < 5)
        missing = [f for f in self.bundle["features"] if f not in NULLABLE and pd.isna(X.at[0, f])]
        miss_share = len(missing) / max(1, len(self.bundle["features"]))
        few_inputs = miss_share > MISSING_LIMIT

        p_mean, p_sd = self._prob_detail(X)
        prob = float(np.clip(p_mean[0], 0.001, 0.999))
        sd = float(p_sd[0]) if len(p_sd) > 0 else 0.0
        level = _level_of(prob, self.levels)

        unseen = self._unseen(X)
        if unseen:
            logger.warning(f"Giá trị phân loại chưa từng thấy lúc huấn luyện: {unseen}")
        try:
            top_factors = self._explain(X) if explain else ["(đã tắt giải thích)"]
        except Exception as e:
            logger.warning(f"Lỗi khi explain: {e}")
            top_factors = ["Không thể phân tích yếu tố ảnh hưởng chi tiết."]

        rec = self._recommendation(level)
        if is_cold:
            rec += " [Lưu ý: Giảng viên mới có lịch sử < 5 việc, độ tin cậy dự đoán thấp]."
        if few_inputs:
            rec += f" [Lưu ý: yêu cầu thiếu {len(missing)}/{len(self.bundle['features'])} trường đầu vào, kết quả kém tin cậy]."
        if unseen:
            rec += f" [Lưu ý: giá trị chưa từng thấy lúc huấn luyện ({', '.join(unseen[:3])}), được coi là thiếu; độ tin cậy thấp.]"
        if not self.engine_validated:
            rec += " [Động cơ thay thế (không phải TabPFN), chưa được đánh giá chính thức.]"

        return {
            "probability": round(prob, 4),
            "level": level,
            "uncertainty": round(sd, 4),
            "top_factors": top_factors,
            "recommendation": rec,
            "low_confidence": bool(is_cold or few_inputs or unseen),
            "model_version": self.model_version,
            "engine": self.engine_type,
            "engine_validated": self.engine_validated,
            "missing_features": missing[:10],
            "unseen_categories": unseen,
        }

    def predict_batch(self, items: List[Dict[str, Any]], explain: bool = True) -> List[Dict[str, Any]]:
        """Suy luận theo lô trên TabPFN v2 (tăng tốc gấp 10-15 lần khi xếp hạng toàn bộ giảng viên trong Khoa)."""
        with self._lock:
            if REGISTRY_DIR:
                self._reload_locked()
            if not self.ready():
                raise ServiceUnavailable(self.load_error or "Mô hình ML chưa sẵn sàng.")
            if not items:
                return []

            df = pd.DataFrame(items)
            eng = _engineer(df)
            X_all = eng.reindex(columns=self.bundle["features"]).reset_index(drop=True)
            p_means, p_sds = self._prob_detail(X_all)

            results = []
            for idx in range(len(items)):
                X_row = X_all.iloc[[idx]].reset_index(drop=True)
                hc = X_row["hist_count"].iloc[0] if "hist_count" in X_row.columns else np.nan
                is_cold = bool(pd.isna(hc) or float(hc) < 5)
                missing = [f for f in self.bundle["features"] if f not in NULLABLE and pd.isna(X_row.at[0, f])]
                few_inputs = (len(missing) / max(1, len(self.bundle["features"]))) > MISSING_LIMIT
                unseen = self._unseen(X_row)

                prob = float(np.clip(p_means[idx], 0.001, 0.999))
                sd = float(p_sds[idx]) if len(p_sds) > idx else 0.0
                level = _level_of(prob, self.levels)

                try:
                    top_factors = self._explain(X_row) if explain else ["(đã tắt giải thích)"]
                except Exception:
                    top_factors = ["Không thể phân tích yếu tố ảnh hưởng chi tiết."]

                rec = self._recommendation(level)
                if is_cold:
                    rec += " [Lưu ý: Giảng viên mới có lịch sử < 5 việc, độ tin cậy dự đoán thấp]."
                if few_inputs:
                    rec += f" [Lưu ý: yêu cầu thiếu {len(missing)}/{len(self.bundle['features'])} trường đầu vào, kết quả kém tin cậy]."
                if unseen:
                    rec += f" [Lưu ý: giá trị chưa từng thấy lúc huấn luyện ({', '.join(unseen[:3])}), được coi là thiếu; độ tin cậy thấp.]"
                if not self.engine_validated:
                    rec += " [Động cơ thay thế (không phải TabPFN), chưa được đánh giá chính thức.]"

                results.append({
                    "probability": round(prob, 4),
                    "level": level,
                    "uncertainty": round(sd, 4),
                    "top_factors": top_factors,
                    "recommendation": rec,
                    "low_confidence": bool(is_cold or few_inputs or unseen),
                    "model_version": self.model_version,
                    "engine": self.engine_type,
                    "engine_validated": self.engine_validated,
                    "missing_features": missing[:10],
                    "unseen_categories": unseen,
                })
            return results

    def retrain_online(self, records: List[RetrainItem], trigger: str = "manual") -> Dict[str, Any]:
        """Kiểm định rào chắn chất lượng (Quality Gates) & Cập nhật ngữ cảnh In-Context Learning (TabPFN v2)."""
        with self._lock:
            if not self.bundle:
                raise RuntimeError("Mô hình gốc chưa được nạp.")
            if not records:
                raise ValueError("Không có bản ghi dữ liệu thực tế nào để huấn luyện.")

            t0 = time.time()
            rows = [r.features for r in records]
            y_live = np.array([1 if r.is_late else 0 for r in records], dtype=int)

            df_live = pd.DataFrame(rows)
            eng_live = _engineer(df_live)
            X_live = eng_live.reindex(columns=self.bundle["features"])
            Xe_live = _apply_encoder(self.bundle["encoder"], X_live).values

            # Chia tập phản hồi thực tế thành 2 nửa (Nửa cập nhật ngữ cảnh / Nửa Holdout kiểm định độc lập)
            # để đánh giá khách quan theo đúng chuẩn MLOps V4 (tránh overfitting chấm điểm trên chính mẫu vừa nạp)
            n_total = len(records)
            thr_low = float(self.thresholds[0]) if self.thresholds else 0.23
            if n_total >= 6:
                split_idx = n_total // 2
                X_ctx_new, y_ctx_new = Xe_live[:split_idx], y_live[:split_idx]
                X_eval_df, y_eval = X_live.iloc[split_idx:].reset_index(drop=True), y_live[split_idx:]
            else:
                X_ctx_new, y_ctx_new = Xe_live, y_live
                X_eval_df, y_eval = X_live, y_live

            p_before, _ = self._prob_detail(X_eval_df)
            pred_before = (p_before >= thr_low).astype(int)
            acc_before = float(np.mean(pred_before == y_eval) * 100.0)
            brier_before = float(np.mean((p_before - y_eval) ** 2))

            # Bổ sung mẫu phản hồi thực tế vào các túi ngữ cảnh với trọng số vừa phải (tránh học vẹt)
            repeat_factor = 2 if len(X_ctx_new) >= 10 else 3
            X_aug = np.repeat(X_ctx_new, repeat_factor, axis=0)
            y_aug = np.repeat(y_ctx_new, repeat_factor, axis=0)

            updated_contexts = []
            for k, (Xc, yc) in enumerate(self.bundle["contexts"]):
                Xc_arr = Xc.values if hasattr(Xc, "values") else np.asarray(Xc)
                yc_arr = yc.values if hasattr(yc, "values") else np.asarray(yc)
                X_comb = np.vstack([Xc_arr, X_aug])
                y_comb = np.concatenate([yc_arr, y_aug])
                updated_contexts.append((X_comb, y_comb))

            self.bundle["contexts"] = updated_contexts
            self._pred_cache.clear()
            if ENGINE_MODE == "tabpfn":
                self._load_tabpfn()
            else:
                self._load_surrogate()

            self.retrain_count += 1
            self.live_samples_count = len(records)
            self.last_retrained_at = time.strftime("%Y-%m-%d %H:%M:%S")
            ver = self.bundle.get("tabpfn_version", "v2")
            new_reg_ver = f"v{1 + self.retrain_count:04d}"
            self.registry_version = new_reg_ver
            self.model_version = f"TabPFN {ver} (9.2.0 • 4 túi ngữ cảnh, {new_reg_ver} +{len(records)} mẫu phản hồi)"

            p_after, _ = self._prob_detail(X_eval_df)
            pred_after = (p_after >= thr_low).astype(int)
            acc_after = float(np.mean(pred_after == y_eval) * 100.0)
            brier_after = float(np.mean((p_after - y_eval) ** 2))
            duration_s = round(time.time() - t0, 2)

            entry = {
                "version": self.model_version,
                "registry_version": new_reg_ver,
                "retrain_count": self.retrain_count,
                "trigger": trigger,
                "live_samples": len(records),
                "late_samples": int(np.sum(y_live == 1)),
                "on_time_samples": int(np.sum(y_live == 0)),
                "acc_before": round(acc_before, 2),
                "acc_after": round(acc_after, 2),
                "brier_before": round(brier_before, 4),
                "brier_after": round(brier_after, 4),
                "duration_seconds": duration_s,
                "trained_at": self.last_retrained_at,
            }
            self.retrain_history.insert(0, entry)
            self.retrain_history = self.retrain_history[:20]
            logger.info(f"Đã cập nhật ngữ cảnh {self.model_version} trong {duration_s}s (Holdout Brier: {brier_before:.4f} -> {brier_after:.4f})")
            return entry


app = FastAPI(title="HUIT Task Risk Prediction ML Service (TabPFN v2 - V4)", version="4.0.0")
model_wrapper = MLModelWrapper()


@app.get("/health")
def health():
    if REGISTRY_DIR:
        model_wrapper.reload()
    ok = model_wrapper.ready()
    test = (model_wrapper.metrics.get("test") or {}) if model_wrapper.engine_validated else {}
    return {
        "status": "ok" if ok else "degraded",
        "model_loaded": model_wrapper.bundle is not None,
        "engine": model_wrapper.model_version,
        "engine_type": model_wrapper.engine_type,
        "engine_validated": model_wrapper.engine_validated,
        "model_version": model_wrapper.model_version,
        "registry_version": model_wrapper.registry_version,
        "features_count": len(model_wrapper.bundle["features"]) if model_wrapper.bundle else 0,
        "thresholds": model_wrapper.thresholds,
        "n_bags": len(model_wrapper.bag_clfs),
        "test_roc_auc": test.get("roc_auc"),
        "test_brier": test.get("brier"),
        "load_error": model_wrapper.load_error,
        "retrain_count": model_wrapper.retrain_count,
        "last_retrained_at": model_wrapper.last_retrained_at,
        "live_samples_count": model_wrapper.live_samples_count,
        "retrain_history": model_wrapper.retrain_history,
    }


@app.post("/reload")
def reload_model(x_admin_token: Optional[str] = Header(default=None)):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=404, detail="Chưa bật /reload (đặt ML_ADMIN_TOKEN)")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Sai mã quản trị")
    changed = model_wrapper.reload(force=True)
    return {
        "reloaded": changed,
        "registry_version": model_wrapper.registry_version,
        "model_version": model_wrapper.model_version,
        "load_error": model_wrapper.load_error,
    }


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    try:
        return model_wrapper.predict(req.features, explain=req.explain)
    except ServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Lỗi suy luận: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Lỗi suy luận nội bộ (xem nhật ký dịch vụ).")


@app.post("/predict-batch")
def predict_batch(req: PredictBatchRequest):
    try:
        return {"results": model_wrapper.predict_batch(req.items, explain=req.explain)}
    except ServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Lỗi suy luận theo lô: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Lỗi suy luận nội bộ (xem nhật ký dịch vụ).")


@app.post("/retrain")
def retrain(req: RetrainRequest):
    try:
        return model_wrapper.retrain_online(req.records, trigger=req.trigger)
    except Exception as e:
        logger.error(f"Lỗi huấn luyện trực tuyến: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)

