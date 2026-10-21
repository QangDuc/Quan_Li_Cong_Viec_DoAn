"""
DỰNG 58 ĐẶC TRƯNG CHO MÔ HÌNH RỦI RO TRỄ HẠN (thuần Python, không truy cập CSDL -> kiểm thử đơn vị được).

Bám theo đúng quy trình lúc huấn luyện:
  * clean_data.py      : giới hạn đuôi (deadline_pressure 5, workload_next_14d 500, active_tasks 20, active_high_priority_tasks 15),
                         cờ *_missing, is_cold_start = (hist_count == 0)
  * enrich_temporal()  : lecturer_task_* làm mịn Laplace (prior 0.2, độ mạnh 3); CHƯA làm loại việc -> lấy tỉ lệ Bộ môn,
                         chưa có Bộ môn -> toàn cục, chưa có gì -> 0.2  (sửa lệch train/serve: bản --inference cũ gán 0.2)
  * train_model.engineer(): complexity_num, priority_num
  * hist_late_rate làm mịn (prior 0.2, độ mạnh 3) — suy ra từ ngữ cảnh: hist_count=1 -> {0.15, 0.40}
  * hist_avg_delay = số ngày trễ TB của các lần trễ (0 nếu chưa trễ lần nào, thiếu nếu chưa có lịch sử) — khớp ngữ cảnh
Khác biệt CÓ CHỦ Ý so với lúc huấn luyện: lịch sử chỉ gồm việc ĐÃ HOÀN THÀNH TRƯỚC thời điểm giao (completed_at < at)
— đúng điều kiện triển khai; enrich_temporal lúc huấn luyện tính cả việc giao trước nhưng chưa xong (xem báo cáo, điểm 2).
"""
import calendar as _cal
import math
from datetime import date, datetime, timedelta

from app.academic import calendar_features

PRIOR_RATE = 0.20
PRIOR_STRENGTH = 3.0
HIST_STRENGTH = 3.0
CAPS = {"deadline_pressure": 5.0, "workload_next_14d": 500.0, "active_tasks": 20, "active_high_priority_tasks": 15}
HIGH_PRIORITIES = {"Cao", "Khẩn cấp"}
COMPLEXITY_NUM = {"Thấp": 0, "Trung bình": 1, "Cao": 2}
PRIORITY_NUM = {"Thấp": 0, "Trung bình": 1, "Cao": 2, "Khẩn cấp": 3}
NAN = float("nan")

# đúng thứ tự meta.feature_schema trong model/metrics.json (kiểm tra bằng tests/test_ml_features.py)
FEATURE_SCHEMA = [
    "task_group", "task_type", "task_subtype", "assignment_level", "assignment_mode", "assignment_channel", "priority",
    "complexity", "subtask_count", "dependency_count", "team_size", "is_urgent_assignment", "require_external_input",
    "require_approval", "available_days", "holiday_in_window", "expected_duration_days", "deadline_pressure",
    "converted_workload", "academic_period", "semester", "academic_week", "peak_season", "accreditation_flag",
    "academic_rank", "degree", "years_experience", "tenure_days", "management_role", "department",
    "teaching_hours_semester", "student_count", "supervised_student_count", "hist_count", "hist_late_rate",
    "hist_avg_delay", "hist_early_rate", "active_tasks", "active_high_priority_tasks", "overdue_open_tasks",
    "deadlines_next_7d", "deadlines_next_14d", "workload_next_14d", "hist_late_last5", "late_last_30d",
    "deadline_month_end", "converted_workload_missing", "hist_avg_delay_missing", "hist_early_rate_missing",
    "hist_late_last5_missing", "is_cold_start", "lecturer_task_count", "lecturer_task_late_rate",
    "dept_task_late_rate", "task_matrix_source", "lecturer_task_late_lift", "complexity_num", "priority_num",
]


def smooth(late, count, prior=PRIOR_RATE, strength=PRIOR_STRENGTH):
    return (late + prior * strength) / (count + strength)


def _isnan(v):
    return v is None or (isinstance(v, float) and math.isnan(v))


def _num(v):
    return NAN if v is None else float(v)


def matrix_features(lect_count, lect_late, dept_count, dept_late, glob_count, glob_late):
    """Đặc trưng ma trận tác vụ–nhân sự cho (giảng viên, loại việc) — cùng thứ tự lùi như enrich_temporal."""
    if dept_count > 0:
        dept_rate = smooth(dept_late, dept_count)
    elif glob_count > 0:
        dept_rate = smooth(glob_late, glob_count)
    else:
        dept_rate = PRIOR_RATE
    if lect_count > 0:
        rate, src, cnt = smooth(lect_late, lect_count), "personal", lect_count
    elif dept_count > 0:
        rate, src, cnt = smooth(dept_late, dept_count), "department", 0
    elif glob_count > 0:
        rate, src, cnt = smooth(glob_late, glob_count), "global", 0
    else:
        rate, src, cnt = PRIOR_RATE, "global", 0
    return dict(lecturer_task_count=float(cnt), lecturer_task_late_rate=rate, dept_task_late_rate=dept_rate,
                task_matrix_source=src, lecturer_task_late_lift=rate - dept_rate)


