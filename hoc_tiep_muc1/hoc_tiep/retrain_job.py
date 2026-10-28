"""Huấn luyện lại có kiểm soát. Quy trình mỗi lần chạy (as_of = ngày chạy):
 1. Lấy việc đã có nhãn tại as_of từ kho phản hồi; chỉ dùng việc "đã chín" (giao trước as_of - maturity_days) cho cửa sổ kiểm tra,
    vì việc mới giao mà đã xong sớm thường là việc đúng hạn (độ trễ nhãn làm lệch tỉ lệ trễ xuống).
 2. Cửa sổ giữ lại (holdout) = việc chín giao SAU dữ liệu cuối của mô hình hiện tại => mô hình hiện tại chưa thấy, so sánh công bằng.
 3. Ứng viên: mô hình A (huấn luyện trước cửa sổ chọn ngưỡng) -> chọn ngưỡng; mô hình ứng viên (huấn luyện đến hết trước holdout) dùng ngưỡng đó.
 4. So cặp theo cụm giảng viên trên holdout; kiểm các rào chắn; chỉ nâng cấp khi tất cả đạt. Ghi quyết định vào lịch sử; không bao giờ chỉnh ngưỡng bằng holdout."""
import numpy as np
import pandas as pd

from .compare import level_stats, levels_array, metrics, paired_bootstrap, pick_thresholds
from .config import Config
from .model_backend import HGBBackend, prepare_features


def build_bundle(backend, feats, df_a, df_val, df_final, cfg, data_end, seed=0):
    """Mô hình A (df_a) -> ngưỡng trên df_val; mô hình cuối (df_final) dùng ngưỡng đó."""
    Xa, ya = prepare_features(df_a, feats), df_a.is_late.values
    thr, ok = (list((0.20, 0.50)), False)
    if len(df_val) >= 300:
        pipe_a = backend.fit(Xa, ya, seed)
        pv = backend.predict({"pipeline": pipe_a, "features": feats}, prepare_features(df_val, feats))
        thr, ok = pick_thresholds(df_val.is_late.values, pv, cfg.max_late_low, cfg.min_prec_high)
    pipe = backend.fit(prepare_features(df_final, feats), df_final.is_late.values, seed)
    return dict(backend=backend.name, pipeline=pipe, features=feats, thresholds=thr, thresholds_met_on_val=bool(ok),
                data_end=str(pd.Timestamp(df_final.assigned_date.max()).date()), n_train=int(len(df_final)))


def init_model(base_df, registry, cfg=None, backend=None, val_frac=0.15, now=None):
    """Tạo v0001 từ dữ liệu lịch sử (cột bắt buộc: assigned_date, is_late + đặc trưng)."""
    cfg, backend = cfg or Config(), backend or HGBBackend()
    df = base_df.sort_values("assigned_date").reset_index(drop=True)
    feats = list(prepare_features(df.head(5)).columns)
    k = int(len(df) * (1 - val_frac))
    b = build_bundle(backend, feats, df.iloc[:k], df.iloc[k:], df, cfg, None)
    v = registry.register(b, dict(kind="init", n_train=b["n_train"], thresholds_met_on_val=b["thresholds_met_on_val"],
                                  config=cfg.to_dict()), now=now)
    registry.promote(v, "khởi tạo", now=now)
    return v


def gate(y, p_cur, p_cand, groups, thr_cur, thr_cand, cfg):
    """Các rào chắn chất lượng trên cùng dòng. Trả về (đạt, danh sách kiểm tra, số liệu)."""
    ci = paired_bootstrap(y, p_cur, p_cand, groups, cfg.n_boot, cfg.seed)
    mc, mn = metrics(y, p_cur), metrics(y, p_cand)
    lc, ln = level_stats(y, p_cur, thr_cur), level_stats(y, p_cand, thr_cand)
    lvl_abs = (not np.isnan(ln["late_low"]) and not np.isnan(ln["prec_high"]) and
               ln["late_low"] <= cfg.max_late_low + cfg.level_slack_low and ln["prec_high"] >= cfg.min_prec_high - cfg.level_slack_high)
    lvl_rel = (not np.isnan(ln["late_low"]) and not np.isnan(lc["late_low"]) and not np.isnan(ln["prec_high"]) and not np.isnan(lc["prec_high"]) and
               ln["late_low"] <= lc["late_low"] and ln["prec_high"] >= lc["prec_high"])
    checks = {
        "auc_khong_kem": (ci["auc"][1] >= -cfg.auc_noninf_margin, f"cận dưới ΔAUC {ci['auc'][1]:+.4f} >= {-cfg.auc_noninf_margin:+.4f}"),
        "logloss_khong_kem": (ci["logloss"][2] <= cfg.logloss_noninf_margin, f"cận trên Δlogloss {ci['logloss'][2]:+.4f} <= {cfg.logloss_noninf_margin:+.4f}"),
        "auc_san": (mn["auc"] >= cfg.min_auc, f"AUC ứng viên {mn['auc']:.4f} >= {cfg.min_auc}"),
        "muc_canh_bao": (bool(lvl_abs or lvl_rel), f"Thấp trễ {ln['late_low']:.3f} (hiện tại {lc['late_low']:.3f}); Cao chính xác {ln['prec_high']:.3f} (hiện tại {lc['prec_high']:.3f})"),
    }
    if cfg.require_significant_gain:
        checks["tot_hon_co_y_nghia"] = (ci["logloss"][2] < 0, f"cận trên Δlogloss {ci['logloss'][2]:+.4f} < 0")
    ok = all(v[0] for v in checks.values())
    return ok, checks, dict(delta=ci, current=mc, candidate=mn, levels_current=lc, levels_candidate=ln)


