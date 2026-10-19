"""Truy vấn CSDL và dựng 58 đặc trưng ML cho một lượt phân công (hoặc xem trước khi giao việc)."""
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.models import (
    Task, TaskAssignment, TaskType, TaskTypeScale, User, LecturerProfile, 
    Department, CalendarEvent, ST_DONE, ST_CANCELLED
)
from app.ml_features import build_features, to_json_safe


def _build_lecturer_and_context(db: Session, lecturer_id: int, task_type_id: int, at: datetime):
    lecturer_user = db.get(User, lecturer_id)
    if not lecturer_user:
        raise ValueError(f"Không tìm thấy giảng viên {lecturer_id}")

    profile = lecturer_user.profile
    dept = lecturer_user.department

    lecturer_dict = {
        "academic_rank": profile.academic_rank if profile else "Giảng viên",
        "degree": profile.degree if profile else "Thạc sĩ",
        "management_role": profile.management_role if profile else "Không",
        "career_start_date": profile.career_start_date if profile else None,
        "join_date": profile.join_date if profile else None,
        "teaching_hours_semester": profile.teaching_hours_semester if profile else None,
        "student_count": profile.student_count if profile else None,
        "supervised_student_count": profile.supervised_student_count if profile else None,
        "department_ml": dept.ml_name if dept else None,
    }

    # 1. Lịch sử hoàn thành của giảng viên
    completed_assignments = (
        db.query(TaskAssignment)
        .filter(
            TaskAssignment.lecturer_id == lecturer_id,
            TaskAssignment.status == ST_DONE,
            TaskAssignment.completed_at.isnot(None)
        )
        .order_by(TaskAssignment.completed_at.asc())
        .all()
    )
    hist_list = [
        {
            "completed_at": a.completed_at,
            "is_late": bool(a.is_late),
            "delay_days": a.delay_days
        }
        for a in completed_assignments
    ]

    # 2. Công việc đang mở của giảng viên
    open_assignments = (
        db.query(TaskAssignment)
        .join(Task)
        .filter(
            TaskAssignment.lecturer_id == lecturer_id,
            TaskAssignment.status != ST_DONE,
            TaskAssignment.status != ST_CANCELLED
        )
        .all()
    )
    open_items = [
        {
            "priority": a.task.priority,
            "original_deadline": a.task.original_deadline,
            "effort_hours": a.task.estimated_effort_hours
        }
        for a in open_assignments
    ]

    late_expr = case((TaskAssignment.is_late == True, 1), else_=0)

    # 3. Ma trận tác vụ - nhân sự (count, late)
    lect_q = (
        db.query(
            func.count(TaskAssignment.id).label("cnt"),
            func.sum(late_expr).label("late_cnt")
        )
        .join(Task)
        .filter(
            TaskAssignment.lecturer_id == lecturer_id,
            Task.task_type_id == task_type_id,
            TaskAssignment.status == ST_DONE
        )
        .first()
    )
    lect_count = int(lect_q.cnt or 0) if lect_q else 0
    lect_late = float(lect_q.late_cnt or 0) if lect_q else 0.0

    dept_count = 0
    dept_late = 0.0
    if dept:
        dept_q = (
            db.query(
                func.count(TaskAssignment.id).label("cnt"),
                func.sum(late_expr).label("late_cnt")
            )
            .join(Task)
            .join(User, TaskAssignment.lecturer_id == User.id)
            .filter(
                User.department_id == dept.id,
                Task.task_type_id == task_type_id,
                TaskAssignment.status == ST_DONE
            )
            .first()
        )
        dept_count = int(dept_q.cnt or 0) if dept_q else 0
        dept_late = float(dept_q.late_cnt or 0) if dept_q else 0.0

    glob_q = (
        db.query(
            func.count(TaskAssignment.id).label("cnt"),
            func.sum(late_expr).label("late_cnt")
        )
        .join(Task)
        .filter(
            Task.task_type_id == task_type_id,
            TaskAssignment.status == ST_DONE
        )
        .first()
    )
    glob_count = int(glob_q.cnt or 0) if glob_q else 0
    glob_late = float(glob_q.late_cnt or 0) if glob_q else 0.0

    mat_dict = {
        "lect_count": lect_count,
        "lect_late": lect_late,
        "dept_count": dept_count,
        "dept_late": dept_late,
        "glob_count": glob_count,
        "glob_late": glob_late
    }

    holidays_raw = db.query(CalendarEvent).filter_by(kind="holiday").all()
    accred_raw = db.query(CalendarEvent).filter_by(kind="accreditation").all()
    holidays = [(h.start_date, h.end_date) for h in holidays_raw]
    accreditations = [(a.start_date, a.end_date) for a in accred_raw]

    return lecturer_dict, hist_list, open_items, mat_dict, holidays, accreditations


