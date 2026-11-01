"""Đối chiếu TOÀN BỘ đặc trưng của dịch vụ (app.ml_features.build_features) với đặc trưng do bộ sinh + clean_data + enrich_temporal tạo ra.
Cách làm: sinh một bộ dữ liệu mô phỏng nhỏ (24 giảng viên, 3 năm, vài giây), dựng lại đầu vào thô của từng dòng (việc, giảng viên, lịch sử đã xong,
việc đang mở, đếm ma trận) rồi so đặc trưng dịch vụ tính ra với cột trong tập huấn luyện.
Chạy:  cd service && python test_feature_parity_full.py [--rows 800] [--keep]"""
import os, sys, types, json, shutil, subprocess, tempfile, datetime as dt, argparse
import numpy as np, pandas as pd
here = os.path.dirname(os.path.abspath(__file__)); ts_dir = os.path.join(here, "..", "training_scripts")
sys.path.insert(0, here); sys.path.insert(0, ts_dir)
import gen_synthetic_data_v5 as g
import build_task_personnel_matrix as bm
from app import ml_features as mf

EXACT = None          # đặc trưng phải khớp tuyệt đối (trừ sai số làm tròn)
TOL = dict(deadline_pressure=0.02, years_experience=0.06)   # sai số tương đối/tuyệt đối cho phép (bộ sinh làm tròn 3 chữ số / 1 chữ số)


def build_data(out, seed=7):
    subprocess.run([sys.executable, os.path.join(ts_dir, "gen_synthetic_data_v5.py"), "--n_lecturers", "24", "--years", "3", "--n_faculties", "2",
                    "--burn_in_days", "0", "--seed", str(seed), "--out", out], check=True, capture_output=True)
    subprocess.run([sys.executable, os.path.join(ts_dir, "clean_data.py"), "--input", f"{out}/ml_training_set.csv",
                    "--output", f"{out}/ml_training_set_clean.csv"], check=True, capture_output=True)


