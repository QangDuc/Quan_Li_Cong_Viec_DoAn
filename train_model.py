#!/usr/bin/env python3
"""
HUẤN LUYỆN MÔ HÌNH CHÍNH: TabPFN (tabular foundation model, học trong ngữ cảnh — in-context learning).
Hỗ trợ đặc trưng ma trận tác vụ–nhân sự (lecturer_task_*, dept_task_*) nếu có trong dữ liệu
(chạy build_task_personnel_matrix.py trước).

  python train_model.py train   --data ./data/ml_training_set_with_matrix.csv --out ./model [--prune]
  python train_model.py predict --model ./model/risk_model.joblib --input viec_moi.csv --output ket_qua.csv [--explain]

Khác với CatBoost: TabPFN là mạng Transformer ĐÃ HUẤN LUYỆN TRƯỚC trên hàng triệu bảng dữ liệu tổng hợp.
"Huấn luyện" ở đây KHÔNG cập nhật trọng số: các dòng huấn luyện được đưa vào làm NGỮ CẢNH (context) và mô hình
dự đoán các dòng mới bằng một lượt suy luận. Vì vậy:
  * model/risk_model.joblib lưu NGỮ CẢNH (tập dòng huấn luyện đã chọn) + bộ mã hóa; trọng số TabPFN được tải lại từ cache khi dự đoán.
  * chi phí nằm ở BƯỚC DỰ ĐOÁN (tỉ lệ với |ngữ cảnh| x |dòng cần dự đoán|) -> nên dùng GPU (Colab T4 là đủ).
  * ngữ cảnh bị giới hạn (--max-context; mặc định ~10.000 dòng, v2.5+ trên GPU ~50.000 dòng). Có thể dùng nhiều "túi" ngữ cảnh khác nhau (--n-bags).

Quy trình: chia THEO THỜI GIAN 60/15/25 -> chọn siêu tham số trên validation -> dựng ngữ cảnh từ train+validation
-> đánh giá trên tập test (khoảng tin cậy bootstrap) -> chọn ngưỡng cảnh báo theo mục tiêu nghiệp vụ trên validation.

Cần: pip install tabpfn   (lần đầu tải trọng số từ Hugging Face; v2.5 trở lên cần chấp nhận giấy phép + HF token)
"""
import argparse, json, os, warnings
import numpy as np, pandas as pd, joblib
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss
warnings.filterwarnings("ignore")

try:
    import torch
    from tabpfn import TabPFNClassifier
    try:
        from tabpfn.constants import ModelVersion
    except Exception:  # bản tabpfn cũ không có ModelVersion
        ModelVersion = None
except ImportError as e:
    raise SystemExit("Chưa cài tabpfn. Chạy: pip install tabpfn\n" + str(e))

ID_COLS = ["task_id", "lecturer_id", "faculty", "assigned_date"]
TARGETS = ["is_late", "late_vs_original_deadline", "late_vs_current_deadline"]
LABEL = "is_late"
LEVEL_NAMES = ["Thấp", "Trung bình", "Cao"]
DEFAULT_THR = (0.20, 0.50)
# Cấu hình TabPFN (đặt bằng tham số dòng lệnh; xem main)
TABPFN_VERSION = "v2"     # v2 (mở, không cần đăng nhập) | v2.5 | v2.6 | ... (cần chấp nhận giấy phép trên Hugging Face)
DEVICE = "auto"           # auto | cpu | cuda
MAX_CONTEXT = None        # số dòng ngữ cảnh tối đa mỗi túi; None -> 10.000 (v2 hoặc CPU) / 50.000 (v2.5+ trên GPU)
N_BAGS = 1                # số túi ngữ cảnh độc lập (trung bình xác suất)
CONTEXT_MODE = "random"   # random: lấy ngẫu nhiên | recent: ưu tiên các dòng mới nhất theo thời gian
PRED_BATCH = 4000         # số dòng dự đoán mỗi lượt (giới hạn bộ nhớ)
# Lưới siêu tham số gọn (chọn theo log-loss validation). TabPFN gần như không cần chỉnh tay.
PARAM_GRID = [
    dict(n_estimators=8, softmax_temperature=0.9),
    dict(n_estimators=8, softmax_temperature=1.0),
    dict(n_estimators=16, softmax_temperature=0.9),
]
GROUPS = {
    "giảng viên": ["academic_rank", "degree", "department", "management_role", "years_experience", "tenure_days"],
    "tải giảng dạy": ["teaching_hours_semester", "course_count", "student_count", "supervised_student_count"],
    "lịch năm học": ["academic_period", "semester", "academic_week", "peak_season", "accreditation_flag", "holiday_in_window"],
    "mô tả công việc": ["task_group", "task_type", "task_subtype", "assignment_level", "assignment_mode", "assignment_channel",
                        "team_size", "require_approval", "converted_workload", "converted_workload_missing"],
    "thời hạn": ["available_days", "working_days_available", "expected_duration_days", "deadline_pressure",
                 "is_urgent_assignment", "estimated_effort_hours", "deadline_month_end"],
    "lịch sử giảng viên": ["hist_count", "hist_late_rate", "hist_avg_delay", "hist_early_rate", "hist_avg_delay_missing",
                           "hist_early_rate_missing", "is_cold_start", "hist_late_last5", "hist_late_last5_missing", "late_last_30d"],
    "tải hiện tại": ["active_tasks", "active_high_priority_tasks", "overdue_open_tasks", "deadlines_next_7d",
                     "deadlines_next_14d", "workload_next_14d"],
    "độ phức tạp & ưu tiên": ["complexity", "complexity_num", "priority", "priority_num", "subtask_count",
                              "dependency_count", "require_external_input"],
    "ma trận tác vụ–nhân sự": ["lecturer_task_count", "lecturer_task_late_rate", "dept_task_late_rate",
                               "lecturer_task_late_lift", "task_matrix_source"],
    "tiến độ": ["progress_pct", "progress_gap", "expected_progress_pct", "days_elapsed", "days_remaining",
                "checkpoint_fraction", "progress_missing"],
}
NAMES = {
    "deadline_pressure": "áp lực deadline", "active_tasks": "số việc đang mở",
    "workload_next_14d": "khối lượng đến hạn trong 14 ngày (giờ)",
    "deadlines_next_7d": "số hạn trong 7 ngày tới", "deadlines_next_14d": "số hạn trong 14 ngày tới",
    "hist_late_rate": "tỉ lệ trễ lịch sử", "complexity": "độ phức tạp", "priority": "mức ưu tiên",
    "available_days": "số ngày được giao", "expected_duration_days": "thời lượng điển hình (ngày)",
    "dependency_count": "số bên phụ thuộc", "subtask_count": "số đầu việc con",
    "require_external_input": "cần đầu vào bên ngoài", "overdue_open_tasks": "số việc đang mở đã quá hạn",
    "active_high_priority_tasks": "số việc ưu tiên cao đang mở", "years_experience": "kinh nghiệm (năm)",
    "tenure_days": "số ngày công tác tại Khoa", "teaching_hours_semester": "giờ giảng học kỳ",
    "academic_period": "giai đoạn năm học", "progress_gap": "chênh lệch tiến độ so với kỳ vọng (%)",
    "task_type": "loại công việc", "management_role": "vai trò quản lý",
    "hist_count": "số việc đã hoàn thành trước đây", "hist_late_last5": "tỉ lệ trễ 5 việc gần nhất",
    "late_last_30d": "số việc trễ trong 30 ngày qua", "deadline_month_end": "hạn chót cuối tháng",
    "progress_missing": "chưa cập nhật tiến độ", "student_count": "số sinh viên phụ trách",
    "complexity_num": "độ phức tạp (0-2)", "priority_num": "mức ưu tiên (0-3)",
    "course_count": "số học phần", "supervised_student_count": "số SV hướng dẫn",
    "hist_avg_delay": "số ngày trễ TB trước đây", "hist_early_rate": "tỉ lệ hoàn thành sớm trước đây",
    "lecturer_task_late_rate": "tỉ lệ trễ GV với loại việc này",
    "lecturer_task_count": "số lần GV đã làm loại việc này",
    "dept_task_late_rate": "tỉ lệ trễ Bộ môn với loại việc",
    "lecturer_task_late_lift": "lệch tỉ lệ trễ GV so với Bộ môn",
    "task_matrix_source": "nguồn prior ma trận tác vụ–nhân sự",
}


