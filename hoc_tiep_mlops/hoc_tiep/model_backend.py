"""Xử lý đặc trưng và mô hình. Dùng lại train_model.engineer/restore_dups nếu import được (để KHỚP dịch vụ); nếu không dùng bản sao tối thiểu.
Mô hình tự học tiếp trong gói này là HistGradientBoosting (chạy CPU). TabPFN: xem README_HOC_TIEP.md (đường xuất dữ liệu + so sánh dự đoán)."""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

try:
    import train_model as _T          # có trong task_risk_service / bộ công cụ
except Exception:                      # pragma: no cover
    _T = None

ID_COLS = ["task_id", "lecturer_id", "faculty", "assigned_date"]
TARGETS = ["is_late", "late_vs_original_deadline", "late_vs_current_deadline"]
EXTRA_DROP = ["completed_date", "risk_logged", "model_version_logged", "intervened", "source"]
DEFAULT_HGB = dict(learning_rate=0.08, max_iter=200, max_leaf_nodes=31, min_samples_leaf=40, l2_regularization=1.0, early_stopping=False)


def _engineer_min(df):
    df = df.copy()
    df = df.drop(columns=[c for c in df.columns if c.startswith("log_")], errors="ignore")
    if "complexity" in df:
        df["complexity_num"] = df.complexity.map({"Thấp": 0, "Trung bình": 1, "Cao": 2})
    if "priority" in df:
        df["priority_num"] = df.priority.map({"Thấp": 0, "Trung bình": 1, "Cao": 2, "Khẩn cấp": 3})
    return df


def prepare_features(df, features=None):
    eng = _T.engineer(df) if _T is not None else _engineer_min(df)
    if features is not None and _T is not None:
        eng = _T.restore_dups(eng, features)
    X = eng.drop(columns=[c for c in ID_COLS + TARGETS + EXTRA_DROP if c in eng.columns])
    if features is not None:
        X = X.reindex(columns=features)
    # các cột chữ -> object với NaN chuẩn
    for c in X.columns:
        if not pd.api.types.is_numeric_dtype(X[c]) and not pd.api.types.is_bool_dtype(X[c]):
            X[c] = X[c].astype(object).where(X[c].notna(), np.nan)
        elif pd.api.types.is_bool_dtype(X[c]):
            X[c] = X[c].astype(int)
    return X


class HGBBackend:
    name = "hgb"

    def __init__(self, **params):
        self.params = {**DEFAULT_HGB, **params}

    def fit(self, X, y, seed=0):
        cat = [c for c in X.columns if not pd.api.types.is_numeric_dtype(X[c])]
        pre = ColumnTransformer(
            [("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1, encoded_missing_value=np.nan), cat)],
            remainder="passthrough", verbose_feature_names_out=False)
        mask = [True] * len(cat) + [False] * (X.shape[1] - len(cat))
        clf = HistGradientBoostingClassifier(categorical_features=mask if cat else None, random_state=seed, **self.params)
        pipe = Pipeline([("pre", pre), ("clf", clf)])
        pipe.fit(X, np.asarray(y).astype(int))
        return pipe

    @staticmethod
    def predict(bundle, X):
        return bundle["pipeline"].predict_proba(X.reindex(columns=bundle["features"]))[:, 1]
