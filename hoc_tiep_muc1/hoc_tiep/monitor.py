"""Module Giám sát Mức 2 (Level 2: Continuous Calibration & Drift Monitoring).
Theo dõi hiệu chuẩn định kỳ, phát hiện trôi dạt phân phối dự đoán (PSI), kiểm tra cam kết ngưỡng nghiệp vụ (SLO) và đề xuất kích hoạt tái huấn luyện.
Cảnh báo dựa trên kiểm định thống kê (Wilson, z-test) và cần tối thiểu 1.000 việc có nhãn trong cửa sổ: với cửa sổ nhỏ, quy tắc ngưỡng cố định
báo động giả gần như liên tục kể cả khi mô hình hiệu chuẩn hoàn hảo (xem tests/test_hoc_tiep.py::t_monitor_false_alarm_rate).
"""
import os
import json
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

try:
    from hoc_tiep.compare import ece, _logloss, level_stats, wilson_bounds, DEFAULT_THR
    from hoc_tiep.feedback_store import FeedbackStore
except ImportError:
    from compare import ece, _logloss, level_stats, wilson_bounds, DEFAULT_THR
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


MIN_SAMPLES_DEFAULT = 1000      # dưới mức này chỉ báo INSUFFICIENT_DATA (nhiễu lấy mẫu quá lớn để kết luận)
SLO_LOW_TARGET, SLO_LOW_ALERT = 0.10, 0.115     # mục tiêu và trần của tỉ lệ trễ nhóm Thấp
SLO_HIGH_TARGET, SLO_HIGH_ALERT = 0.60, 0.55    # mục tiêu và sàn của độ chính xác nhóm Cao


def calibration_z(y, p):
    """z-test độ lệch trung bình: (số trễ thực - số trễ kỳ vọng) / sqrt(tổng p(1-p)). Với mô hình hiệu chuẩn hoàn hảo, z ~ N(0,1)."""
    var = float(np.sum(p * (1 - p)))
    return float((np.sum(y) - np.sum(p)) / np.sqrt(max(var, 1e-12)))


