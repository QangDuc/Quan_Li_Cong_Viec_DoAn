#!/usr/bin/env python3
"""
MA TRẬN TÁC VỤ – NHÂN SỰ (task–personnel feature matrix)

  python build_task_personnel_matrix.py --data ./data/ml_training_set_clean.csv --out ./data
  python build_task_personnel_matrix.py --data ./data/ml_training_set_clean.csv --out ./data --enrich ./data/ml_training_set_clean.csv

Ý nghĩa (đúng đề cương khóa luận):
  Mỗi ô (giảng viên × loại công việc) tóm tắt hiệu suất lịch sử:
    - số lần đã làm loại việc đó
    - tỉ lệ trễ
    - số ngày trễ trung bình (khi trễ)
  Dùng để:
    1) Phân tích / heat-map (báo cáo)
    2) Bổ sung đặc trưng cho mô hình dự đoán (lecturer_task_late_rate, ...)
    3) Prior khi cold-start: chưa từng làm loại việc → lấy trung bình Bộ môn cùng loại việc

Tránh rò rỉ thời gian: đặc trưng của dòng t chỉ dùng các việc hoàn thành TRƯỚC assigned_date của dòng t.
"""
import argparse, json, os
import numpy as np
import pandas as pd

PRIOR_RATE = 0.20
PRIOR_STRENGTH = 3.0   # Laplace smoothing
MIN_COUNT_PERSONAL = 1  # dưới ngưỡng này ưu tiên prior Bộ môn


def _smooth_rate(late_sum, count, prior=PRIOR_RATE, strength=PRIOR_STRENGTH):
    return (late_sum + prior * strength) / (count + strength)


def build_static_matrix(df, key_task="task_type"):
    """Ma trận tổng hợp toàn tập (chỉ để báo cáo / heat-map, KHÔNG dùng trực tiếp làm đặc trưng huấn luyện)."""
    g = df.groupby(["lecturer_id", key_task], dropna=False)
    mat = g.agg(
        n_tasks=("is_late", "size"),
        n_late=("is_late", "sum"),
        late_rate=("is_late", "mean"),
    ).reset_index()
    mat["late_rate_smooth"] = _smooth_rate(mat.n_late, mat.n_tasks)
    if "department" in df.columns:
        lect_dep = df[["lecturer_id", "department"]].drop_duplicates("lecturer_id")
        mat = mat.merge(lect_dep, on="lecturer_id", how="left")
        dep = df.groupby(["department", key_task], dropna=False).agg(
            dept_n=("is_late", "size"), dept_late=("is_late", "sum")
        ).reset_index()
        dep["dept_late_rate_smooth"] = _smooth_rate(dep.dept_late, dep.dept_n)
        mat = mat.merge(dep, on=["department", key_task], how="left")
    mat["key_task"] = key_task
    return mat.sort_values(["lecturer_id", key_task]).reset_index(drop=True)


