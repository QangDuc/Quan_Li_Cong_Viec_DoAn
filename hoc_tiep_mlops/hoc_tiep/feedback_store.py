"""Kho phản hồi (SQLite): dự đoán đã đưa ra (kèm đặc trưng LÚC GIAO VIỆC), kết quả thật khi việc hoàn thành, can thiệp của người quản lý.
Quyền riêng tư: chỉ lưu mã (task_id, lecturer_id); đặc trưng không chứa họ tên. Nên dùng mã giả danh và hạn chế quyền đọc file .db."""
import json, sqlite3, zlib
import numpy as np
import pandas as pd

TARGET_COLS = ["is_late", "late_vs_original_deadline", "late_vs_current_deadline", "completed_date"]
SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions(
 task_id TEXT NOT NULL, lecturer_id TEXT NOT NULL, kind TEXT NOT NULL, model_version TEXT NOT NULL,
 predicted_at TEXT NOT NULL, assigned_date TEXT NOT NULL, risk REAL NOT NULL, level TEXT, features BLOB NOT NULL,
 PRIMARY KEY(task_id, lecturer_id, kind));
CREATE TABLE IF NOT EXISTS outcomes(
 task_id TEXT NOT NULL, lecturer_id TEXT NOT NULL, completed_date TEXT NOT NULL, is_late INTEGER NOT NULL,
 recorded_at TEXT NOT NULL, PRIMARY KEY(task_id, lecturer_id));
CREATE TABLE IF NOT EXISTS interventions(
 task_id TEXT NOT NULL, lecturer_id TEXT NOT NULL, intervened_at TEXT NOT NULL, action TEXT);
CREATE INDEX IF NOT EXISTS ix_pred_assigned ON predictions(assigned_date);
CREATE INDEX IF NOT EXISTS ix_out_completed ON outcomes(completed_date);
"""


def _d(x):
    return str(pd.Timestamp(x).date())


def _clean(v):
    if v is None:
        return None
    if isinstance(v, (pd.Timestamp,)):
        return str(v.date())
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if v is pd.NA or v is pd.NaT:
        return None
    return v


def _pack(row):
    return zlib.compress(json.dumps({k: _clean(v) for k, v in row.items()}, ensure_ascii=False).encode("utf-8"), 3)


class FeedbackStore:
    def __init__(self, path=":memory:"):
        self.path = path
        self.con = sqlite3.connect(path)
        self.con.executescript(SCHEMA)

    def close(self):
        self.con.close()

    # ---- ghi ----
    def log_predictions(self, feats, risk, levels, version, kind="static", predicted_at=None):
        """Ghi dự đoán. Chỉ giữ dự đoán ĐẦU TIÊN của mỗi (việc, giảng viên, loại) - đó là điều người quản lý đã thấy. Trả về số dòng mới."""
        need = {"task_id", "lecturer_id", "assigned_date"}
        if not need <= set(feats.columns):
            raise ValueError(f"thiếu cột {need - set(feats.columns)}")
        f = feats.drop(columns=[c for c in TARGET_COLS if c in feats.columns]).reset_index(drop=True)
        risk = np.asarray(risk, float)
        pa = predicted_at if predicted_at is not None else pd.Timestamp.today()
        pa = list(pa) if hasattr(pa, "__len__") and not isinstance(pa, str) else [pa] * len(f)
        rows = [(str(r["task_id"]), str(r["lecturer_id"]), kind, version, _d(pa[i]), _d(r["assigned_date"]), float(risk[i]),
                 None if levels is None else str(levels[i]), _pack(r))
                for i, r in enumerate(f.to_dict("records"))]
        before = self.con.total_changes
        with self.con:
            self.con.executemany("INSERT OR IGNORE INTO predictions VALUES (?,?,?,?,?,?,?,?,?)", rows)
        return self.con.total_changes - before

    def record_outcomes(self, df, recorded_at=None):
        """df: task_id, lecturer_id, completed_date, is_late (0/1). Kết quả là bản ghi cuối: ghi lại sẽ thay thế (sửa nhãn)."""
        ra = pd.Series(recorded_at if recorded_at is not None else pd.Timestamp.today(), index=df.index) if (
            recorded_at is None or isinstance(recorded_at, (str, pd.Timestamp))) else pd.Series(recorded_at).reset_index(drop=True)
        rows = [(str(t), str(l), _d(c), int(y), _d(r)) for t, l, c, y, r in
                zip(df.task_id, df.lecturer_id, df.completed_date, df.is_late, ra)]
        with self.con:
            self.con.executemany("INSERT OR REPLACE INTO outcomes VALUES (?,?,?,?,?)", rows)
        return len(rows)

    def record_intervention(self, task_id, lecturer_id, intervened_at=None, action=""):
        with self.con:
            self.con.execute("INSERT INTO interventions VALUES (?,?,?,?)",
                             (str(task_id), str(lecturer_id), _d(intervened_at or pd.Timestamp.today()), action))

    # ---- đọc ----
    def labeled_frame(self, as_of, kind="static", intervention_policy="exclude"):
        """Các việc đã có kết quả thật TẠI THỜI ĐIỂM as_of (hoàn thành và đã ghi nhận trước as_of). Việc chưa xong KHÔNG có mặt (độ trễ nhãn)."""
        q = """SELECT p.features, p.risk, p.model_version, o.completed_date, o.is_late,
               EXISTS(SELECT 1 FROM interventions i WHERE i.task_id=p.task_id AND i.lecturer_id=p.lecturer_id AND i.intervened_at<?) AS intervened
               FROM predictions p JOIN outcomes o ON o.task_id=p.task_id AND o.lecturer_id=p.lecturer_id
               WHERE p.kind=? AND o.completed_date<? AND o.recorded_at<?"""
        a = _d(as_of)
        cur = self.con.execute(q, (a, kind, a, a))
        recs, meta = [], []
        for fb, risk, ver, cd, y, iv in cur:
            r = json.loads(zlib.decompress(fb).decode("utf-8"))
            recs.append(r)
            meta.append((risk, ver, cd, y, iv))
        if not recs:
            df = pd.DataFrame(columns=["task_id", "lecturer_id", "assigned_date", "completed_date", "is_late", "risk_logged", "model_version_logged", "intervened"])
            df.attrs["n_excluded_intervened"] = 0
            return df
        df = pd.DataFrame(recs)
        m = pd.DataFrame(meta, columns=["risk_logged", "model_version_logged", "completed_date", "is_late", "intervened"])
        df = pd.concat([df, m], axis=1)
        df["assigned_date"] = pd.to_datetime(df["assigned_date"])
        df["completed_date"] = pd.to_datetime(df["completed_date"])
        df["is_late"] = df["is_late"].astype(int)
        n_ex = 0
        if intervention_policy == "exclude":
            n_ex = int(df.intervened.sum())
            df = df[df.intervened == 0].reset_index(drop=True)
        df.attrs["n_excluded_intervened"] = n_ex
        return df

    def stats(self):
        g = lambda q: self.con.execute(q).fetchone()[0]
        return dict(n_predictions=g("SELECT COUNT(*) FROM predictions"), n_outcomes=g("SELECT COUNT(*) FROM outcomes"),
                    n_labeled=g("SELECT COUNT(*) FROM predictions p JOIN outcomes o ON o.task_id=p.task_id AND o.lecturer_id=p.lecturer_id"),
                    n_interventions=g("SELECT COUNT(*) FROM interventions"),
                    versions=dict(self.con.execute("SELECT model_version, COUNT(*) FROM predictions GROUP BY 1").fetchall()))