def engineer(df):
    df = df.copy()
    df = df.drop(columns=[c for c in df.columns if c.startswith("log_")], errors="ignore")
    if "complexity" in df:
        df["complexity_num"] = df.complexity.map({"Thấp": 0, "Trung bình": 1, "Cao": 2})
    if "priority" in df:
        df["priority_num"] = df.priority.map({"Thấp": 0, "Trung bình": 1, "Cao": 2, "Khẩn cấp": 3})
    return df


def split_cols(X):
    cat = [c for c in X.columns if not pd.api.types.is_numeric_dtype(X[c])]
    return cat, [c for c in X.columns if c not in cat]


def resolve_device():
    if DEVICE != "auto":
        return DEVICE
    return "cuda" if torch.cuda.is_available() else "cpu"


def context_limit():
    if MAX_CONTEXT:
        return int(MAX_CONTEXT)
    # v2 được huấn luyện trước tới ~10.000 dòng; v2.5 trở lên tới ~50.000 dòng (cần GPU)
    big = TABPFN_VERSION != "v2" and resolve_device() == "cuda"
    return 50000 if big else 10000


def fit_encoder(X):
    """Mã hóa thứ tự cho cột phân loại (TabPFN nhận số + chỉ số cột phân loại); NaN giữ nguyên."""
    cat, num = split_cols(X)
    maps = {}
    for c in cat:
        vals = X[c].dropna().astype(str).unique()
        maps[c] = {v: i for i, v in enumerate(sorted(vals))}
    return dict(cat=cat, num=num, maps=maps, order=list(X.columns))


def apply_encoder(enc, X):
    out = pd.DataFrame(index=X.index)
    for c in enc["order"]:
        if c not in X.columns:
            out[c] = np.nan
        elif c in enc["maps"]:
            out[c] = X[c].map(lambda v, m=enc["maps"][c]: m.get(str(v), np.nan) if v == v and v is not None else np.nan)
        else:
            out[c] = pd.to_numeric(X[c], errors="coerce")
    return out.astype(np.float32)


def make_tabpfn(params, cat_idx, seed=0):
    kw = dict(
        n_estimators=params.get("n_estimators", 8),
        softmax_temperature=params.get("softmax_temperature", 0.9),
        categorical_features_indices=cat_idx or None,
        device=resolve_device(),
        ignore_pretraining_limits=True,
        random_state=seed,
    )
    if ModelVersion is not None and hasattr(TabPFNClassifier, "create_default_for_version"):
        return TabPFNClassifier.create_default_for_version(ModelVersion(TABPFN_VERSION), **kw)
    return TabPFNClassifier(**kw)


def pick_context(n, y, k, seed):
    """Chọn chỉ số dòng làm ngữ cảnh cho túi thứ k."""
    lim = context_limit()
    if n <= lim:
        return np.arange(n)
    if CONTEXT_MODE == "recent":
        # dữ liệu đã sắp theo thời gian: nửa ngữ cảnh là các dòng mới nhất, nửa còn lại lấy ngẫu nhiên từ phần cũ hơn
        half = lim // 2
        rng = np.random.default_rng(seed + 1000 * k)
        older = rng.choice(n - half, size=lim - half, replace=False)
        return np.sort(np.concatenate([older, np.arange(n - half, n)]))
    rng = np.random.default_rng(seed + 1000 * k)
    return np.sort(rng.choice(n, size=lim, replace=False))


def get_clf(bundle, k):
    """Dựng (lười) bộ phân loại TabPFN cho túi k từ ngữ cảnh đã lưu; cache trong bundle['_clf']."""
    cache = bundle.setdefault("_clf", {})
    if k not in cache:
        Xc, yc = bundle["contexts"][k]
        clf = make_tabpfn(bundle["hyperparams"], bundle["cat_idx"], seed=bundle.get("seed", 0) + k)
        clf.fit(Xc, yc)
        cache[k] = clf
    return cache[k]