def evaluate_monitoring_window(df_window, thr=DEFAULT_THR, baseline_preds=None, min_samples=MIN_SAMPLES_DEFAULT):
    """Đánh giá sức khỏe mô hình trên một cửa sổ có nhãn. Cảnh báo chỉ nổ khi sai lệch CÓ Ý NGHĨA THỐNG KÊ và đủ lớn về thực tiễn:
      * SLO mức Thấp: cận dưới Wilson 95% của tỉ lệ trễ nhóm Thấp > 11,5% (ALERT) hoặc > 10% (WARNING)
      * SLO mức Cao: cận trên Wilson 95% của độ chính xác nhóm Cao < 55% (ALERT) hoặc < 60% (WARNING)
      * Hiệu chuẩn: |z| >= 3,5 và |lệch| >= 3,5 điểm % (ALERT); |z| >= 3 và |lệch| >= 2 điểm % (WARNING)
      * Trôi dạt phân phối dự đoán: PSI >= 0,25 (ALERT), >= 0,10 (WARNING)
    ECE chỉ được báo cáo (không phải điều kiện cảnh báo) vì ECE lệch dương ở mẫu nhỏ.
    Lưu ý: cửa sổ tính theo ngày hoàn thành; việc trễ hoàn thành muộn hơn nên tỉ lệ trễ của cửa sổ gần nhất có thể lệch thấp."""
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
    z = calibration_z(y, p)
    brier = float(brier_score_loss(y, p))
    logloss = float(_logloss(y, p))
    ece_val = float(ece(y, p))
    auc_val = float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else None

    lvl = level_stats(y, p, thr)
    lo_mask, hi_mask = p < thr[0], p >= thr[1]
    low_ci = wilson_bounds(int(y[lo_mask].sum()), int(lo_mask.sum())) if lo_mask.sum() >= 30 else (np.nan, np.nan)
    high_ci = wilson_bounds(int(y[hi_mask].sum()), int(hi_mask.sum())) if hi_mask.sum() >= 30 else (np.nan, np.nan)

    psi_val, psi_desc = (None, "NO_BASELINE")
    if baseline_preds is not None and len(baseline_preds) > 0:
        psi_val, psi_desc = compute_psi(baseline_preds, p)

    reasons, status, action = [], "HEALTHY", "NORMAL"

    def raise_to(level, act):
        nonlocal status, action
        if level == "ALERT":
            status, action = "ALERT", "TRIGGER_RETRAIN"
        elif status != "ALERT":
            status, action = "WARNING", "MONITOR_CLOSELY"

    # 1. Cam kết mức Thấp
    if not np.isnan(low_ci[0]):
        if low_ci[0] > SLO_LOW_ALERT:
            raise_to("ALERT", None)
            reasons.append(f"Vi phạm SLO: nhóm Thấp trễ {lvl['late_low']:.1%} (KTC 95% [{low_ci[0]:.1%}; {low_ci[1]:.1%}]), cận dưới vượt trần {SLO_LOW_ALERT:.1%}.")
        elif low_ci[0] > SLO_LOW_TARGET:
            raise_to("WARNING", None)
            reasons.append(f"Nhóm Thấp trễ {lvl['late_low']:.1%} (KTC 95% [{low_ci[0]:.1%}; {low_ci[1]:.1%}]) vượt mục tiêu {SLO_LOW_TARGET:.0%} có ý nghĩa thống kê.")
    # 2. Cam kết mức Cao
    if not np.isnan(high_ci[1]):
        if high_ci[1] < SLO_HIGH_ALERT:
            raise_to("ALERT", None)
            reasons.append(f"Vi phạm SLO: độ chính xác nhóm Cao {lvl['prec_high']:.1%} (KTC 95% [{high_ci[0]:.1%}; {high_ci[1]:.1%}]), cận trên dưới sàn {SLO_HIGH_ALERT:.0%}.")
        elif high_ci[1] < SLO_HIGH_TARGET:
            raise_to("WARNING", None)
            reasons.append(f"Độ chính xác nhóm Cao {lvl['prec_high']:.1%} (KTC 95% [{high_ci[0]:.1%}; {high_ci[1]:.1%}]) thấp hơn mục tiêu {SLO_HIGH_TARGET:.0%} có ý nghĩa thống kê.")
    # 3. Hiệu chuẩn trung bình
    if abs(z) >= 3.5 and gap >= 0.035:
        raise_to("ALERT", None)
        reasons.append(f"Lệch hiệu chuẩn có ý nghĩa: dự báo {mean_p:.1%} so với thực tế {actual_rate:.1%} (lệch {gap:.1%}, z = {z:+.1f}).")
    elif abs(z) >= 3.0 and gap >= 0.020:
        raise_to("WARNING", None)
        reasons.append(f"Lệch hiệu chuẩn nhẹ nhưng có ý nghĩa: dự báo {mean_p:.1%} so với thực tế {actual_rate:.1%} (lệch {gap:.1%}, z = {z:+.1f}).")
    # 4. Trôi dạt phân phối dự đoán
    if psi_val is not None and psi_val >= 0.25:
        raise_to("ALERT", None)
        reasons.append(f"Phân phối dự đoán trôi dạt nghiêm trọng: PSI = {psi_val} >= 0.25.")
    elif psi_val is not None and psi_val >= 0.10:
        raise_to("WARNING", None)
        reasons.append(f"Phân phối dự đoán dịch chuyển nhẹ: PSI = {psi_val}.")

    if not reasons:
        reasons.append("Không có sai lệch có ý nghĩa thống kê so với cam kết và hiệu chuẩn.")

    return {
        "status": status,
        "action": action,
        "n_samples": n_samples,
        "mean_prediction": round(mean_p, 4),
        "actual_late_rate": round(actual_rate, 4),
        "calibration_gap": round(gap, 4),
        "calibration_z": round(z, 2),
        "ece": round(ece_val, 4),
        "auc": round(auc_val, 4) if auc_val is not None else None,
        "brier": round(brier, 4),
        "logloss": round(logloss, 4),
        "thresholds": list(thr),
        "low_risk": {
            "share": round(lvl["share_low"], 4),
            "actual_late_rate": round(lvl["late_low"], 4) if not np.isnan(lvl["late_low"]) else None,
            "wilson_95": [round(low_ci[0], 4), round(low_ci[1], 4)] if not np.isnan(low_ci[0]) else None,
        },
        "high_risk": {
            "share": round(lvl["share_high"], 4),
            "precision": round(lvl["prec_high"], 4) if not np.isnan(lvl["prec_high"]) else None,
            "wilson_95": [round(high_ci[0], 4), round(high_ci[1], 4)] if not np.isnan(high_ci[0]) else None,
        },
        "drift_psi": {
            "value": psi_val,
            "status": psi_desc
        },
        "reasons": reasons
    }


class Level2Monitor:
    """Bộ điều phối Giám sát Mức 2 (Level 2 Continuous Monitoring Coordinator)."""

    def __init__(self, store: FeedbackStore, thr=DEFAULT_THR, min_samples=MIN_SAMPLES_DEFAULT):
        self.store = store
        self.thr = thr
        self.min_samples = min_samples

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

        eval_res = evaluate_monitoring_window(df_win, thr=self.thr, baseline_preds=baseline_preds, min_samples=self.min_samples)
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