def run(store, registry, base_df, as_of, cfg=None, backend=None, dry_run=False, kind="static", now=None):
    cfg, backend = cfg or Config(), backend or HGBBackend()
    as_of = pd.Timestamp(as_of)
    now = now if now is not None else as_of
    cur_v = registry.current()
    cur = registry.load(cur_v)
    feats = cur["features"]
    data_end = pd.Timestamp(cur["data_end"])
    dec = dict(as_of=str(as_of.date()), current=cur_v, promoted=False, candidate=None, reasons=[], checks={}, dry_run=dry_run)

    def reject(msg):
        dec["reasons"].append(msg)
        registry._log("retrain_decision", now, **{k: v for k, v in dec.items() if k != "details"})
        return dec

    fb = store.labeled_frame(as_of, kind, cfg.intervention_policy)
    dec["n_excluded_intervened"] = fb.attrs.get("n_excluded_intervened", 0)
    new = fb[fb.assigned_date > data_end] if len(fb) else fb
    dec["n_new_labeled"], dec["n_new_late"] = int(len(new)), int(new.is_late.sum()) if len(new) else 0
    miss = [c for c in feats if prepare_features(fb.tail(200), feats)[c].isna().all()] if len(fb) else list(feats)
    dec["missing_feature_share"] = round(len(miss) / max(1, len(feats)), 4)
    if len(new) < cfg.min_new_labeled:
        return reject(f"chưa đủ việc mới có nhãn: {len(new)} < {cfg.min_new_labeled}")
    if dec["n_new_late"] < cfg.min_new_late:
        return reject(f"chưa đủ việc trễ mới: {dec['n_new_late']} < {cfg.min_new_late}")
    lr = new.is_late.mean()
    if not (cfg.late_rate_bounds[0] <= lr <= cfg.late_rate_bounds[1]):
        return reject(f"tỉ lệ trễ của dữ liệu mới {lr:.3f} ngoài khoảng cho phép {cfg.late_rate_bounds} (nghi lỗi dữ liệu)")
    if dec["missing_feature_share"] > cfg.max_missing_feature_share:
        return reject(f"thiếu {len(miss)} cột đặc trưng trong dữ liệu mới: {miss[:5]}")

    pool = pd.concat([base_df[[c for c in base_df.columns if c in set(fb.columns) | set(feats) | {"task_id", "lecturer_id", "assigned_date", "is_late"}]], fb],
                     ignore_index=True)
    pool["assigned_date"] = pd.to_datetime(pool["assigned_date"])
    pool = pool.drop_duplicates(["task_id", "lecturer_id"], keep="last").sort_values("assigned_date").reset_index(drop=True)

    H1 = as_of - pd.Timedelta(days=cfg.maturity_days)
    H0 = max(H1 - pd.Timedelta(days=cfg.holdout_days), data_end + pd.Timedelta(days=1))
    V0 = H0 - pd.Timedelta(days=cfg.val_days)
    ho = pool[(pool.assigned_date >= H0) & (pool.assigned_date < H1)]
    dec["windows"] = dict(holdout=[str(H0.date()), str(H1.date())], val_start=str(V0.date()), cur_data_end=str(data_end.date()))
    dec["n_holdout"] = int(len(ho))
    dec["n_holdout_late"] = int(ho.is_late.sum()) if len(ho) else 0
    dec["n_holdout_lecturers"] = int(ho.lecturer_id.nunique()) if len(ho) else 0
    if len(ho) < cfg.min_holdout_rows:
        return reject(f"cửa sổ so sánh quá nhỏ: {len(ho)} < {cfg.min_holdout_rows} (cần đợi việc mới 'chín')")
    if dec["n_holdout_late"] < cfg.min_holdout_late or dec["n_holdout_lecturers"] < cfg.min_holdout_lecturers:
        return reject(f"cửa sổ so sánh thiếu việc trễ ({dec['n_holdout_late']}) hoặc giảng viên ({dec['n_holdout_lecturers']})")

    df_a, df_val, df_fin = pool[pool.assigned_date < V0], pool[(pool.assigned_date >= V0) & (pool.assigned_date < H0)], pool[pool.assigned_date < H0]
    cand = build_bundle(backend, feats, df_a, df_val, df_fin, cfg, None, cfg.seed)
    p_cur = backend.predict(cur, prepare_features(ho, feats))
    p_cand = backend.predict(cand, prepare_features(ho, feats))
    ok, checks, det = gate(ho.is_late.values, p_cur, p_cand, ho.lecturer_id.values, cur["thresholds"], cand["thresholds"], cfg)
    dec["checks"] = {k: dict(ok=bool(v[0]), detail=v[1]) for k, v in checks.items()}
    dec["details"] = det
    dec["candidate_thresholds"], dec["thresholds_met_on_val"] = cand["thresholds"], cand["thresholds_met_on_val"]
    dec["reasons"] = [f"{k}: {v[1]}" for k, v in checks.items() if not v[0]]
    if ok and not dry_run:
        v = registry.register(cand, dict(kind="retrain", as_of=str(as_of.date()), parent=cur_v, n_train=cand["n_train"],
                                         gate=dec["checks"], delta=det["delta"], config=cfg.to_dict()), now=now)
        registry.promote(v, f"qua mọi rào chắn tại {as_of.date()}", now=now)
        dec["promoted"], dec["candidate"] = True, v
    registry._log("retrain_decision", now, **{k: v for k, v in dec.items() if k != "details"})
    return dec