def history_features(hist, at: datetime):
    """hist: các việc ĐÃ HOÀN THÀNH trước `at`, mỗi phần tử dict(completed_at, is_late, delay_days), sắp tăng theo completed_at."""
    n = len(hist)
    if n == 0:
        return dict(hist_count=0.0, hist_late_rate=PRIOR_RATE, hist_avg_delay=NAN, hist_early_rate=NAN,
                    hist_late_last5=NAN, late_last_30d=0.0)
    lates = [h for h in hist if h["is_late"]]
    last5 = hist[-5:]
    since = at - timedelta(days=30)
    return dict(
        hist_count=float(n),
        hist_late_rate=smooth(len(lates), n, strength=HIST_STRENGTH),
        hist_avg_delay=(sum(h["delay_days"] or 0 for h in lates) / len(lates)) if lates else 0.0,
        hist_early_rate=sum(1 for h in hist if (h["delay_days"] is not None and h["delay_days"] <= -2)) / n,
        hist_late_last5=sum(1 for h in last5 if h["is_late"]) / len(last5),
        late_last_30d=float(sum(1 for h in lates if h["completed_at"] > since)),
    )


def load_features(open_items, today: date):
    """open_items: việc đang mở của GV lúc giao, mỗi phần tử dict(priority, original_deadline, effort_hours)."""
    due7 = [o for o in open_items if today <= o["original_deadline"] <= today + timedelta(days=7)]
    due14 = [o for o in open_items if today <= o["original_deadline"] <= today + timedelta(days=14)]
    return dict(
        active_tasks=float(min(len(open_items), CAPS["active_tasks"])),
        active_high_priority_tasks=float(min(sum(1 for o in open_items if o["priority"] in HIGH_PRIORITIES),
                                             CAPS["active_high_priority_tasks"])),
        overdue_open_tasks=float(sum(1 for o in open_items if o["original_deadline"] < today)),
        deadlines_next_7d=float(len(due7)),
        deadlines_next_14d=float(len(due14)),
        workload_next_14d=float(min(sum(o["effort_hours"] or 0 for o in due14), CAPS["workload_next_14d"])),
    )


def deadline_month_end(d: date) -> int:
    """[giả định] hạn rơi vào 4 ngày cuối tháng (tỉ lệ 4/30 ≈ 0,13 gần với 0,14 trong ngữ cảnh)."""
    return int(d.day > _cal.monthrange(d.year, d.month)[1] - 4)


def build_features(task: dict, lecturer: dict, at: datetime, hist: list, open_items: list, mat: dict,
                   holidays=(), accreditations=()) -> dict:
    """Trả về dict đủ 58 đặc trưng (đúng tên trong FEATURE_SCHEMA). Giá trị thiếu = NaN.
    task     : task_type, task_group, scale, assignment_level, assignment_mode, assignment_channel, priority, complexity,
               subtask_count, dependency_count, team_size, require_external_input, require_approval, original_deadline,
               expected_duration_days, conversion_hours
    lecturer : academic_rank, degree, management_role, career_start_date, join_date, teaching_hours_semester,
               student_count, supervised_student_count, department_ml
    mat      : lect_count, lect_late, dept_count, dept_late, glob_count, glob_late (cùng loại việc, việc đã hoàn thành trước at)"""
    today = at.date()
    deadline = task["original_deadline"]
    available = (deadline - today).days
    if available < 1:
        raise ValueError("Hạn hoàn thành phải sau ngày giao ít nhất 1 ngày")
    expected = float(task["expected_duration_days"])
    pressure = min(expected / available, CAPS["deadline_pressure"])
    conv = task.get("conversion_hours")
    f = dict(
        task_group=task["task_group"],
        task_type=task["task_type"],
        task_subtype=f"{task['task_type']} - {task['scale']}",
        assignment_level=task["assignment_level"],
        assignment_mode=task["assignment_mode"],
        assignment_channel=task.get("assignment_channel") or "Hệ thống",
        priority=task["priority"],
        complexity=task["complexity"],
        subtask_count=float(task["subtask_count"]),
        dependency_count=float(task["dependency_count"]),
        team_size=float(task["team_size"]),
        is_urgent_assignment=int(pressure > 1.25),
        require_external_input=int(bool(task["require_external_input"])),
        require_approval=int(bool(task["require_approval"])),
        available_days=float(available),
        expected_duration_days=expected,
        deadline_pressure=pressure,
        converted_workload=_num(conv),
        academic_rank=lecturer.get("academic_rank"),
        degree=lecturer.get("degree"),
        years_experience=round((today - lecturer["career_start_date"]).days / 365.25, 1) if lecturer.get("career_start_date") else NAN,
        tenure_days=float((today - lecturer["join_date"]).days) if lecturer.get("join_date") else NAN,
        management_role=lecturer.get("management_role"),
        department=lecturer.get("department_ml"),
        teaching_hours_semester=_num(lecturer.get("teaching_hours_semester")),
        student_count=_num(lecturer.get("student_count")),
        supervised_student_count=_num(lecturer.get("supervised_student_count")),
        deadline_month_end=deadline_month_end(deadline),
    )
    f.update(calendar_features(today, deadline, holidays, accreditations))
    f.update(history_features(hist, at))
    f.update(load_features(open_items, today))
    f.update(matrix_features(**mat))
    f["converted_workload_missing"] = int(_isnan(f["converted_workload"]))
    f["hist_avg_delay_missing"] = int(_isnan(f["hist_avg_delay"]))
    f["hist_early_rate_missing"] = int(_isnan(f["hist_early_rate"]))
    f["hist_late_last5_missing"] = int(_isnan(f["hist_late_last5"]))
    f["is_cold_start"] = int(f["hist_count"] == 0)
    f["complexity_num"] = COMPLEXITY_NUM.get(f["complexity"], NAN)
    f["priority_num"] = PRIORITY_NUM.get(f["priority"], NAN)
    return {k: f[k] for k in FEATURE_SCHEMA}


def to_json_safe(features: dict) -> dict:
    """NaN -> None để gửi JSON."""
    return {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in features.items()}
