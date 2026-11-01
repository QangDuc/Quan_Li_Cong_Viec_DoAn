"""
Dịch vụ Machine Learning suy luận độc lập (FastAPI, cổng 8001).

Nạp model/risk_model.joblib (không sửa file model) và dùng đúng bộ mã hóa (encoder), danh sách đặc trưng, ngưỡng, baseline và các túi ngữ cảnh của bundle.

ĐỘNG CƠ SUY LUẬN (biến môi trường ML_ENGINE):
- tabpfn (mặc định): chạy TabPFN đúng phiên bản lưu trong bundle (bundle["tabpfn_version"]) trên các túi ngữ cảnh. Dùng GPU nếu có, ngược lại CPU
  (CPU với 4 túi x 10.000 dòng có thể chậm; thời gian chưa được đo). Nếu không nạp được TabPFN, dịch vụ báo "degraded" và /predict trả 503,
  KHÔNG âm thầm chuyển sang mô hình khác.
- surrogate_hgb (chỉ bật khi chủ động chọn, dùng cho demo trên máy không có TabPFN): huấn luyện 4 bộ HistGradientBoosting trên các túi ngữ cảnh khi
  khởi động. Đây KHÔNG phải mô hình đã được đánh giá chính thức: AUC trên tập test v2 là 0,7991 (TabPFN: 0,8090). Ngưỡng của động cơ này lấy từ
  model/cpu_surrogate.json (chọn trên validation, xem calibrate_cpu_surrogate.py); mọi phản hồi mang engine_validated=false.

Giải thích đóng góp từng yếu tố bằng độ lệch logit khi thay từng yếu tố về giá trị điển hình (baseline), chỉ xét các trường mà yêu cầu có gửi.
Chạy độc lập:  python ml_service.py   (hoặc: uvicorn ml_service:app --port 8001 trong thư mục này)
"""
import os
import json
import time
import logging
import threading
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import joblib
import sklearn
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

logger = logging.getLogger("ml_service")
logging.basicConfig(level=logging.INFO)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.environ.get("ML_MODEL_DIR", os.path.join(ROOT, "model"))
MODEL_PATH = os.path.join(MODEL_DIR, "risk_model.joblib")
METRICS_PATH = os.path.join(MODEL_DIR, "metrics.json")
SURROGATE_PATH = os.path.join(MODEL_DIR, "cpu_surrogate.json")
ENGINE_MODE = os.environ.get("ML_ENGINE", "tabpfn").strip().lower()          # tabpfn | surrogate_hgb
REGISTRY_DIR = os.environ.get("ML_REGISTRY_DIR", "").strip()                  # nếu đặt: nạp phiên bản CURRENT của kho học tiếp (hoc_tiep_mlops) thay cho model/
ADMIN_TOKEN = os.environ.get("ML_ADMIN_TOKEN", "").strip()                    # bật điểm /reload (header X-Admin-Token); để trống = tắt
MISSING_LIMIT = float(os.environ.get("MISSING_FEATURE_LIMIT", "0.25"))        # quá tỉ lệ này đặc trưng không được gửi -> độ tin cậy thấp
NULLABLE = {"converted_workload", "hist_avg_delay", "hist_early_rate", "hist_late_last5"}   # được phép trống hợp lệ (có cờ *_missing)

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
            out[c] = X[c].map(lambda v, m=enc["maps"][c]: m.get(str(v), np.nan) if v == v and v is not None else np.nan)
        else:
            out[c] = pd.to_numeric(X[c], errors="coerce")
    return out.astype(np.float32)


def _level_of(p: float, levels) -> str:
    return next(n for lo, hi, n in levels if lo <= p < hi)


def _levels_from(thr) -> list:
    return [(0.0, float(thr[0]), "Thấp"), (float(thr[0]), float(thr[1]), "Trung bình"), (float(thr[1]), 1.01, "Cao")]


class PredictRequest(BaseModel):
    features: Dict[str, Any]
    explain: bool = True        # False: bỏ bước giải thích (giảm ~50-60 lần số lượt suy luận TabPFN mỗi yêu cầu)


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


class ServiceUnavailable(RuntimeError):
    pass