def enrich_temporal(df, key_task="task_type"):
    """
    Gắn đặc trưng ma trận vào từng dòng, chỉ dùng lịch sử TRƯỚC ngày giao (tránh rò rỉ).
    Trả về df kèm các cột:
      lecturer_task_count, lecturer_task_late_rate,
      dept_task_late_rate, task_matrix_source  (personal | department | global)
    """
    df = df.sort_values(["assigned_date", "lecturer_id"]).reset_index(drop=True)
    n = len(df)
    out_count = np.zeros(n, dtype=float)
    out_rate = np.full(n, PRIOR_RATE)
    out_dept = np.full(n, PRIOR_RATE)
    out_src = np.array(["global"] * n, dtype=object)

    # state: (lecturer_id, task) -> [count, late_sum]
    #        (department, task) -> [count, late_sum]
    lect_state = {}
    dept_state = {}
    global_state = {}  # task -> [count, late_sum]

    has_dept = "department" in df.columns
    rows = df.itertuples(index=True)

    # We need sequential update: for each row use state BEFORE adding this row's outcome.
    # Outcomes become available only after the task is "done" — in training set all rows are labeled,
    # so we treat past rows (earlier assigned_date) as history. Same lecturer+task earlier rows count.
    for i, r in enumerate(df.itertuples(index=False)):
        lid = r.lecturer_id
        task = getattr(r, key_task)
        dep = getattr(r, "department", None) if has_dept else None

        lk = (lid, task)
        if lk in lect_state:
            c, s = lect_state[lk]
            out_count[i] = c
            out_rate[i] = _smooth_rate(s, c)
            out_src[i] = "personal"
        else:
            out_count[i] = 0
            # fallback department
            if has_dept and dep is not None and (dep, task) in dept_state:
                c, s = dept_state[(dep, task)]
                out_rate[i] = _smooth_rate(s, c)
                out_src[i] = "department"
            elif task in global_state:
                c, s = global_state[task]
                out_rate[i] = _smooth_rate(s, c)
                out_src[i] = "global"
            else:
                out_rate[i] = PRIOR_RATE
                out_src[i] = "global"

        if has_dept and dep is not None and (dep, task) in dept_state:
            c, s = dept_state[(dep, task)]
            out_dept[i] = _smooth_rate(s, c)
        elif task in global_state:
            c, s = global_state[task]
            out_dept[i] = _smooth_rate(s, c)
        else:
            out_dept[i] = PRIOR_RATE

        # update state with this row's label (becomes history for later rows)
        late = float(r.is_late) if hasattr(r, "is_late") and r.is_late == r.is_late else 0.0
        if lk not in lect_state:
            lect_state[lk] = [0.0, 0.0]
        lect_state[lk][0] += 1
        lect_state[lk][1] += late
        if has_dept and dep is not None:
            dk = (dep, task)
            if dk not in dept_state:
                dept_state[dk] = [0.0, 0.0]
            dept_state[dk][0] += 1
            dept_state[dk][1] += late
        if task not in global_state:
            global_state[task] = [0.0, 0.0]
        global_state[task][0] += 1
        global_state[task][1] += late

    df = df.copy()
    df["lecturer_task_count"] = out_count
    df["lecturer_task_late_rate"] = out_rate
    df["dept_task_late_rate"] = out_dept
    df["task_matrix_source"] = out_src
    # chênh lệch so với prior toàn cục: dương = rủi ro cao hơn mặt bằng loại việc
    df["lecturer_task_late_lift"] = df["lecturer_task_late_rate"] - df["dept_task_late_rate"]
    return df