def extract_features_for_assignment(db: Session, task_id: int, lecturer_id: int, at: datetime | None = None) -> dict:
    at = at or datetime.now()
    task = db.get(Task, task_id)
    if not task:
        raise ValueError(f"Không tìm thấy công việc {task_id}")

    task_type = db.get(TaskType, task.task_type_id)
    scale_obj = (
        db.query(TaskTypeScale)
        .filter_by(task_type_id=task.task_type_id, scale=task.scale)
        .first()
    )

    expected_duration = scale_obj.expected_duration_days if scale_obj else 7.0
    conversion_hours = scale_obj.conversion_hours if scale_obj else None

    task_dict = {
        "task_group": task_type.task_group,
        "task_type": task_type.name,
        "scale": task.scale,
        "assignment_level": task.assignment_level,
        "assignment_mode": task.assignment_mode,
        "assignment_channel": task.assignment_channel,
        "priority": task.priority,
        "complexity": task.complexity,
        "subtask_count": task.subtask_count,
        "dependency_count": task.dependency_count,
        "team_size": len(task.assignments) if task.assignments else 1,
        "require_external_input": task.require_external_input,
        "require_approval": task.require_approval,
        "original_deadline": task.original_deadline,
        "expected_duration_days": expected_duration,
        "conversion_hours": conversion_hours,
    }

    lecturer_dict, hist_list, open_items, mat_dict, holidays, accreditations = _build_lecturer_and_context(
        db, lecturer_id, task.task_type_id, at
    )

    features = build_features(
        task=task_dict,
        lecturer=lecturer_dict,
        at=at,
        hist=hist_list,
        open_items=open_items,
        mat=mat_dict,
        holidays=holidays,
        accreditations=accreditations
    )
    return to_json_safe(features)


def extract_features_for_preview(
    db: Session,
    task_type_id: int,
    scale: str,
    priority: str,
    complexity: str,
    original_deadline: date,
    lecturer_id: int,
    team_size: int = 1,
    subtask_count: int = 1,
    dependency_count: int = 0,
    require_external_input: bool = False,
    require_approval: bool = False,
    assignment_level: str = "Khoa",
    assignment_channel: str = "Hệ thống",
    at: datetime | None = None
) -> dict:
    at = at or datetime.now()
    task_type = db.get(TaskType, task_type_id)
    if not task_type:
        raise ValueError(f"Không tìm thấy loại công việc {task_type_id}")

    scale_obj = (
        db.query(TaskTypeScale)
        .filter_by(task_type_id=task_type_id, scale=scale)
        .first()
    )
    expected_duration = scale_obj.expected_duration_days if scale_obj else 7.0
    conversion_hours = scale_obj.conversion_hours if scale_obj else None

    task_dict = {
        "task_group": task_type.task_group,
        "task_type": task_type.name,
        "scale": scale,
        "assignment_level": assignment_level,
        "assignment_mode": "Group" if team_size > 1 else "Individual",
        "assignment_channel": assignment_channel,
        "priority": priority,
        "complexity": complexity,
        "subtask_count": subtask_count,
        "dependency_count": dependency_count,
        "team_size": team_size,
        "require_external_input": require_external_input,
        "require_approval": require_approval,
        "original_deadline": original_deadline,
        "expected_duration_days": expected_duration,
        "conversion_hours": conversion_hours,
    }

    lecturer_dict, hist_list, open_items, mat_dict, holidays, accreditations = _build_lecturer_and_context(
        db, lecturer_id, task_type_id, at
    )

    features = build_features(
        task=task_dict,
        lecturer=lecturer_dict,
        at=at,
        hist=hist_list,
        open_items=open_items,
        mat=mat_dict,
        holidays=holidays,
        accreditations=accreditations
    )
    return to_json_safe(features)