class MLModelWrapper:
    def __init__(self):
        self.bundle = None
        self.metrics = {}
        self.bag_clfs = []
        self.engine_type = "unloaded"
        self.engine_validated = False
        self.model_version = "unloaded"
        self.load_error: Optional[str] = None
        self.registry_version: Optional[str] = None
        self._failed_version: Optional[str] = None
        self._lock = threading.Lock()      # TabPFN/torch dùng chung một đối tượng: tuần tự hóa suy luận giữa các luồng của FastAPI
        self.levels = []
        self.thresholds = None
        self._load()

    def ready(self) -> bool:
        return self.bundle is not None and len(self.bag_clfs) > 0 and bool(self.levels)

    # ---- kho phiên bản (học tiếp) ----
    @staticmethod
    def _registry_current() -> Optional[str]:
        p = os.path.join(REGISTRY_DIR, "CURRENT")
        return open(p, encoding="utf-8").read().strip() if os.path.exists(p) else None

    def _bundle_from_registry(self):
        """Đọc phiên bản CURRENT của kho (hoc_tiep.ModelRegistry), kiểm tra SHA-256, đổi sang định dạng bundle của dịch vụ."""
        import hashlib
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
        bundle = dict(features=list(b["features"]), encoder=m["encoder"], contexts=m["contexts"], cat_idx=m["cat_idx"],
                      hyperparams=m["hyperparams"], tabpfn_version=m["tabpfn_version"], seed=m.get("seed", 0),
                      thresholds=list(b["thresholds"]), baseline=m["baseline"], meta=b.get("meta") or {})
        return bundle, v

    def reload(self, force: bool = False) -> bool:
        """Nạp lại khi CURRENT đổi (hoặc force). Nếu nạp phiên bản mới lỗi thì GIỮ NGUYÊN mô hình đang chạy."""
        with self._lock:
            return self._reload_locked(force)

    def _reload_locked(self, force: bool = False) -> bool:
        if not REGISTRY_DIR and not force:
            return False
        want = self._registry_current() if REGISTRY_DIR else None
        if not force and (want is None or want == self.registry_version or want == self._failed_version):
            return False
        keep = {k: getattr(self, k) for k in ("bundle", "bag_clfs", "engine_type", "engine_validated", "model_version", "load_error",
                                              "levels", "thresholds", "metrics", "registry_version")}
        self.bundle, self.bag_clfs, self.levels, self.load_error = None, [], [], None
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

    # ---- nạp mô hình ----
    def _make_tabpfn(self, k: int, device: str):
        """Dựng TabPFN giống train_model.make_tabpfn: đúng phiên bản trong bundle, không dùng phiên bản mặc định của gói."""
        from tabpfn import TabPFNClassifier
        try:
            from tabpfn.constants import ModelVersion
        except Exception:
            ModelVersion = None
        params = self.bundle.get("hyperparams", {})
        kw = dict(
            n_estimators=params.get("n_estimators", 8),
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
        if REGISTRY_DIR:
            try:
                self.bundle, self.registry_version = self._bundle_from_registry()
            except Exception as e:
                self.load_error = f"Không nạp được kho phiên bản {REGISTRY_DIR}: {type(e).__name__}: {e}"
                logger.error(self.load_error)
                return
            if ENGINE_MODE != "tabpfn":
                self.load_error = "Chế độ kho phiên bản (ML_REGISTRY_DIR) chỉ dùng với ML_ENGINE=tabpfn"
                logger.error(self.load_error)
                return
        else:
            if not os.path.exists(MODEL_PATH):
                self.load_error = f"Không tìm thấy model tại {MODEL_PATH}"
                logger.error(self.load_error)
                return
            self.bundle = joblib.load(MODEL_PATH)        # joblib là pickle: chỉ nạp file từ nguồn tin cậy
        if not REGISTRY_DIR and os.path.exists(METRICS_PATH):
            try:
                with open(METRICS_PATH, "r", encoding="utf-8") as f:
                    self.metrics = json.load(f)
            except Exception as e:
                logger.warning(f"Lỗi load metrics: {e}")
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

    def _load_tabpfn(self):
        try:
            import torch
            device = os.environ.get("TABPFN_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
            if device == "cpu":
                logger.warning("TabPFN chạy trên CPU: có thể chậm với 4 túi x 10.000 dòng ngữ cảnh (chưa đo thời gian).")
            clfs = []
            for k, (Xc, yc) in enumerate(self.bundle["contexts"]):
                clf = self._make_tabpfn(k, device)
                clf.fit(Xc, yc)
                clfs.append(clf)
            self.bag_clfs = clfs
            self.engine_type = f"tabpfn_{self.bundle.get('tabpfn_version', 'v2')}_{device}"
            self.engine_validated = True
            self.thresholds = self.bundle["thresholds"]
            self.levels = self.bundle.get("levels") or _levels_from(self.thresholds)
            self.model_version = f"TabPFN {self.bundle.get('tabpfn_version', 'v2')} ({len(clfs)} túi, {device})"
        except Exception as e:
            self.bag_clfs = []
            self.engine_type = "unavailable"
            self.load_error = f"Không nạp được TabPFN: {type(e).__name__}: {e}. Cài tabpfn và trọng số, hoặc đặt ML_ENGINE=surrogate_hgb cho bản demo (không được đánh giá)."
            logger.error(self.load_error)

    def _load_surrogate(self):
        from sklearn.ensemble import HistGradientBoostingClassifier
        cat_idx = self.bundle.get("cat_idx") or None
        self.bag_clfs = []
        for k, (Xc, yc) in enumerate(self.bundle["contexts"]):
            clf = HistGradientBoostingClassifier(max_iter=150, learning_rate=0.05, max_depth=6, categorical_features=cat_idx, random_state=42 + k)
            clf.fit(Xc, yc)
            self.bag_clfs.append(clf)
        self.engine_type = "surrogate_hgb_cpu"
        self.engine_validated = False
        sur = None
        if os.path.exists(SURROGATE_PATH):
            try:
                sur = json.load(open(SURROGATE_PATH, encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Không đọc được {SURROGATE_PATH}: {e}")
        if sur and sur.get("thresholds"):
            self.thresholds = sur["thresholds"]
            auc = sur.get("test", {}).get("roc_auc")
            self.model_version = f"SURROGATE HistGBoost ({len(self.bag_clfs)} túi; KHÔNG phải TabPFN" + (f"; AUC test {auc:.4f}" if auc else "") + ")"
        else:
            self.thresholds = self.bundle["thresholds"]
            self.model_version = f"SURROGATE HistGBoost ({len(self.bag_clfs)} túi; KHÔNG phải TabPFN; dùng ngưỡng của TabPFN nên mức cảnh báo chưa được hiệu chuẩn)"
            logger.warning("Thiếu cpu_surrogate.json: dùng ngưỡng của TabPFN cho động cơ HGB (nhóm Thấp có thể trễ > 10%).")
        self.levels = _levels_from(self.thresholds)

    # ---- suy luận ----
    def _prob_detail(self, X: pd.DataFrame):
        Xe = _apply_encoder(self.bundle["encoder"], X)
        arr = np.vstack([clf.predict_proba(Xe.values)[:, 1] for clf in self.bag_clfs])
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
            if pd.isna(X.at[0, f]):          # trường không được gửi (hoặc trống): không coi là yếu tố rủi ro/bảo vệ
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
        lg = logit(self._prob_detail(big)[0])
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

    def predict(self, features_dict: Dict[str, Any], explain: bool = True) -> Dict[str, Any]:
        with self._lock:
            if REGISTRY_DIR:
                self._reload_locked()          # CURRENT đổi (nâng cấp/quay lại) -> nạp lại trước khi dự đoán
            return self._predict(features_dict, explain)

    def _unseen(self, X: pd.DataFrame) -> List[str]:
        """Giá trị phân loại chưa từng thấy lúc huấn luyện: bộ mã hóa coi là thiếu, nên phải báo cho người dùng."""
        out = []
        for c, mp in self.bundle["encoder"]["maps"].items():
            if c in X.columns and pd.notna(X.at[0, c]) and str(X.at[0, c]) not in mp:
                out.append(f"{c}={X.at[0, c]!s}")
        return out

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


app = FastAPI(title="HUIT Task Risk Prediction ML Service", version="1.1.0")
model_wrapper = MLModelWrapper()


@app.get("/health")
def health():
    if REGISTRY_DIR:
        model_wrapper.reload()        # CURRENT đổi -> nạp lại ngay (job học tiếp dựa vào /health để xác nhận nâng cấp)
    ok = model_wrapper.ready()
    test = (model_wrapper.metrics.get("test") or {}) if model_wrapper.engine_validated else {}
    return {
        "status": "ok" if ok else "degraded",
        "model_loaded": model_wrapper.bundle is not None,
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
    }


@app.post("/reload")
def reload_model(x_admin_token: Optional[str] = Header(default=None)):
    """Nạp lại mô hình thủ công (sau khi thay model/ hoặc đổi CURRENT). Tắt nếu không đặt ML_ADMIN_TOKEN."""
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=404, detail="Chưa bật /reload (đặt ML_ADMIN_TOKEN)")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Sai mã quản trị")
    changed = model_wrapper.reload(force=True)
    return {"reloaded": changed, "registry_version": model_wrapper.registry_version, "model_version": model_wrapper.model_version,
            "load_error": model_wrapper.load_error}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    try:
        return model_wrapper.predict(req.features, explain=req.explain)
    except ServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Lỗi suy luận: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Lỗi suy luận nội bộ (xem nhật ký dịch vụ).")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)