def pivot_heatmap(mat, key_task="task_type", value="late_rate_smooth", top_lecturers=15, top_tasks=12):
    """Ma trận rộng để vẽ heat-map / đưa vào báo cáo."""
    # chọn GV và task phổ biến nhất
    top_l = mat.groupby("lecturer_id").n_tasks.sum().nlargest(top_lecturers).index
    top_t = mat.groupby(key_task).n_tasks.sum().nlargest(top_tasks).index
    sub = mat[mat.lecturer_id.isin(top_l) & mat[key_task].isin(top_t)]
    wide = sub.pivot_table(index="lecturer_id", columns=key_task, values=value, aggfunc="first")
    return wide


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="ml_training_set_clean.csv (có is_late, task_type, lecturer_id)")
    ap.add_argument("--out", default="./data")
    ap.add_argument("--key-task", default="task_type", choices=["task_type", "task_group"])
    ap.add_argument("--enrich", default=None,
                    help="file CSV cần gắn đặc trưng ma trận (mặc định = --data); ghi *_with_matrix.csv")
    ap.add_argument("--inference", action="store_true",
                    help="file enrich không có nhãn: chỉ merge ma trận tĩnh đã tính từ --data")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    df = pd.read_csv(a.data, parse_dates=["assigned_date"] if "assigned_date" in pd.read_csv(a.data, nrows=0).columns else None)
    if "is_late" not in df.columns and not a.inference:
        raise SystemExit("Cần cột is_late để xây ma trận. Với dữ liệu dự đoán: truyền --data là tập có nhãn + --enrich file cần dự đoán --inference")

    # 1) Ma trận tĩnh (báo cáo)
    if "is_late" in df.columns:
        mat = build_static_matrix(df, key_task=a.key_task)
        mat_path = os.path.join(a.out, "task_personnel_matrix.csv")
        mat.to_csv(mat_path, index=False, encoding="utf-8-sig")
        print(f"Ma trận tĩnh: {len(mat)} ô (lecturer × {a.key_task}) → {mat_path}")
        print(mat.head(8).to_string(index=False))

        wide = pivot_heatmap(mat, key_task=a.key_task)
        wide_path = os.path.join(a.out, "task_personnel_matrix_wide.csv")
        wide.to_csv(wide_path, encoding="utf-8-sig")
        print(f"Ma trận wide (heat-map): {wide.shape} → {wide_path}")

        # thống kê nhanh
        coverage = (mat.n_tasks >= 3).mean()
        print(f"Tỉ lệ ô có ≥ 3 việc: {coverage:.1%} | late_rate_smooth TB: {mat.late_rate_smooth.mean():.3f}")
    else:
        mat = None
        print("Bỏ qua ma trận tĩnh (không có nhãn trong --data)")

    # 2) Enrich đặc trưng theo thời gian
    enrich_path = a.enrich or a.data
    edf = pd.read_csv(enrich_path, parse_dates=["assigned_date"] if "assigned_date" in pd.read_csv(enrich_path, nrows=0).columns else None)

    if a.inference or "is_late" not in edf.columns:
        # merge ma trận tĩnh (đã tính từ tập có nhãn)
        if mat is None:
            raise SystemExit("Cần --data có nhãn để suy ra ma trận khi --inference")
        key = ["lecturer_id", a.key_task]
        use = mat[key + ["n_tasks", "late_rate_smooth"]].rename(
            columns={"n_tasks": "lecturer_task_count", "late_rate_smooth": "lecturer_task_late_rate"}
        )
        edf = edf.merge(use, on=key, how="left")
        if "department" in edf.columns and "dept_late_rate_smooth" in mat.columns:
            dep = mat[["department", a.key_task, "dept_late_rate_smooth"]].drop_duplicates()
            dep = dep.rename(columns={"dept_late_rate_smooth": "dept_task_late_rate"})
            edf = edf.merge(dep, on=["department", a.key_task], how="left")
        else:
            edf["dept_task_late_rate"] = PRIOR_RATE
        edf["lecturer_task_count"] = edf["lecturer_task_count"].fillna(0)
        edf["lecturer_task_late_rate"] = edf["lecturer_task_late_rate"].fillna(PRIOR_RATE)
        edf["dept_task_late_rate"] = edf["dept_task_late_rate"].fillna(PRIOR_RATE)
        edf["task_matrix_source"] = np.where(edf["lecturer_task_count"] > 0, "personal", "department")
        edf["lecturer_task_late_lift"] = edf["lecturer_task_late_rate"] - edf["dept_task_late_rate"]
        print(f"[inference] merge ma trận tĩnh vào {len(edf)} dòng")
    else:
        edf = enrich_temporal(edf, key_task=a.key_task)
        src_dist = edf.task_matrix_source.value_counts(normalize=True).round(3).to_dict()
        print(f"Đặc trưng thời gian: nguồn prior = {src_dist}")
        print(f"  lecturer_task_count=0 (chưa làm loại việc): {(edf.lecturer_task_count == 0).mean():.1%}")

    out_enrich = os.path.join(a.out, os.path.splitext(os.path.basename(enrich_path))[0] + "_with_matrix.csv")
    # nếu enrich trùng data mặc định
    if os.path.abspath(enrich_path) == os.path.abspath(a.data) and not a.enrich:
        out_enrich = os.path.join(a.out, "ml_training_set_with_matrix.csv")
    edf.to_csv(out_enrich, index=False, encoding="utf-8-sig")
    print(f"Đã ghi file kèm đặc trưng ma trận: {out_enrich}")

    meta = dict(
        key_task=a.key_task,
        prior_rate=PRIOR_RATE,
        prior_strength=PRIOR_STRENGTH,
        n_matrix_cells=int(len(mat)) if mat is not None else 0,
        features_added=[
            "lecturer_task_count", "lecturer_task_late_rate",
            "dept_task_late_rate", "lecturer_task_late_lift", "task_matrix_source",
        ],
        output_matrix=os.path.join(a.out, "task_personnel_matrix.csv"),
        output_enriched=out_enrich,
    )
    json.dump(meta, open(os.path.join(a.out, "task_personnel_matrix_meta.json"), "w"),
              ensure_ascii=False, indent=2)
    print("Xong.")


if __name__ == "__main__":
    main()
