"""So sánh mô hình (so cặp theo cụm giảng viên), thống kê mức cảnh báo, chọn ngưỡng. pick_thresholds là bản sao của train_model.pick_thresholds."""
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

DEFAULT_THR = (0.20, 0.50)


def wilson_bounds(k, n, z=1.96):
    if n == 0:
        return 0.0, 1.0
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return float(c - h), float(c + h)


def pick_thresholds(y, p, max_late_low=0.10, min_prec_high=0.60, min_n=30, safety_margin=0.01, min_band=0.05, cao_top_pct=None):
    y = np.asarray(y); p = np.asarray(p)
    grid = np.linspace(0.02, 0.95, 94)
    t1 = t2 = None
    for t in grid:
        s_ = p < t
        n = int(s_.sum())
        if n >= min_n and wilson_bounds(int(y[s_].sum()), n)[1] + safety_margin <= max_late_low:
            t1 = float(t)
    if cao_top_pct:
        t2 = float(np.quantile(p, 1 - cao_top_pct / 100.0))
    else:
        for t in grid:
            s_ = p >= t
            n = int(s_.sum())
            if n >= min_n and wilson_bounds(int(y[s_].sum()), n)[0] - safety_margin >= min_prec_high:
                t2 = float(t)
                break
    if t1 is None or t2 is None:
        return list(DEFAULT_THR), False
    if t2 - t1 < min_band:
        gap = (min_band - (t2 - t1)) / 2
        t1, t2 = t1 - gap, t2 + gap
    if t1 <= 0 or t1 >= t2:
        return list(DEFAULT_THR), False
    return [round(t1, 2), round(t2, 2)], True


def level_of(p, thr):
    return "Thấp" if p < thr[0] else ("Trung bình" if p < thr[1] else "Cao")


def levels_array(p, thr):
    p = np.asarray(p)
    return np.where(p < thr[0], "Thấp", np.where(p < thr[1], "Trung bình", "Cao"))


def level_stats(y, p, thr):
    y = np.asarray(y); p = np.asarray(p)
    lo, hi = p < thr[0], p >= thr[1]
    return dict(n_low=int(lo.sum()), share_low=float(lo.mean()), late_low=float(y[lo].mean()) if lo.sum() >= 30 else np.nan,
                n_high=int(hi.sum()), share_high=float(hi.mean()), prec_high=float(y[hi].mean()) if hi.sum() >= 30 else np.nan,
                share_mid=float(1 - lo.mean() - hi.mean()))


def ece(y, p, k=10):
    d = pd.DataFrame({"y": np.asarray(y), "p": np.asarray(p)})
    d["q"] = pd.qcut(d.p, k, duplicates="drop")
    g = d.groupby("q", observed=True).agg(y=("y", "mean"), p=("p", "mean"), n=("y", "size"))
    return float((g.n * (g.y - g.p).abs()).sum() / g.n.sum())


def _logloss(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def metrics(y, p):
    y = np.asarray(y); p = np.asarray(p)
    return dict(auc=float(roc_auc_score(y, p)), logloss=_logloss(y, p), brier=float(brier_score_loss(y, p)),
                ece=ece(y, p), mean_pred=float(p.mean()), base_rate=float(y.mean()))


def paired_bootstrap(y, p_a, p_b, groups, n_boot=300, seed=0):
    """Hiệu b - a (b = ứng viên, a = hiện tại) trên CÙNG các dòng, lấy mẫu lại theo cụm giảng viên.
    Trả về {chỉ_số: (điểm, cận dưới 2,5%, cận trên 97,5%)} cho AUC, logloss, Brier. AUC cao hơn là tốt; logloss/Brier thấp hơn là tốt."""
    y = np.asarray(y).astype(int); a = np.asarray(p_a, float); b = np.asarray(p_b, float)
    g = np.asarray(groups)
    order = np.argsort(g, kind="stable")
    ug, start = np.unique(g[order], return_index=True)
    bounds = list(start) + [len(g)]
    members = [order[bounds[k]:bounds[k + 1]] for k in range(len(ug))]
    rng = np.random.default_rng(seed)

    def d(i):
        yi = y[i]
        if yi.min() == yi.max():
            return None
        return (roc_auc_score(yi, b[i]) - roc_auc_score(yi, a[i]), _logloss(yi, b[i]) - _logloss(yi, a[i]),
                brier_score_loss(yi, b[i]) - brier_score_loss(yi, a[i]))
    pt = d(np.arange(len(y)))
    boots = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(ug), len(ug))
        r = d(np.concatenate([members[k] for k in pick]))
        if r is not None:
            boots.append(r)
    B = np.array(boots)
    out = {}
    for j, name in enumerate(["auc", "logloss", "brier"]):
        out[name] = (float(pt[j]), float(np.percentile(B[:, j], 2.5)), float(np.percentile(B[:, j], 97.5)))
    out["n_boot_ok"] = len(boots)
    return out