def run(rows=800, keep=False, verbose=True):
    out = tempfile.mkdtemp(prefix="parity_")
    try:
        build_data(out)
        clean = pd.read_csv(f"{out}/ml_training_set_clean.csv", parse_dates=["assigned_date"])
        raw = pd.read_csv(f"{out}/ml_training_set.csv", parse_dates=["assigned_date"])[["task_id", "lecturer_id", "estimated_effort_hours"]]
        ta = pd.read_csv(f"{out}/task_assignments.csv", parse_dates=["assigned_date", "original_deadline", "completed_date"])
        ta = ta[["task_id", "lecturer_id", "original_deadline", "completed_date", "delay_days"]]
        exp = bm.enrich_temporal(clean.copy(), data_path=f"{out}/ml_training_set_clean.csv")      # đặc trưng ma trận lúc huấn luyện
        exp = exp.merge(raw, on=["task_id", "lecturer_id"], how="left").merge(ta, on=["task_id", "lecturer_id"], how="left")
        exp = exp.sort_values(["lecturer_id", "assigned_date", "task_id"]).reset_index(drop=True)
        exp["pos"] = exp.groupby("lecturer_id").cumcount()
        hol = [(d.date(), d.date()) for d in pd.to_datetime(g.HOLIDAYS)]
        acc = [(pd.Timestamp(a).date(), pd.Timestamp(b).date()) for a, b in g.CFG["accreditation_windows"]]

        need = ["subtask_count", "dependency_count", "require_external_input", "years_experience"]
        pool = exp[exp[need].notna().all(axis=1)]
        samp = pool.sample(min(rows, len(pool)), random_state=1)
        by_l = {k: v for k, v in exp.groupby("lecturer_id")}
        by_d = {k: v for k, v in exp.groupby("department")}
        schema = list(mf.FEATURE_SCHEMA)
        got_rows, exp_rows = [], []
        for _, r in samp.iterrows():
            at = r.assigned_date.to_pydatetime(); L = by_l[r.lecturer_id]
            done = L[(L.completed_date < r.assigned_date) & (L.pos < r.pos)].sort_values(["completed_date", "pos"])   # thứ tự hoàn thành (như CSDL trả về)
            opn = L[(L.pos < r.pos) & ~(L.completed_date < r.assigned_date)]
            hist = [dict(completed_at=c.to_pydatetime(), assigned_at=a_.to_pydatetime(), task_id=tid, is_late=bool(l), delay_days=int(d))
                    for c, a_, tid, l, d in zip(done.completed_date, done.assigned_date, done.task_id, done.is_late, done.delay_days)]
            items = [dict(priority=p, original_deadline=d.date(), effort_hours=float(e)) for p, d, e in zip(opn.priority, opn.original_deadline, opn.estimated_effort_hours)]
            D = by_d[r.department]; D = D[D.completed_date < r.assigned_date]; G = exp[(exp.completed_date < r.assigned_date)]
            same = lambda X: X[X.task_type == r.task_type]
            Ls, Ds, Gs = same(done), same(D), same(G)
            mat = dict(lect_count=len(Ls), lect_late=float(Ls.is_late.sum()), dept_count=len(Ds), dept_late=float(Ds.is_late.sum()),
                       glob_count=len(Gs), glob_late=float(Gs.is_late.sum()))
            task = dict(task_type=r.task_type, task_group=r.task_group, scale=r.task_subtype.rsplit(" - ", 1)[-1], assignment_level=r.assignment_level,
                        assignment_mode=r.assignment_mode, assignment_channel=r.assignment_channel, priority=r.priority, complexity=r.complexity,
                        subtask_count=r.subtask_count, dependency_count=r.dependency_count, team_size=r.team_size,
                        require_external_input=r.require_external_input, require_approval=r.require_approval,
                        original_deadline=r.original_deadline.date(), expected_duration_days=r.expected_duration_days,
                        conversion_hours=None if pd.isna(r.converted_workload) else r.converted_workload)
            lect = dict(academic_rank=r.academic_rank, degree=r.degree, management_role=r.management_role,
                        career_start_date=(r.assigned_date - pd.Timedelta(days=r.years_experience * 365.25)).date(),
                        join_date=(r.assigned_date - pd.Timedelta(days=float(r.tenure_days))).date(), teaching_hours_semester=r.teaching_hours_semester,
                        student_count=r.student_count, supervised_student_count=r.supervised_student_count, department_ml=r.department)
            got_rows.append(mf.build_features(task, lect, at, hist, items, mat, holidays=hol, accreditations=acc))
            exp_rows.append(r)
        G_ = pd.DataFrame(got_rows); E_ = pd.DataFrame(exp_rows).reset_index(drop=True)
        res = []
        for f in schema:
            if f not in E_.columns:
                res.append((f, "n/a", np.nan)); continue   # complexity_num, priority_num: tạo lúc huấn luyện, không nằm trong CSV
            a, b = G_[f], E_[f]
            if pd.api.types.is_numeric_dtype(b) and pd.api.types.is_numeric_dtype(a):
                both_nan = a.isna() & b.isna(); tol = TOL.get(f, 1e-6)
                diff = ((a - b).abs() > (tol * b.abs().clip(lower=1) if f == "deadline_pressure" else tol)) | (a.isna() ^ b.isna())
                diff &= ~both_nan
            else:
                diff = a.astype(str) != b.astype(str)
            res.append((f, int(diff.sum()), float(diff.mean())))
        R = pd.DataFrame(res, columns=["feature", "n_mismatch", "rate"])
        if verbose:
            print(f"Đối chiếu {len(G_)} dòng, {len(schema)} đặc trưng")
            print(R[R.n_mismatch != 0].to_string(index=False) if (R.n_mismatch != 0).any() else "Tất cả khớp")
        return R, G_, E_
    finally:
        if not keep: shutil.rmtree(out, ignore_errors=True)


def test_all_features_match():
    R, *_ = run(verbose=False)
    allowed = {"deadline_month_end": 0.10, "is_urgent_assignment": 0.01}      # lệch có thể giải thích (xem docstring ml_features)
    bad = R[(R.n_mismatch != 0) & (R.apply(lambda x: x.rate > allowed.get(x.feature, 0) if isinstance(x.n_mismatch, int) else False, axis=1))]
    assert bad.empty, "\n" + bad.to_string(index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--rows", type=int, default=800); ap.add_argument("--keep", action="store_true")
    a = ap.parse_args(); run(a.rows, a.keep)
