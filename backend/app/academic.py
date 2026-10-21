"""Lịch năm học: tuần, học kỳ, giai đoạn, mùa cao điểm.

Quy tắc tuần -> học kỳ/giai đoạn được SUY RA TỪ NGỮ CẢNH của mô hình (scratch/derive_rules.py, giai đoạn 2):
  HK1 tuần 1–24, HK2 tuần 25–48, Hè 49–53; giai đoạn lấy theo giá trị phổ biến nhất ở mỗi tuần;
  peak_season = 1 khi giai đoạn là final_exam / grade_submission / graduation_project (khớp 100% trong ngữ cảnh).
Ngày bắt đầu tuần 1 cấu hình bằng ACADEMIC_YEAR_START (mặc định 15/08 — [giả định], khớp vị trí Tết/30-4/2-9 trong ngữ cảnh).
"""
from datetime import date, timedelta

from app import config

PEAK_PERIODS = {"final_exam", "grade_submission", "graduation_project"}
_PERIOD_BY_WEEK = {}
for _w0, _w1, _p in [(1, 7, "semester_start"), (8, 11, "normal_teaching"), (12, 15, "midterm"), (16, 22, "final_exam"),
                     (23, 24, "grade_submission"), (25, 30, "semester_start"), (31, 33, "normal_teaching"),
                     (34, 37, "midterm"), (38, 41, "graduation_project"), (42, 46, "final_exam"),
                     (47, 48, "grade_submission"), (49, 53, "summer")]:
    for _w in range(_w0, _w1 + 1):
        _PERIOD_BY_WEEK[_w] = _p
PERIOD_NAMES = {"semester_start": "Đầu học kỳ", "normal_teaching": "Giảng dạy", "midterm": "Giữa kỳ",
                "final_exam": "Thi cuối kỳ", "grade_submission": "Nộp điểm", "graduation_project": "Bảo vệ tốt nghiệp",
                "summer": "Học kỳ hè"}
SEMESTERS = ["HK1", "HK2", "Summer"]


def _start_md():
    m, d = config.ACADEMIC_YEAR_START.split("-")
    return int(m), int(d)


def year_start(d: date) -> date:
    m, dd = _start_md()
    s = date(d.year, m, dd)
    return s if d >= s else date(d.year - 1, m, dd)


def academic_year_label(d: date) -> str:
    s = year_start(d)
    return f"{s.year}-{s.year + 1}"


def academic_week(d: date) -> int:
    return min(53, (d - year_start(d)).days // 7 + 1)


def semester_of_week(w: int) -> str:
    return "HK1" if w <= 24 else ("HK2" if w <= 48 else "Summer")


def semester_of(d: date) -> str:
    w = academic_week(d)
    return "HK1" if w <= 24 else ("HK2" if w <= 48 else "HE")


def period_of_week(w: int) -> str:
    return _PERIOD_BY_WEEK[min(max(w, 1), 53)]



def year_range(label: str):
    """'2026-2027' -> [ngày đầu, ngày đầu năm sau)."""
    y = int(label.split("-")[0])
    m, d = _start_md()
    return date(y, m, d), date(y + 1, m, d)


def semester_range(label: str, semester: str):
    s, e = year_range(label)
    if semester == "HK1":
        return s, s + timedelta(weeks=24)
    if semester == "HK2":
        return s + timedelta(weeks=24), s + timedelta(weeks=48)
    return s + timedelta(weeks=48), e


def overlaps(a0: date, a1: date, b0: date, b1: date) -> bool:
    return a0 <= b1 and b0 <= a1


def calendar_features(assigned: date, deadline: date, holidays, accreditations) -> dict:
    """holidays / accreditations: danh sách (ngày đầu, ngày cuối)."""
    w = academic_week(assigned)
    period = period_of_week(w)
    return dict(
        academic_period=period,
        semester=semester_of_week(w),
        academic_week=w,
        peak_season=int(period in PEAK_PERIODS),
        accreditation_flag=int(any(s <= assigned <= e for s, e in accreditations)),
        holiday_in_window=int(any(overlaps(assigned, deadline, s, e) for s, e in holidays)),
    )
