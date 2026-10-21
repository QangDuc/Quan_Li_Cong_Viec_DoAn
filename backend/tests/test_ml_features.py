"""Kiểm thử tự động các quy tắc nghiệp vụ và bộ dựng đặc trưng ML 58 cột."""
import pytest
from datetime import date, datetime, timedelta
from app.ml_features import (
    build_features, FEATURE_SCHEMA, history_features, load_features, matrix_features
)
from app.academic import (
    academic_week, semester_of_week, period_of_week, academic_year_label
)

def test_feature_schema_completeness():
    assert len(FEATURE_SCHEMA) == 58
    assert "lecturer_task_late_lift" in FEATURE_SCHEMA
    assert "is_cold_start" in FEATURE_SCHEMA
    assert "deadline_pressure" in FEATURE_SCHEMA

def test_academic_calendar_rules():
    d = date(2026, 10, 15)
    week = academic_week(d)
    assert 1 <= week <= 53
    sem = semester_of_week(week)
    assert sem in ["HK1", "HK2", "Summer"]
    period = period_of_week(week)
    assert period in [
        "semester_start", "normal_teaching", "midterm", "final_exam",
        "grade_submission", "graduation_project", "summer"
    ]
    assert academic_year_label(d) == "2026-2027"

def test_matrix_features_fallback():
    # Khi giảng viên chưa từng làm loại việc này (lect_count = 0) -> lùi về bộ môn
    m = matrix_features(
        lect_count=0, lect_late=0.0,
        dept_count=10, dept_late=2.0,
        glob_count=50, glob_late=10.0
    )
    assert m["task_matrix_source"] == "department"
    assert m["lecturer_task_count"] == 0.0
    # Tỉ lệ trễ cá nhân phải bằng tỉ lệ bộ môn khi cold-start (sửa lỗi train/serve skew)
    assert m["lecturer_task_late_rate"] == m["dept_task_late_rate"]
    assert m["lecturer_task_late_lift"] == 0.0

def test_build_58_features():
    task_dict = {
        "task_group": "Giảng dạy",
        "task_type": "Giảng dạy học phần",
        "scale": "quy mô chuẩn",
        "assignment_level": "Khoa",
        "assignment_mode": "Individual",
        "assignment_channel": "Hệ thống",
        "priority": "Cao",
        "complexity": "Trung bình",
        "subtask_count": 5,
        "dependency_count": 1,
        "team_size": 1,
        "require_external_input": False,
        "require_approval": True,
        "original_deadline": date(2026, 11, 15),
        "expected_duration_days": 30.0,
        "conversion_hours": 44.0,
    }
    lecturer_dict = {
        "academic_rank": "Giảng viên",
        "degree": "Thạc sĩ",
        "management_role": "Không",
        "career_start_date": date(2018, 9, 1),
        "join_date": date(2020, 2, 1),
        "teaching_hours_semester": 180.0,
        "student_count": 200,
        "supervised_student_count": 3,
        "department_ml": "K01 - Công nghệ phần mềm",
    }
    mat_dict = {
        "lect_count": 5, "lect_late": 1.0,
        "dept_count": 20, "dept_late": 4.0,
        "glob_count": 100, "glob_late": 20.0
    }
    at = datetime(2026, 10, 15, 8, 0, 0)
    features = build_features(
        task=task_dict,
        lecturer=lecturer_dict,
        at=at,
        hist=[],
        open_items=[],
        mat=mat_dict
    )
    assert len(features) == 58
    assert features["is_cold_start"] == 1  # vì hist trống
    assert features["task_type"] == "Giảng dạy học phần"
    assert features["priority_num"] == 2  # Cao -> 2
    assert features["complexity_num"] == 1 # Trung bình -> 1
