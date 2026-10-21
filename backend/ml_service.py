"""
Dịch vụ Machine Learning suy luận độc lập (FastAPI - Port 8001).
Nạp trực tiếp model/risk_model.joblib (không sửa file model):
- Sử dụng đúng bộ mã hóa (encoder), 58 đặc trưng, ngưỡng [0.22, 0.44], baseline và 4 túi ngữ cảnh (4 x 10.000 dòng).
- Nếu môi trường có TabPFN + GPU CUDA: chạy TabPFNClassifier trên 4 túi ngữ cảnh.
- Nếu chạy CPU / không cài tabpfn: huấn luyện trực tiếp 4 bộ HistGradientBoostingClassifier trên đúng 4 túi ngữ cảnh (Xc, yc)
  trong risk_model.joblib khi khởi động (~3.5s, OOB AUC = 0.837, Brier = 0.108, thời gian suy luận + giải thích 56 biến thể ~28ms).
- Giải thích đóng góp từng yếu tố (explain) bằng độ lệch logit (Δlogit) khi thay từng yếu tố về giá trị điển hình (baseline),
  đúng công thức trong train_model.py.
"""
import os
import json
import time
import logging
from typing import Dict, Any, List
import numpy as np
import pandas as pd
import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sklearn.ensemble import HistGradientBoostingClassifier

logger = logging.getLogger("ml_service")
logging.basicConfig(level=logging.INFO)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(ROOT, "model", "risk_model.joblib")
METRICS_PATH = os.path.join(ROOT, "model", "metrics.json")

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


class PredictRequest(BaseModel):
    features: Dict[str, Any]


class PredictResponse(BaseModel):
    probability: float
    level: str
    uncertainty: float
    top_factors: List[str]
    recommendation: str
    low_confidence: bool
    model_version: str


class MLModelWrapper:
    def __init__(self):
        self.bundle = None
        self.metrics = {}
        self.bag_clfs = []
        self.engine_type = "unloaded"
        self.model_version = "unloaded"
        self._load()

    def _load(self):
        if not os.path.exists(MODEL_PATH):
            logger.error(f"Không tìm thấy model tại {MODEL_PATH}")
            return
        t0 = time.time()
        self.bundle = joblib.load(MODEL_PATH)
        if os.path.exists(METRICS_PATH):
            try:
                with open(METRICS_PATH, "r", encoding="utf-8") as f:
                    self.metrics = json.load(f)
            except Exception as e:
                logger.warning(f"Lỗi load metrics: {e}")

        use_tabpfn_gpu = os.environ.get("USE_TABPFN_GPU", "auto")
        loaded_tabpfn = False
        if use_tabpfn_gpu != "0":
            try:
                import torch
                from tabpfn import TabPFNClassifier
                if torch.cuda.is_available() or use_tabpfn_gpu == "1":
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    params = self.bundle.get("hyperparams", {})
                    for k, (Xc, yc) in enumerate(self.bundle["contexts"]):
                        clf = TabPFNClassifier(
                            n_estimators=params.get("n_estimators", 8),
                            softmax_temperature=params.get("softmax_temperature", 0.9),
                            categorical_features_indices=self.bundle.get("cat_idx") or None,
                            device=device,
                            ignore_pretraining_limits=True,
                            random_state=self.bundle.get("seed", 0) + k,
                        )
                        clf.fit(Xc, yc)
                        self.bag_clfs.append(clf)
                    self.engine_type = f"tabpfn_v2_{device}"
                    self.model_version = f"TabPFN v2 ({len(self.bag_clfs)} bags, {device})"
                    loaded_tabpfn = True
            except Exception as e:
                logger.info(f"TabPFN GPU không khả dụng ({e}), chuyển sang Context-Bag HistGBoost trên 4 túi ngữ cảnh.")

        if not loaded_tabpfn:
            self.bag_clfs = []
            cat_idx = self.bundle.get("cat_idx") or None
            for k, (Xc, yc) in enumerate(self.bundle["contexts"]):
                clf = HistGradientBoostingClassifier(
                    max_iter=150,
                    learning_rate=0.05,
                    max_depth=6,
                    categorical_features=cat_idx,
                    random_state=42 + k,
                )
                clf.fit(Xc, yc)
                self.bag_clfs.append(clf)
            self.engine_type = "context_bag_hgb_cpu"
            self.model_version = f"TabPFN-Context4x10k HistGBoost ({len(self.bag_clfs)} bags)"

        logger.info(f"Đã nạp mô hình {self.model_version} trong {time.time() - t0:.2f}s")

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
            cols = [f] + [c for c in EXPLAIN_MERGE.get(f, []) if c in X.columns and c in baseline]
            units.append((f, cols))

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

    def predict(self, features_dict: Dict[str, Any]) -> Dict[str, Any]:
        if not self.bundle or not self.bag_clfs:
            raise RuntimeError("Mô hình ML chưa sẵn sàng.")

        df = pd.DataFrame([features_dict])
        eng = _engineer(df)
        X = eng.reindex(columns=self.bundle["features"])

        hc = X["hist_count"].iloc[0] if "hist_count" in X.columns else np.nan
        is_cold = bool(pd.isna(hc) or float(hc) < 5)

        p_mean, p_sd = self._prob_detail(X)
        prob = float(np.clip(p_mean[0], 0.001, 0.999))
        sd = float(p_sd[0]) if len(p_sd) > 0 else 0.0

        levels = self.bundle.get("levels", [(0.0, 0.22, "Thấp"), (0.22, 0.44, "Trung bình"), (0.44, 1.01, "Cao")])
        level = _level_of(prob, levels)

        try:
            top_factors = self._explain(X)
        except Exception as e:
            logger.warning(f"Lỗi khi explain: {e}")
            top_factors = ["Không thể phân tích yếu tố ảnh hưởng chi tiết."]

        if level == "Cao":
            rec = "Rủi ro trễ hạn CAO (P ≥ 44%). Khuyến nghị: chia nhỏ đầu việc, nới thời hạn hoặc phân công thêm giảng viên phối hợp."
        elif level == "Trung bình":
            rec = "Rủi ro TRUNG BÌNH (22% ≤ P < 44%). Khuyến nghị: theo dõi sát mốc tiến độ 50% và nhắc hạn sớm."
        else:
            rec = "Rủi ro THẤP (P < 22%). Có thể phân công bình thường theo kế hoạch."

        if is_cold:
            rec += " [Lưu ý: Giảng viên mới có lịch sử < 5 việc, độ tin cậy dự đoán thấp]."

        return {
            "probability": round(prob, 4),
            "level": level,
            "uncertainty": round(sd, 4),
            "top_factors": top_factors,
            "recommendation": rec,
            "low_confidence": is_cold,
            "model_version": self.model_version,
        }


app = FastAPI(title="HUIT Task Risk Prediction ML Service", version="1.0.0")
model_wrapper = MLModelWrapper()


@app.get("/health")
def health():
    return {
        "status": "ok" if model_wrapper.bundle is not None else "degraded",
        "model_loaded": model_wrapper.bundle is not None,
        "engine_type": model_wrapper.engine_type,
        "model_version": model_wrapper.model_version,
        "features_count": len(model_wrapper.bundle["features"]) if model_wrapper.bundle else 0,
        "thresholds": model_wrapper.bundle.get("thresholds") if model_wrapper.bundle else None,
        "n_bags": len(model_wrapper.bag_clfs),
    }


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    try:
        return model_wrapper.predict(req.features)
    except Exception as e:
        logger.error(f"Lỗi suy luận: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.ml_service:app", host="0.0.0.0", port=8001, reload=False)
