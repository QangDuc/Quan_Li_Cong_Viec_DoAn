"""Module Giám sát Mức 2 (Level 2: Continuous Calibration & Drift Monitoring).
Theo dõi hiệu chuẩn định kỳ (Rolling Calibration Gap & ECE), phát hiện trôi dạt phân phối (PSI),
kiểm tra vi phạm cam kết ngưỡng nghiệp vụ (SLO Tracking) và đưa ra quyết định kích hoạt tái huấn luyện.
"""
import os
import json
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

try:
    from hoc_tiep.compare import ece, _logloss, level_stats, DEFAULT_THR
    from hoc_tiep.feedback_store import FeedbackStore
except ImportError:
    from compare import ece, _logloss, level_stats, DEFAULT_THR
    from feedback_store import FeedbackStore


def compute_psi(expected, actual, n_bins=10, eps=1e-4):
    """Tính chỉ số ổn định dân số (Population Stability Index - PSI) giữa hai phân phối xác suất.
    - expected: Phân phối cơ sở (lúc huấn luyện / baseline)
    - actual: Phân phối thực tế tại cửa sổ vận hành hiện tại
    Quy ước chuẩn:
    - PSI < 0.10: Ổn định (Stable / No Drift)
    - 0.10 <= PSI < 0.25: Dịch chuyển nhẹ (Moderate Drift)
    - PSI >= 0.25: Trôi dạt nghiêm trọng (Significant Drift - Cần Retrain)
    """
    exp = np.asarray(expected, float)
    act = np.asarray(actual, float)
    if len(exp) == 0 or len(act) == 0:
        return 0.0, "INSUFFICIENT_DATA"

    # Tạo 10 bins phân vị đều dựa trên phân phối expected
    quantiles = np.linspace(0, 1, n_bins + 1)
    bins = np.percentile(exp, quantiles * 100)
    bins[0] = -1e-6
    bins[-1] = 1.0 + 1e-6
    bins = np.unique(bins)

    exp_counts, _ = np.histogram(exp, bins=bins)
    act_counts, _ = np.histogram(act, bins=bins)

    exp_pct = np.clip(exp_counts / len(exp), eps, 1.0)
    act_pct = np.clip(act_counts / len(act), eps, 1.0)

    # Chuẩn hóa lại tổng = 1
    exp_pct /= exp_pct.sum()
    act_pct /= act_pct.sum()

    psi_val = float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))

    if psi_val < 0.10:
        interpretation = "STABLE"
    elif psi_val < 0.25:
        interpretation = "MODERATE_DRIFT"
    else:
        interpretation = "SIGNIFICANT_DRIFT"

    return round(psi_val, 4), interpretation


