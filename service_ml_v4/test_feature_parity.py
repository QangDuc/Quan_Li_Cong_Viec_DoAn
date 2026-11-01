"""Kiểm tra TƯƠNG ĐƯƠNG giữa đặc trưng dịch vụ (app/ml_features.py, app/academic.py) và định nghĩa của bộ sinh dữ liệu huấn luyện.
Chạy:  cd service && python test_feature_parity.py   (cần training_scripts/ ở thư mục cha; không cần backend)"""
import os, sys, datetime as dt
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here); sys.path.insert(0, os.path.join(here, "..", "training_scripts"))
import pandas as pd
import gen_synthetic_data_v5 as g
from app import academic as ac
from app import ml_features as mf


def test_calendar_matches_generator():
    bad = []
    for i in range(365 * 4):
        d = dt.date(2025, 8, 15) + dt.timedelta(days=i); ts = pd.Timestamp(d)
        f = ac.calendar_features(d, d + dt.timedelta(days=3), [], [])
        exp = (g.academic_period(ts), g.semester(ts), int((ts - g.ay_start(ts)).days // 7 + 1),
               int(g.academic_period(ts) in (g.FE, g.GP, g.GS)))
        got = (f["academic_period"], f["semester"], f["academic_week"], f["peak_season"])
        if exp != got: bad.append((str(d), exp, got))
    assert not bad, bad[:5]


def test_workload_includes_overdue_like_generator():
    today = dt.date(2026, 3, 2)
    items = [dict(priority="Cao", original_deadline=today - dt.timedelta(days=3), effort_hours=20),
             dict(priority="Thấp", original_deadline=today + dt.timedelta(days=5), effort_hours=10),
             dict(priority="Thấp", original_deadline=today + dt.timedelta(days=30), effort_hours=99)]
    f = mf.load_features(items, today)
    assert f["workload_next_14d"] == 30.0 and f["deadlines_next_14d"] == 1.0 and f["overdue_open_tasks"] == 1.0


def test_month_end_is_last_business_day():
    # bộ sinh: hạn dồn cuối tháng = ngày cuối tháng, lùi về thứ Sáu nếu rơi cuối tuần
    for y in (2026, 2027):
        for m in range(1, 13):
            cand = pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0)
            while cand.dayofweek >= 5: cand -= pd.Timedelta(days=1)
            assert mf.deadline_month_end(cand.date()) == 1, cand
            assert mf.deadline_month_end((cand - pd.Timedelta(days=7)).date()) == 0


if __name__ == "__main__":
    for n, fn in list(globals().items()):
        if n.startswith("test_"): fn(); print("ĐẠT", n)