def prob_detail(model, X, ckpt=None, tag=None):
    """Xác suất trễ hạn: (trung bình các túi, độ lệch chuẩn giữa các túi). Độ lệch = 0 nếu chỉ có 1 túi.
    Độ lệch giữa các túi là thước đo độ KHÔNG CHẮC CHẮN của mô hình (ngữ cảnh khác nhau cho kết quả khác nhau).
    Nếu truyền ckpt (thư mục) và tag: mỗi lô (túi, đoạn dòng) được lưu ra đĩa ngay khi tính xong và được nạp lại nếu đã có
    -> dừng giữa chừng rồi chạy lại chỉ mất tối đa một lô."""
    import time
    Xe = apply_encoder(model["encoder"], X)
    n = len(Xe)
    n_bags = len(model["contexts"])
    chunks_per_bag = max(1, -(-n // PRED_BATCH))
    total = n_bags * chunks_per_bag
    per_bag = []
    n_cached = n_done = 0
    t0 = time.time()
    for k in range(n_bags):
        clf = None
        ps = []
        for ci, i in enumerate(range(0, n, PRED_BATCH)):
            path = os.path.join(ckpt, f"{tag}_b{k}_c{ci}.npy") if ckpt and tag else None
            if path and os.path.exists(path):
                ps.append(np.load(path))
                n_cached += 1
                continue
            if clf is None:
                clf = get_clf(model, k)
            part = clf.predict_proba(Xe.iloc[i:i + PRED_BATCH].values)[:, 1]
            if path:
                tmp = path + ".tmp.npy"
                np.save(tmp, part)
                os.replace(tmp, path)
            ps.append(part)
            n_done += 1
            if tag and total > 1:
                el = time.time() - t0
                left = (total - n_done - n_cached) * el / n_done
                print(f"   [{tag}] lô {n_done + n_cached}/{total} (túi {k + 1}/{n_bags}) | đã chạy {el / 60:.1f} phút | còn khoảng {left / 60:.1f} phút", flush=True)
        per_bag.append(np.concatenate(ps) if ps else np.zeros(0))
    if ckpt and tag:
        print(f"   [{tag}] {n_done} lô vừa tính, {n_cached} lô nạp lại từ điểm lưu", flush=True)
    arr = np.vstack(per_bag)
    mean = np.clip(arr.mean(axis=0), 1e-4, 1 - 1e-4)
    sd = arr.std(axis=0) if arr.shape[0] > 1 else np.zeros(n)
    return mean, sd


def prob(model, X):
    """Xác suất trễ hạn: trung bình các túi ngữ cảnh."""
    return prob_detail(model, X)[0]


def ece(y, p, k=10):
    d = pd.DataFrame({"y": y, "p": p, "q": pd.qcut(p, k, duplicates="drop")})
    g = d.groupby("q", observed=True).agg(y=("y", "mean"), p=("p", "mean"), n=("y", "size"))
    return float((g.n * (g.y - g.p).abs()).sum() / g.n.sum())


def metrics(y, p):
    top = p >= np.quantile(p, 0.8)
    return dict(
        roc_auc=roc_auc_score(y, p),
        pr_auc=average_precision_score(y, p),
        brier=brier_score_loss(y, p),
        ece=ece(y, p),
        base_rate=float(y.mean()),
        recall_at_top20pct=float(y[top].sum() / max(1, y.sum())),
        precision_at_top20pct=float(y[top].mean()),
    )


def boot_auc(y, p, groups=None, n=300, seed=0):
    """Khoảng tin cậy 95% bootstrap của AUC.
    Nếu truyền `groups` (ví dụ lecturer_id) thì lấy mẫu lại THEO CỤM: các dòng của cùng một giảng viên không độc lập,
    nên lấy mẫu theo từng dòng làm khoảng tin cậy hẹp hơn thực tế."""
    y = np.asarray(y)
    p = np.asarray(p)
    rng = np.random.default_rng(seed)
    a = []
    if groups is None:
        for _ in range(n):
            i = rng.integers(0, len(y), len(y))
            if y[i].min() != y[i].max():
                a.append(roc_auc_score(y[i], p[i]))
    else:
        g = np.asarray(groups)
        order = np.argsort(g, kind="stable")
        ug, start = np.unique(g[order], return_index=True)
        bounds = list(start) + [len(g)]
        members = [order[bounds[k]:bounds[k + 1]] for k in range(len(ug))]
        for _ in range(n):
            pick = rng.integers(0, len(ug), len(ug))
            i = np.concatenate([members[k] for k in pick])
            if y[i].min() != y[i].max():
                a.append(roc_auc_score(y[i], p[i]))
    return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]


def wilson_bounds(k, n, z=1.96):
    """Cận dưới/trên (Wilson, ~95%) của một tỉ lệ k/n."""
    if n == 0:
        return 0.0, 1.0
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return float(c - h), float(c + h)


def pick_thresholds(y, p, max_late_low=0.10, min_prec_high=0.60, min_n=30, safety_margin=0.01, min_band=0.05,
                    cao_top_pct=None):
    """Chọn hai ngưỡng (Thấp | Trung bình | Cao) trên validation, có BIÊN AN TOÀN:
      - Thấp: tỉ lệ trễ của nhóm p < t1 phải <= max_late_low, tính theo CẬN TRÊN 95% (Wilson) cộng thêm safety_margin
              (ngưỡng chọn vừa khít trên một lát validation thường kém đi khi sang giai đoạn sau).
      - Cao: độ chính xác của nhóm p >= t2 phải >= min_prec_high, tính theo CẬN DƯỚI 95% trừ safety_margin.
      - Dải 'Trung bình' tối thiểu min_band (nới t1 xuống / t2 lên; việc này chỉ làm hai nhóm biên tinh hơn, không làm mất đảm bảo).
      - cao_top_pct (tuỳ chọn, ví dụ 10): thay t2 bằng ngưỡng để đúng top x% việc rơi vào 'Cao' (theo năng lực xử lý).
    Trả về (ngưỡng, đạt_mục_tiêu)."""
    y = np.asarray(y)
    p = np.asarray(p)
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


def levels_from(thr):
    return [(0.0, thr[0], LEVEL_NAMES[0]), (thr[0], thr[1], LEVEL_NAMES[1]), (thr[1], 1.01, LEVEL_NAMES[2])]


def level_of(p, levels):
    return next(n for lo, hi, n in levels if lo <= p < hi)


def baseline_values(X):
    cat, num = split_cols(X)
    b = {}
    for c in num:
        b[c] = float(X[c].median()) if X[c].notna().any() else 0.0
    for c in cat:
        b[c] = X[c].mode().iloc[0] if X[c].notna().any() else ""
    return b


NAMES.update({
    "task_group": "nhóm công việc", "task_subtype": "loại và quy mô công việc", "assignment_level": "cấp giao việc",
    "assignment_mode": "hình thức giao (cá nhân/nhóm)", "assignment_channel": "kênh giao việc", "team_size": "số người thực hiện",
    "is_urgent_assignment": "giao gấp (áp lực deadline > 1,25)", "require_approval": "cần phê duyệt",
    "holiday_in_window": "có nghỉ lễ/Tết trong thời gian thực hiện", "converted_workload": "giờ chuẩn quy đổi",
    "semester": "học kỳ", "academic_week": "tuần của năm học", "peak_season": "mùa cao điểm (thi/chấm/nộp điểm)",
    "accreditation_flag": "trong đợt kiểm định", "academic_rank": "chức danh", "degree": "học vị", "department": "bộ môn",
    "converted_workload_missing": "thiếu giờ chuẩn quy đổi", "hist_avg_delay_missing": "thiếu số ngày trễ TB trước đây",
    "hist_early_rate_missing": "thiếu tỉ lệ làm sớm trước đây", "hist_late_last5_missing": "thiếu tỉ lệ trễ 5 việc gần nhất",
    "is_cold_start": "giảng viên mới (ít lịch sử)",
})


def fmt(v):
    """Hiển thị gọn: số nguyên giữ nguyên, số lớn làm tròn, số nhỏ 3 chữ số có nghĩa."""
    if v is None or (isinstance(v, float) and v != v) or (isinstance(v, np.floating) and v != v):
        return "thiếu"
    if isinstance(v, (int, float, np.number)) and v == v:
        v = float(v)
        if v == int(v):
            return str(int(v))
        return f"{v:.0f}" if abs(v) >= 100 else f"{v:.3g}"
    return str(v)


# Các đặc trưng thực chất là một yếu tố (bản chữ + bản số) -> gộp khi giải thích, hiển thị bản đầu tiên
EXPLAIN_MERGE = {"complexity": ["complexity_num"], "priority": ["priority_num"]}


def explain(m, X, k_up=3, k_down=2, min_effect=0.02):
    """Đóng góp xấp xỉ: Δ logit khi đặt từng yếu tố về giá trị điển hình (trung vị/mốt của dữ liệu huấn luyện).
    Mọi biến thể (n dòng x số yếu tố) được GỘP thành MỘT lần suy luận để tiết kiệm thời gian.
    Lưu ý: 'tăng/giảm rủi ro' là SO VỚI MỨC ĐIỂN HÌNH, không phải mức rủi ro tuyệt đối; các đóng góp không cộng lại đúng bằng
    tổng thay đổi vì các đặc trưng tương quan với nhau; đây là gợi ý yếu tố nổi bật, không chứng minh quan hệ nhân quả."""
    X = X.reset_index(drop=True)
    features, baseline = m["features"], m["baseline"]
    merged = {x for v in EXPLAIN_MERGE.values() for x in v}
    units = []  # (tên hiển thị, [các cột cùng thay])
    for f in features:
        if f in merged or f not in X.columns or f not in baseline:
            continue
        cols = [f] + [c for c in EXPLAIN_MERGE.get(f, []) if c in X.columns and c in baseline]
        units.append((f, cols))
    n = len(X)

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
    lg = logit(prob(m, big))
    l0 = lg[:n]
    C = pd.DataFrame({f: l0 - lg[(j + 1) * n:(j + 2) * n] for j, (f, _) in enumerate(units)})
    out = []
    for i in range(n):
        row = C.iloc[i].sort_values(ascending=False)
        up = row[row > min_effect].head(k_up)
        down = row[row < -min_effect].sort_values().head(k_down)
        txt = lambda s: "; ".join(f"{NAMES.get(f, f)} = {fmt(X.at[i, f])}" for f in s.index)
        parts = []
        if len(up):
            parts.append("Tăng rủi ro (so với mức điển hình): " + txt(up))
        if len(down):
            parts.append("Giảm rủi ro: " + txt(down))
        out.append(" | ".join(parts) if parts else "Không có yếu tố nổi bật so với mức điển hình")
    return out


def fit_model(X, y, params=None, seed=0):
    """"Huấn luyện" TabPFN = chọn ngữ cảnh + mã hóa. X phải được sắp theo thời gian (cũ -> mới).
    Trả về bundle dùng được với prob()."""
    X = X.reset_index(drop=True)
    y = np.asarray(y).astype(int)
    params = params or PARAM_GRID[0]
    enc = fit_encoder(X)
    Xe = apply_encoder(enc, X)
    cat_idx = [Xe.columns.get_loc(c) for c in enc["cat"] if c in Xe.columns]
    contexts = []
    for k in range(max(1, N_BAGS)):
        idx = pick_context(len(Xe), y, k, seed)
        contexts.append((Xe.iloc[idx].values, y[idx]))
    return dict(
        model_name="tabpfn", tabpfn_version=TABPFN_VERSION, features=list(X.columns), hyperparams=params,
        encoder=enc, contexts=contexts, cat_idx=cat_idx, seed=seed,
        cat_features=[c for c in enc["cat"]], context_mode=CONTEXT_MODE, max_context=context_limit(),
    )


def permutation_importance(bundle, X, y, n_rows=1500, seed=0):
    """Độ giảm AUC khi xáo trộn từng đặc trưng (trên mẫu con của validation) — TabPFN không có importance nội tại."""
    rng = np.random.default_rng(seed)
    i = rng.choice(len(X), size=min(n_rows, len(X)), replace=False)
    Xs, ys = X.iloc[i].reset_index(drop=True), np.asarray(y)[i]
    base = roc_auc_score(ys, prob(bundle, Xs))
    rows = []
    for f in bundle["features"]:
        if f not in Xs.columns:
            continue
        Xp = Xs.copy()
        Xp[f] = Xp[f].values[rng.permutation(len(Xp))]
        rows.append((f, base - roc_auc_score(ys, prob(bundle, Xp))))
    imp = pd.DataFrame(rows, columns=["feature", "auc_drop"]).sort_values("auc_drop", ascending=False)
    imp["importance"] = imp["auc_drop"]
    return imp[["feature", "importance", "auc_drop"]]


def unseen_categories(enc, X, max_examples=3):
    """Giá trị phân loại có mặt trong dữ liệu mới nhưng chưa từng xuất hiện lúc huấn luyện (sẽ bị coi là thiếu)."""
    out = {}
    for c, mp in enc["maps"].items():
        if c not in X.columns:
            continue
        v = X[c].dropna().astype(str)
        bad = v[~v.isin(mp.keys())]
        if len(bad):
            out[c] = dict(n=int(len(bad)), pct=round(100 * len(bad) / max(1, len(X)), 1), examples=sorted(bad.unique())[:max_examples])
    return out


def make_meta(df_all, trva_mask, cols, args_used):
    """Thông tin để biết khi nào cần huấn luyện lại và kiểm tra tương thích khi nạp mô hình."""
    import datetime, platform
    d = df_all.loc[trva_mask, "assigned_date"]
    try:
        import tabpfn as _tp
        tp_ver = getattr(_tp, "__version__", "?")
    except Exception:
        tp_ver = "?"
    return dict(
        trained_at=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        data_start=str(d.min().date()), data_end=str(d.max().date()), n_rows=int(trva_mask.sum()),
        n_features=len(cols), feature_schema=list(cols),
        versions=dict(python=platform.python_version(), tabpfn=tp_ver, torch=getattr(torch, "__version__", "?")),
        settings=args_used,
    )


def slim(bundle):
    """Bản để lưu: bỏ các bộ phân loại TabPFN đã dựng (sẽ dựng lại từ ngữ cảnh khi nạp)."""
    return {k: v for k, v in bundle.items() if k != "_clf"}


_nn = lambda v: None if v != v else round(float(v), 4)


class _Tee:
    """Ghi mọi thứ in ra màn hình đồng thời vào file (để bảng kết quả không mất khi đóng phiên Colab)."""
    def __init__(self, stream, path):
        self.stream, self.f = stream, open(path, "a", encoding="utf-8")

    def write(self, x):
        self.stream.write(x)
        self.f.write(x)
        self.f.flush()
        return len(x)

    def flush(self):
        self.stream.flush()
        self.f.flush()

    def close(self):
        self.f.close()


def train(a):
    import sys
    os.makedirs(a.out, exist_ok=True)
    _orig = sys.stdout
    sys.stdout = _Tee(_orig, os.path.join(a.out, "train_report.txt"))
    print("\n" + "=" * 70 + "\nLẦN CHẠY train — " + pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S") + "\n" + "=" * 70)
    try:
        return _train(a)
    finally:
        sys.stdout.close()
        sys.stdout = _orig


def _train(a):
    for k, v in dict(max_late_low=0.10, min_prec_high=0.60, safety_margin=0.01, min_band=0.05, cao_top_pct=None,
                     resume=False, keep_checkpoint=False).items():
        if not hasattr(a, k):
            setattr(a, k, v)
    df = engineer(pd.read_csv(a.data, parse_dates=["assigned_date"])).sort_values("assigned_date").reset_index(drop=True)
    y = df[LABEL].astype(int).values
    X = df.drop(columns=[c for c in ID_COLS + TARGETS if c in df.columns])
    t1, t2 = df.assigned_date.quantile(0.60), df.assigned_date.quantile(0.75)
    tr = (df.assigned_date <= t1).values
    va = ((df.assigned_date > t1) & (df.assigned_date <= t2)).values
    te = (df.assigned_date > t2).values
    trva = tr | va
    print(
        f"Train {tr.sum()} (<= {t1.date()}) | Validation {va.sum()} | Test {te.sum()} (> {t2.date()}, "
        f"{int(y[te].sum())} việc trễ) | {X.shape[1]} đặc trưng | mô hình: TabPFN {TABPFN_VERSION} | "
        f"thiết bị: {resolve_device()} | ngữ cảnh tối đa {context_limit():,} dòng x {N_BAGS} túi ({CONTEXT_MODE})"
    )
    if resolve_device() == "cpu":
        print("[LƯU Ý] Đang chạy CPU: dự đoán TabPFN chậm. Nên dùng GPU (Colab: Runtime > Change runtime type > T4) "
              "hoặc giảm --max-context / dùng --no-tune.")

    # --- điểm lưu (checkpoint): cho phép dừng giữa chừng rồi chạy lại với --resume ---
    ckpt = os.path.join(a.out, "checkpoint")
    key = dict(data=os.path.basename(a.data), n_rows=int(len(df)), n_late=int(y.sum()), tabpfn=TABPFN_VERSION,
               n_bags=N_BAGS, max_context=context_limit(), mode=CONTEXT_MODE, batch=PRED_BATCH, no_tune=bool(a.no_tune),
               grid=[sorted(p.items()) for p in (PARAM_GRID[:1] if a.no_tune else PARAM_GRID)], n_features=int(X.shape[1]))
    os.makedirs(a.out, exist_ok=True)
    keyfile = os.path.join(ckpt, "key.json")
    if os.path.isdir(ckpt):
        same = False
        if a.resume and os.path.exists(keyfile):
            try:
                same = json.load(open(keyfile, encoding="utf-8")) == json.loads(json.dumps(key))
            except Exception:
                same = False
        if not same:
            if a.resume:
                print("[LƯU Ý] Điểm lưu cũ không khớp cấu hình/dữ liệu hiện tại -> bỏ và tính lại từ đầu.")
            import shutil
            shutil.rmtree(ckpt, ignore_errors=True)
        else:
            print("Tiếp tục từ điểm lưu: " + ckpt)
    os.makedirs(ckpt, exist_ok=True)
    json.dump(key, open(keyfile, "w", encoding="utf-8"), ensure_ascii=False)

    all_cols = list(X.columns)
    cols = all_cols
    pruned = []
    grid = PARAM_GRID[:1] if a.no_tune else PARAM_GRID

    def select(cols_, grid_, use_ckpt=True):
        best = None
        for gi, params in enumerate(grid_):
            m = fit_model(X.loc[tr, cols_], y[tr], params=params)
            p = prob_detail(m, X.loc[va, cols_], ckpt=ckpt if use_ckpt else None, tag=f"va{gi}")[0]
            ll = log_loss(y[va], p)
            print(f"   [tune] {params} -> log-loss validation = {ll:.4f}", flush=True)
            if best is None or ll < best[0]:
                best = (ll, params, m, p)
        return best

    val_ll, best_params, m_tr, p_va = select(all_cols, grid, use_ckpt=not a.prune)

    if a.prune:
        drop = []
        for gname, gcols in GROUPS.items():
            gc = [c for c in gcols if c in all_cols]
            if not gc:
                continue
            keep = [c for c in all_cols if c not in gc]
            try:
                ll, _, _, _ = select(keep, [best_params], use_ckpt=False)
                d = ll - val_ll
            except Exception:
                d = 1.0
            print(f"   [prune] bỏ nhóm '{gname}': Δ log-loss validation = {d:+.4f}")
            if d <= 0.0002:
                drop += gc
                pruned.append(gname)
        if drop:
            keep = [c for c in all_cols if c not in drop]
            try:
                ll, params, m, p_new = select(keep, [best_params], use_ckpt=False)
                d = ll - val_ll
            except Exception:
                d = 1.0
            if d <= 0.0005:
                cols, best_params, m_tr, val_ll, p_va = keep, params, m, ll, p_new
                print(f"   -> bỏ các nhóm {pruned} ({len(all_cols) - len(keep)} cột), Δ tổng = {d:+.4f}")
            else:
                pruned = []
                print(f"   -> bỏ đồng thời làm xấu đi ({d:+.4f}), giữ đầy đủ đặc trưng")

    # Dựng ngữ cảnh cuối từ train+validation (dữ liệu đã sắp theo thời gian)
    m_main = fit_model(X.loc[trva, cols], y[trva], params=best_params)
    p_te = prob_detail(m_main, X.loc[te, cols], ckpt=None if a.prune else ckpt, tag="te")[0]
    res = metrics(y[te], p_te)
    grp = df.loc[te, "lecturer_id"].values if "lecturer_id" in df.columns else None
    ci = boot_auc(y[te], p_te, groups=grp)        # theo cụm giảng viên (đúng hơn)
    ci_rows = boot_auc(y[te], p_te)               # theo từng dòng (để đối chiếu với các bản cũ)

    # ngưỡng trên validation (mô hình chỉ thấy train)
    thr, ok = pick_thresholds(y[va], p_va, max_late_low=a.max_late_low, min_prec_high=a.min_prec_high,
                              safety_margin=a.safety_margin, min_band=a.min_band, cao_top_pct=a.cao_top_pct)
    levels = levels_from(thr)

    print(f"\nMÔ HÌNH CHÍNH: TabPFN {TABPFN_VERSION} | params = {best_params} | log-loss validation = {val_ll:.4f}")
    print("\n=== KẾT QUẢ TRÊN TẬP TEST (theo thời gian) ===\n" + pd.Series({k: round(v, 3) for k, v in res.items()}).to_string())
    print(f"AUC {res['roc_auc']:.3f} (khoảng tin cậy 95%, bootstrap theo giảng viên: {ci[0]:.3f}-{ci[1]:.3f}; "
          f"theo từng dòng: {ci_rows[0]:.3f}-{ci_rows[1]:.3f})")

    lv = pd.DataFrame({"level": [level_of(v, levels) for v in p_te], "y": y[te]}).groupby("level").y.agg(["count", "mean"]).reindex(LEVEL_NAMES)
    lv.columns = ["so_viec", "ti_le_tre_thuc_te"]
    lv["so_viec"] = lv["so_viec"].fillna(0)
    lv["ti_le_viec"] = lv.so_viec / lv.so_viec.sum()
    print(
        f"\n=== MỨC CẢNH BÁO (ngưỡng {thr}"
        f"{' chọn trên validation, có biên an toàn ' + str(a.safety_margin) if ok else ' mặc định [giả định]'}) ===\n"
        + lv.round(3).to_string()
    )
    if ok:
        low_rate, high_rate = lv.loc["Thấp", "ti_le_tre_thuc_te"], lv.loc["Cao", "ti_le_tre_thuc_te"]
        print(f"   Mục tiêu: nhóm Thấp trễ <= {a.max_late_low:.0%} -> thực tế trên test {low_rate:.1%} "
              f"({'đạt' if low_rate <= a.max_late_low else 'KHÔNG đạt'}); nhóm Cao chính xác >= {a.min_prec_high:.0%} -> thực tế {high_rate:.1%} "
              f"({'đạt' if high_rate >= a.min_prec_high else 'KHÔNG đạt'})")

    dec = pd.DataFrame({"p": p_te, "y": y[te]})
    dec["nhom"] = pd.qcut(dec.p, 10, duplicates="drop")
    print("\n=== HIỆU CHUẨN THEO DECILE ===\n" + dec.groupby("nhom", observed=True).mean().round(3).to_string())
    dec_json = [dict(mean_pred=round(float(g.p.mean()), 4), late_rate=round(float(g.y.mean()), 4), n=int(len(g)))
                for _, g in dec.groupby("nhom", observed=True)]

    seg = {}
    Xt = X.loc[te]
    for sname, mask in [
        ("giảng viên mới (lịch sử < 5 việc)", (Xt.get("hist_count", pd.Series(99, index=Xt.index)) < 5).values),
        ("giảng viên có lịch sử >= 5 việc", (Xt.get("hist_count", pd.Series(0, index=Xt.index)) >= 5).values),
        ("mùa cao điểm", (Xt.get("peak_season", pd.Series(0, index=Xt.index)) == 1).values),
        ("độ phức tạp cao", (Xt.get("complexity", pd.Series("", index=Xt.index)) == "Cao").values),
    ]:
        yy, pp = y[te][mask], p_te[mask]
        seg[sname] = dict(
            n=int(mask.sum()),
            late_rate=round(float(yy.mean()), 3) if mask.sum() else None,
            mean_pred=round(float(pp.mean()), 3) if mask.sum() else None,
            auc=round(float(roc_auc_score(yy, pp)), 3)
            if mask.sum() >= 50 and yy.sum() >= 15 and yy.sum() < len(yy)
            else None,
        )
    print("\n=== HIỆU QUẢ THEO NHÓM ===\n" + pd.DataFrame(seg).T.to_string())

    os.makedirs(a.out, exist_ok=True)
    meta = make_meta(df, trva, cols, dict(n_bags=N_BAGS, max_context=context_limit(), context_mode=CONTEXT_MODE,
                                          tabpfn_version=TABPFN_VERSION, no_tune=bool(a.no_tune)))
    json.dump(
        dict(
            main_model="tabpfn",
            tabpfn_version=TABPFN_VERSION,
            device=resolve_device(),
            context=dict(max_context=context_limit(), n_bags=N_BAGS, mode=CONTEXT_MODE,
                         n_rows_in_context=int(len(m_main["contexts"][0][1]))),
            hyperparams=best_params,
            val_logloss=round(float(val_ll), 4),
            test={k: round(float(v), 4) for k, v in res.items()},
            test_auc_ci95=[round(c, 4) for c in ci],
            test_auc_ci95_method="bootstrap theo cụm giảng viên",
            test_auc_ci95_by_row=[round(c, 4) for c in ci_rows],
            threshold_config=dict(max_late_low=a.max_late_low, min_prec_high=a.min_prec_high, safety_margin=a.safety_margin,
                                  min_band=a.min_band, cao_top_pct=a.cao_top_pct),
            thresholds=thr,
            thresholds_from_target_precision=ok,
            pruned_groups=pruned,
            segments=seg,
            alert_levels={k: dict(n=int(r.so_viec), late_rate=(None if r.so_viec == 0 else round(float(r.ti_le_tre_thuc_te), 4)),
                                  share=round(float(r.ti_le_viec), 4)) for k, r in lv.iterrows()},
            target_check=(dict(max_late_low=a.max_late_low, actual_low=_nn(lv.loc["Thấp", "ti_le_tre_thuc_te"]),
                               ok_low=bool(lv.loc["Thấp", "ti_le_tre_thuc_te"] <= a.max_late_low),
                               min_prec_high=a.min_prec_high, actual_high=_nn(lv.loc["Cao", "ti_le_tre_thuc_te"]),
                               ok_high=bool(lv.loc["Cao", "ti_le_tre_thuc_te"] >= a.min_prec_high)) if ok else None),
            calibration_deciles=dec_json,
            n_train=int(trva.sum()),
            n_test=int(te.sum()),
            meta=meta,
        ),
        open(f"{a.out}/metrics.json", "w"),
        ensure_ascii=False,
        indent=2,
    )
    base = baseline_values(X.loc[trva, cols])
    out = slim(m_main)
    out.update(levels=levels, thresholds=thr, baseline=base, meta=meta)
    joblib.dump(out, f"{a.out}/risk_model.joblib", compress=3)
    print(f"\nĐã lưu ngữ cảnh + bộ mã hóa + báo cáo vào {os.path.abspath(a.out)}")
    if not a.keep_checkpoint:
        import shutil
        shutil.rmtree(ckpt, ignore_errors=True)
    if a.importance_rows > 0:
        print(f"\nĐang tính độ quan trọng đặc trưng (hoán vị, {a.importance_rows} dòng validation; mô hình ĐÃ được lưu, có thể dừng bước này)...", flush=True)
        imp = permutation_importance(m_tr, X.loc[va, cols], y[va], n_rows=a.importance_rows)
        print("=== TOP 12 ĐẶC TRƯNG (giảm AUC khi xáo trộn) ===\n" + imp.head(12).round(4).to_string(index=False))
        imp.to_csv(f"{a.out}/feature_importance.csv", index=False)

    ex = df[te].assign(p=p_te).sort_values("p", ascending=False).head(3)
    texts = explain(dict(m_main, baseline=base), X.loc[ex.index, cols])
    print("\n=== VÍ DỤ CẢNH BÁO ===")
    for (_, r), tx in zip(ex.iterrows(), texts):
        print(
            f"- {r.task_id} ({r.task_type if 'task_type' in r else ''}): có {r.p:.0%} khả năng giảng viên {r.lecturer_id} "
            f"trễ deadline này -> mức {level_of(r.p, levels)} "
            f"(thực tế: {'trễ' if r[LABEL] else 'đúng hạn'})\n    {tx}"
        )


STALE_DAYS = 180          # cảnh báo nếu dữ liệu cần dự đoán cách dữ liệu huấn luyện quá số ngày này


def predict(a):
    m = joblib.load(a.model)
    # dùng đúng phiên bản/thiết bị lúc huấn luyện, trừ khi người dùng ghi đè
    global TABPFN_VERSION
    if not a.tabpfn_version:
        TABPFN_VERSION = m.get("tabpfn_version", TABPFN_VERSION)
    meta = m.get("meta")
    if meta:
        print(f"Mô hình: TabPFN {m.get('tabpfn_version', '?')} | huấn luyện {meta['trained_at'][:10]} trên dữ liệu "
              f"{meta['data_start']} -> {meta['data_end']} ({meta['n_rows']:,} dòng) | {len(m['contexts'])} túi ngữ cảnh")
    df = pd.read_csv(a.input)
    eng = engineer(df)
    lost = [c for c in m["features"] if c not in eng.columns]
    if lost:
        print(
            f"[CẢNH BÁO] Thiếu {len(lost)}/{len(m['features'])} cột đặc trưng (sẽ coi là trống): {lost[:8]}...\n"
            "          -> chạy clean_data.py --inference (và build_task_personnel_matrix nếu cần) trước khi dự đoán."
        )
    X = eng.reindex(columns=m["features"])

    # --- kiểm tra đầu vào ---
    unseen = unseen_categories(m["encoder"], X)
    for c, info in unseen.items():
        print(f"[CẢNH BÁO] Cột '{c}': {info['n']} giá trị ({info['pct']}%) chưa từng thấy lúc huấn luyện, ví dụ {info['examples']} "
              "-> được coi là thiếu; dự đoán cho các dòng này kém tin cậy.")
    if meta and "assigned_date" in df.columns:
        try:
            gap = (pd.to_datetime(df["assigned_date"]).max() - pd.Timestamp(meta["data_end"])).days
            if gap > STALE_DAYS:
                print(f"[CẢNH BÁO] Dữ liệu cần dự đoán muộn hơn dữ liệu huấn luyện {gap} ngày (> {STALE_DAYS}); "
                      "nên kiểm tra hiệu chuẩn trên dữ liệu gần đây hoặc huấn luyện lại.")
        except Exception:
            pass

    p, sd = prob_detail(m, X)
    out = df[[c for c in ID_COLS if c in df.columns]].copy()
    out["risk_probability"] = p.round(3)
    out["risk_level"] = [level_of(v, m["levels"]) for v in p]
    if len(m["contexts"]) > 1:
        out["risk_uncertainty"] = sd.round(3)      # độ lệch chuẩn giữa các túi: càng lớn mô hình càng không chắc
    notes = [[] for _ in range(len(X))]
    hc = X["hist_count"] if "hist_count" in X.columns else pd.Series(np.nan, index=X.index)
    cold = (hc.fillna(0) < 5).values
    if "is_cold_start" in X.columns:
        cold = cold | (X["is_cold_start"].fillna(0) == 1).values
    for i in np.where(cold)[0]:
        notes[i].append("Giảng viên mới (lịch sử < 5 việc): độ tin cậy thấp")
    for c in unseen:
        v = X[c].astype(str)
        bad = (~v.isin(m["encoder"]["maps"][c].keys())) & X[c].notna().values
        for i in np.where(bad.values)[0]:
            notes[i].append(f"'{c}' có giá trị chưa từng thấy")
    out["ghi_chu"] = ["; ".join(x) for x in notes]
    if a.explain:
        out["top_factors"] = explain(m, X)
    out.to_csv(a.output, index=False, encoding="utf-8-sig")
    print(out.drop(columns=["top_factors"], errors="ignore").head(10).to_string(index=False))
    print(f"\nĐã ghi {a.output}")


def configure(a):
    """Nhận cấu hình TabPFN từ dòng lệnh."""
    global TABPFN_VERSION, DEVICE, MAX_CONTEXT, N_BAGS, CONTEXT_MODE
    if getattr(a, "tabpfn_version", None):
        TABPFN_VERSION = a.tabpfn_version
    DEVICE = getattr(a, "device", "auto") or "auto"
    MAX_CONTEXT = getattr(a, "max_context", None)
    N_BAGS = getattr(a, "n_bags", 1) or 1
    CONTEXT_MODE = getattr(a, "context_mode", "random") or "random"


def add_tabpfn_args(p):
    p.add_argument("--tabpfn-version", default=None, help="v2 (mặc định, mở) | v2.5 | v2.6 ... (cần HF token + giấy phép)")
    p.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    p.add_argument("--max-context", type=int, default=None, help="số dòng ngữ cảnh tối đa/túi (mặc định 10000; 50000 nếu v2.5+ trên GPU)")
    p.add_argument("--n-bags", type=int, default=1, help="số túi ngữ cảnh độc lập, lấy trung bình xác suất")
    p.add_argument("--context-mode", default="random", choices=["random", "recent"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("train")
    t.add_argument("--data", required=True)
    t.add_argument("--out", default="./model")
    t.add_argument("--prune", action="store_true", help="loại các nhóm đặc trưng không giúp ích trên validation (chậm)")
    t.add_argument("--resume", action="store_true", help="tiếp tục từ điểm lưu trong <out>/checkpoint nếu cấu hình và dữ liệu không đổi")
    t.add_argument("--keep-checkpoint", action="store_true", help="giữ lại thư mục điểm lưu sau khi huấn luyện xong")
    t.add_argument("--no-tune", action="store_true", help="bỏ chọn siêu tham số, dùng cấu hình đầu tiên (nhanh)")
    t.add_argument("--importance-rows", type=int, default=0, help="số dòng tính độ quan trọng hoán vị; 0 = bỏ qua (mặc định). RẤT TỐN: ~ (số đặc trưng+1) x số túi x số dòng lượt suy luận")
    t.add_argument("--max-late-low", type=float, default=0.10, help="mục tiêu: nhóm 'Thấp' có tỉ lệ trễ tối đa")
    t.add_argument("--min-prec-high", type=float, default=0.60, help="mục tiêu: nhóm 'Cao' có độ chính xác tối thiểu")
    t.add_argument("--safety-margin", type=float, default=0.01, help="biên an toàn khi chọn ngưỡng (đề phòng lệch giữa validation và giai đoạn sau)")
    t.add_argument("--min-band", type=float, default=0.05, help="độ rộng tối thiểu của dải 'Trung bình'")
    t.add_argument("--cao-top-pct", type=float, default=None, help="(tuỳ chọn) đặt ngưỡng 'Cao' để đúng top x%% việc rơi vào nhóm Cao theo năng lực xử lý")
    add_tabpfn_args(t)
    t.set_defaults(f=train)
    q = sp.add_parser("predict")
    q.add_argument("--model", required=True)
    q.add_argument("--input", required=True)
    q.add_argument("--output", default="predictions.csv")
    q.add_argument("--explain", action="store_true")
    add_tabpfn_args(q)
    q.set_defaults(f=predict)
    a = ap.parse_args()
    configure(a)
    a.f(a)