def evaluate_monitoring_window(df_window, thr=DEFAULT_THR, baseline_preds=None, min_samples=30):
    """Đánh giá toàn diện sức khỏe mô hình trên một cửa sổ thời gian xác định (tháng hoặc quý)."""
    if len(df_window) < min_samples:
        return {
            "status": "INSUFFICIENT_DATA",
            "n_samples": len(df_window),
            "message": f"Số lượng mẫu ({len(df_window)}) chưa đủ ngưỡng tối thiểu ({min_samples}) để kết luận."
        }

    y = df_window["is_late"].values.astype(int)
    p = df_window["risk_logged"].values.astype(float)

    n_samples = len(y)
    mean_p = float(p.mean())
    actual_rate = float(y.mean())
    gap = float(abs(mean_p - actual_rate))
    brier = float(brier_score_loss(y, p))
    logloss = float(_logloss(y, p))
    ece_val = float(ece(y, p))
    auc_val = float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else None

    # Phân nhóm cảnh báo theo ngưỡng nghiệp vụ
    lvl = level_stats(y, p, thr)

    # Đánh giá Drift qua PSI nếu có phân phối baseline
    psi_val, psi_desc = (None, "NO_BASELINE")
    if baseline_preds is not None and len(baseline_preds) > 0:
        psi_val, psi_desc = compute_psi(baseline_preds, p)

    # Kiểm tra các quy tắc Rào chắn & Vi phạm cam kết
    reasons = []
    status = "HEALTHY"
    action = "NORMAL"

    # Quy tắc 1: Vi phạm cam kết mức Thấp (trễ > 11.5%)
    if not np.isnan(lvl["late_low"]) and lvl["late_low"] > 0.115:
        status = "ALERT"
        action = "TRIGGER_RETRAIN"
        reasons.append(f"Vi phạm SLO: Tỉ lệ trễ nhóm Thấp ({lvl['late_low']:.1%}) vượt trần an toàn 11.5%.")

    # Quy tắc 2: Vi phạm cam kết mức Cao (chính xác < 55%)
    if not np.isnan(lvl["prec_high"]) and lvl["prec_high"] < 0.55:
        if status != "ALERT":
            status = "WARNING"
            action = "MONITOR_CLOSELY"
        reasons.append(f"Độ chính xác cảnh báo Cao ({lvl['prec_high']:.1%}) rớt dưới 55%.")

    # Quy tắc 3: Độ lệch hiệu chuẩn (Calibration Gap > 3.0%)
    if gap > 0.035:
        status = "ALERT"
        action = "TRIGGER_RETRAIN"
        reasons.append(f"Độ lệch hiệu chuẩn nghiêm trọng: Dự báo ({mean_p:.1%}) lệch thực tế ({actual_rate:.1%}) tới {gap:.1%}.")
    elif gap > 0.020:
        if status != "ALERT":
            status = "WARNING"
            action = "MONITOR_CLOSELY"
        reasons.append(f"Cảnh báo lệch hiệu chuẩn nhẹ: Gap = {gap:.1%} (> 2.0%).")

    # Quy tắc 4: Sai số ECE quá cao (> 0.03)
    if ece_val > 0.030:
        if status != "ALERT":
            status = "WARNING"
        reasons.append(f"Sai số ECE trượt = {ece_val:.4f} (> 0.030).")

    # Quy tắc 5: Trôi dạt phân phối PSI >= 0.25
    if psi_val is not None and psi_val >= 0.25:
        status = "ALERT"
        action = "TRIGGER_RETRAIN"
        reasons.append(f"Phát hiện trôi dạt dữ liệu nghiêm trọng: PSI = {psi_val} >= 0.25.")
    elif psi_val is not None and psi_val >= 0.10:
        if status != "ALERT":
            status = "WARNING"
        reasons.append(f"Phát hiện dịch chuyển nhẹ phân phối: PSI = {psi_val}.")

    if not reasons:
        reasons.append("Mô hình vận hành tối ưu, độ hiệu chuẩn và cam kết mức cảnh báo đều đạt chuẩn.")

    return {
        "status": status,
        "action": action,
        "n_samples": n_samples,
        "mean_prediction": round(mean_p, 4),
        "actual_late_rate": round(actual_rate, 4),
        "calibration_gap": round(gap, 4),
        "ece": round(ece_val, 4),
        "auc": round(auc_val, 4) if auc_val is not None else None,
        "brier": round(brier, 4),
        "logloss": round(logloss, 4),
        "thresholds": list(thr),
        "low_risk": {
            "share": round(lvl["share_low"], 4),
            "actual_late_rate": round(lvl["late_low"], 4) if not np.isnan(lvl["late_low"]) else None
        },
        "high_risk": {
            "share": round(lvl["share_high"], 4),
            "precision": round(lvl["prec_high"], 4) if not np.isnan(lvl["prec_high"]) else None
        },
        "drift_psi": {
            "value": psi_val,
            "status": psi_desc
        },
        "reasons": reasons
    }


class Level2Monitor:
    """Bộ điều phối Giám sát Mức 2 (Level 2 Continuous Monitoring Coordinator)."""

    def __init__(self, store: FeedbackStore, thr=DEFAULT_THR):
        self.store = store
        self.thr = thr

    def check_period(self, as_of, window_days=90, baseline_as_of=None):
        """Giám sát sức khỏe mô hình trong cửa sổ [as_of - window_days, as_of]."""
        as_of_dt = pd.Timestamp(as_of)
        start_dt = as_of_dt - pd.Timedelta(days=window_days)

        df = self.store.labeled_frame(as_of=as_of_dt)
        if df.empty:
            return {"status": "NO_DATA", "message": "Chưa có dữ liệu việc hoàn thành có nhãn trong kho."}

        # Lọc cửa sổ hoàn thành trong khoảng giám sát
        mask = (df["completed_date"] >= start_dt) & (df["completed_date"] <= as_of_dt)
        df_win = df[mask].reset_index(drop=True)

        baseline_preds = None
        if baseline_as_of is not None:
            df_base = df[df["completed_date"] <= pd.Timestamp(baseline_as_of)]
            if not df_base.empty:
                baseline_preds = df_base["risk_logged"].values

        eval_res = evaluate_monitoring_window(df_win, thr=self.thr, baseline_preds=baseline_preds)
        eval_res["as_of"] = str(as_of_dt.date())
        eval_res["window_start"] = str(start_dt.date())
        eval_res["window_days"] = window_days
        return eval_res

    def run_rolling_timeline(self, dates, window_days=90):
        """Chạy chuỗi giám sát trượt theo danh sách các mốc ngày (ví dụ: từng quý hoặc từng tháng)."""
        history = []
        for d in dates:
            res = self.check_period(d, window_days=window_days)
            history.append(res)
        return history
