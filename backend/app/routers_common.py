"""API Router: Thông báo, Quét nhắc hạn tự động (FR-02, FR-03), Lịch năm học & Danh mục tra cứu."""
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db import get_db
from app.models import (
    Notification, Department, TaskType, CalendarEvent, User,
    Task, TaskAssignment, ST_DONE, ST_CANCELLED
)
from app.deps import current_user

router = APIRouter(prefix="/api/common", tags=["Common"])

@router.get("/notifications")
def get_notifications(unread_only: bool = False, db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = db.query(Notification).filter_by(user_id=user.id)
    if unread_only:
        q = q.filter_by(is_read=False)
    return q.order_by(desc(Notification.created_at)).limit(50).all()

@router.put("/notifications/read-all")
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.query(Notification).filter_by(user_id=user.id, is_read=False).update({"is_read": True})
    db.commit()
    return {"message": "Đã đánh dấu tất cả thông báo là đã đọc"}

@router.put("/notifications/{notif_id}/read")
def mark_read(notif_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    n = db.query(Notification).filter_by(id=notif_id, user_id=user.id).first()
    if n:
        n.is_read = True
        db.commit()
    return {"message": "Đã đánh dấu đã đọc"}

@router.post("/notifications/scan-deadlines")
def scan_deadlines(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Quét tự động các công việc sắp đến hạn (<= 3 ngày) và quá hạn để tạo thông báo nhắc nhở (FR-02, FR-03)."""
    today = date.today()
    open_assigns = (
        db.query(TaskAssignment)
        .join(Task)
        .filter(TaskAssignment.status != ST_DONE, TaskAssignment.status != ST_CANCELLED)
        .all()
    )
    created = 0
    for a in open_assigns:
        days_left = (a.task.current_deadline - today).days
        if days_left < 0:
            dedupe = f"overdue:{a.task_id}:{a.lecturer_id}:{today.isoformat()}"
            if not db.query(Notification).filter_by(dedupe_key=dedupe).first():
                db.add(Notification(
                    user_id=a.lecturer_id,
                    kind="overdue",
                    title=f"Quá hạn ({abs(days_left)} ngày): {a.task.title}",
                    content=f"Công việc '{a.task.title}' (Mã {a.task.code}) đã quá hạn chót {a.task.current_deadline}. Vui lòng cập nhật tiến độ hoặc gửi yêu cầu gia hạn.",
                    task_id=a.task_id,
                    dedupe_key=dedupe
                ))
                created += 1
        elif 0 <= days_left <= 3:
            dedupe = f"due_soon:{a.task_id}:{a.lecturer_id}:{today.isoformat()}"
            if not db.query(Notification).filter_by(dedupe_key=dedupe).first():
                db.add(Notification(
                    user_id=a.lecturer_id,
                    kind="due_soon",
                    title=f"Sắp đến hạn (còn {days_left} ngày): {a.task.title}",
                    content=f"Công việc '{a.task.title}' (Mã {a.task.code}) sẽ đến hạn vào {a.task.current_deadline}. Tiến độ hiện tại: {a.progress_pct}%.",
                    task_id=a.task_id,
                    dedupe_key=dedupe
                ))
                created += 1
    db.commit()
    return {"message": f"Đã quét nhắc hạn công việc: tạo mới {created} thông báo", "created": created}

@router.get("/departments")
def get_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()

@router.get("/task-types")
def get_task_types(db: Session = Depends(get_db)):
    types = db.query(TaskType).filter_by(is_active=True).all()
    res = []
    for t in types:
        res.append({
            "id": t.id,
            "name": t.name,
            "task_group": t.task_group,
            "default_complexity": t.default_complexity,
            "default_subtask_count": t.default_subtask_count,
            "default_dependency_count": t.default_dependency_count,
            "scales": [
                {
                    "scale": s.scale,
                    "expected_duration_days": s.expected_duration_days,
                    "conversion_hours": s.conversion_hours
                }
                for s in t.scales
            ]
        })
    return res

from pydantic import BaseModel
from typing import List
from app.models import TaskTypeScale
from app.deps import manager_or_admin


class ScaleUpdateItem(BaseModel):
    scale: str
    conversion_hours: float
    expected_duration_days: float


class TaskTypeScalesUpdateRequest(BaseModel):
    scales: List[ScaleUpdateItem]


@router.put("/task-types/{task_type_id}/scales", dependencies=[Depends(manager_or_admin)])
def update_task_type_scales(
    task_type_id: int,
    req: TaskTypeScalesUpdateRequest,
    db: Session = Depends(get_db)
):
    """Cập nhật định mức giờ chuẩn quy đổi và số ngày dự kiến thực hiện cho một loại công việc (FR-09)."""
    tt = db.get(TaskType, task_type_id)
    if not tt:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Không tìm thấy loại công việc")

    existing = {s.scale: s for s in tt.scales}
    for item in req.scales:
        if item.scale in existing:
            existing[item.scale].conversion_hours = round(float(item.conversion_hours), 2)
            existing[item.scale].expected_duration_days = round(float(item.expected_duration_days), 1)
        else:
            db.add(TaskTypeScale(
                task_type_id=tt.id,
                scale=item.scale,
                conversion_hours=round(float(item.conversion_hours), 2),
                expected_duration_days=round(float(item.expected_duration_days), 1)
            ))
    db.commit()
    return {"message": f"Đã cập nhật định mức giờ chuẩn cho '{tt.name}'"}


@router.get("/calendar-events")
def get_calendar_events(db: Session = Depends(get_db)):
    return db.query(CalendarEvent).all()
