"""API Router: Nghiệp vụ công việc, tiến độ, gia hạn, thông báo, ML risk (FR-01, FR-02, FR-04, FR-08, FR-10)."""
import uuid
import json
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db import get_db
from app.models import (
    Task, TaskAssignment, TaskType, TaskTypeScale, User, ProgressUpdate,
    ExtensionRequest, Notification, RiskPrediction, ST_NEW, ST_DOING, ST_DONE,
    EXT_PENDING, EXT_APPROVED, EXT_REJECTED, ROLE_MANAGER, ROLE_ADMIN, ROLE_LECTURER
)
from app.deps import current_user, manager_or_admin, lecturer_scope, can_see_lecturer, can_see_risk
from app.schemas import TaskCreate, TaskRiskPreviewRequest, ProgressUpdateCreate, ExtensionCreate, ExtensionReview
from app.ml_client import predict_and_record_risk, preview_risk_for_features
from app.ml_extract import extract_features_for_preview

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

@router.get("")
def list_tasks(
    status_filter: str | None = None,
    academic_year: str | None = None,
    lecturer_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    query = db.query(Task)
    scope = lecturer_scope(db, user)

    if scope is not None:
        query = query.join(TaskAssignment).filter(TaskAssignment.lecturer_id.in_(scope))
    elif lecturer_id is not None:
        query = query.join(TaskAssignment).filter(TaskAssignment.lecturer_id == lecturer_id)

    if status_filter:
        query = query.filter(Task.status == status_filter)

    scales = {
        (tts.task_type_id, tts.scale): (tts.conversion_hours or 0.0)
        for tts in db.query(TaskTypeScale).all()
    }

    tasks = query.order_by(desc(Task.assigned_at), desc(Task.id)).all()
    res = []
    seen_ids = set()
    for t in tasks:
        if t.id in seen_ids:
            continue
        seen_ids.add(t.id)

        assignees = []
        for a in t.assignments:
            ml_info = None
            if can_see_risk(db, user, a.lecturer_id):
                pred = (
                    db.query(RiskPrediction)
                    .filter_by(assignment_id=a.id)
                    .order_by(desc(RiskPrediction.id))
                    .first()
                )
                if pred:
                    ml_info = {
                        "id": pred.id,
                        "status": pred.status,
                        "probability": pred.probability,
                        "level": pred.level,
                        "uncertainty": pred.uncertainty,
                        "top_factors": json.loads(pred.top_factors) if pred.top_factors else [],
                        "recommendation": pred.recommendation,
                        "notes": pred.notes,
                        "low_confidence": pred.low_confidence,
                        "actual_is_late": pred.actual_is_late
                    }

            assignees.append({
                "assignment_id": a.id,
                "lecturer_id": a.lecturer_id,
                "lecturer_name": a.lecturer.full_name,
                "lecturer_code": a.lecturer.profile.lecturer_code if a.lecturer.profile else "",
                "department_name": a.lecturer.department.name if a.lecturer.department else "",
                "progress_pct": a.progress_pct,
                "status": a.status,
                "is_late": a.is_late,
                "delay_days": a.delay_days,
                "completed_at": a.completed_at,
                "ml_prediction": ml_info
            })

        conv_hours = (
            t.school_item.conversion_hours
            if t.school_item
            else scales.get((t.task_type_id, t.scale), 0.0)
        )

        res.append({
            "id": t.id,
            "code": t.code,
            "title": t.title,
            "description": t.description,
            "task_type_id": t.task_type_id,
            "task_type_name": t.task_type.name,
            "task_group": t.task_type.task_group,
            "scale": t.scale,
            "school_catalog_id": t.school_catalog_id,
            "school_catalog_code": t.school_item.code if t.school_item else None,
            "school_catalog_name": t.school_item.name if t.school_item else None,
            "conversion_hours": round(conv_hours, 2),
            "priority": t.priority,
            "complexity": t.complexity,
            "assignment_mode": t.assignment_mode,
            "assignment_level": t.assignment_level,
            "status": t.status,
            "assigned_at": t.assigned_at,
            "original_deadline": t.original_deadline,
            "current_deadline": t.current_deadline,
            "creator_name": t.creator.full_name if t.creator else "Hệ thống",
            "extension_count": len(t.extensions),
            "pending_extensions": sum(1 for e in t.extensions if e.status == EXT_PENDING),
            "assignees": assignees
        })
    return res


@router.post("/preview-risk", dependencies=[Depends(manager_or_admin)])
def preview_task_risk(
    req: TaskRiskPreviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    """
    Xem trước dự đoán rủi ro trễ hạn ML và xếp hạng giảng viên phù hợp trước khi giao việc (FR-10, UC-01 Bước 4-6).
    """
    if req.original_deadline <= date.today():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Thời hạn hoàn thành phải sau ngày giao ít nhất 1 ngày")

    if req.lecturer_ids and len(req.lecturer_ids) > 0:
        lecturers = db.query(User).filter(User.id.in_(req.lecturer_ids), User.is_active == True).all()
    else:
        q = db.query(User).filter(User.role == ROLE_LECTURER, User.is_active == True)
        if user.role == ROLE_MANAGER and user.department_id is not None:
            q = q.filter(User.department_id == user.department_id)
        lecturers = q.all()

    team_size = len(req.lecturer_ids) if req.lecturer_ids and len(req.lecturer_ids) > 1 else 1
    candidates = []
    for lec in lecturers:
        feats = extract_features_for_preview(
            db=db,
            task_type_id=req.task_type_id,
            scale=req.scale or "quy mô chuẩn",
            priority=req.priority or "Trung bình",
            complexity=req.complexity or "Trung bình",
            original_deadline=req.original_deadline,
            lecturer_id=lec.id,
            team_size=team_size,
            subtask_count=req.subtask_count or 1,
            dependency_count=req.dependency_count or 0,
            require_external_input=req.require_external_input or False,
            require_approval=req.require_approval or False,
            assignment_level=req.assignment_level or "Khoa",
            assignment_channel=req.assignment_channel or "Hệ thống"
        )
        pred = preview_risk_for_features(feats)
        candidates.append({
            "lecturer_id": lec.id,
            "full_name": lec.full_name,
            "lecturer_code": lec.profile.lecturer_code if lec.profile else f"GV{lec.id:04d}",
            "department_name": lec.department.name if lec.department else "",
            "academic_rank": lec.profile.academic_rank if lec.profile else "Giảng viên",
            "degree": lec.profile.degree if lec.profile else "Thạc sĩ",
            "teaching_hours_semester": lec.profile.teaching_hours_semester if lec.profile else 0.0,
            "current_open_tasks": int(feats.get("active_tasks") or 0),
            "current_overdue_tasks": int(feats.get("overdue_open_tasks") or 0),
            "hist_completed_count": int(feats.get("hist_count") or 0),
            "hist_late_rate": round(float(feats.get("hist_late_rate") or 0.0) * 100, 1),
            "mat_type_count": int(feats.get("lecturer_task_count") or 0),
            "mat_type_late_rate": round(float(feats.get("lecturer_task_late_rate") or 0.0) * 100, 1),
            "lead_time_days": int(feats.get("available_days") or 0),
            "expected_duration_days": round(float(feats.get("expected_duration_days") or 7.0), 1),
            "lead_vs_expected_ratio": round(float(feats.get("deadline_pressure") or 1.0), 2),
            "status": pred.get("status", "ok"),
            "probability": pred.get("probability"),
            "level": pred.get("level"),
            "uncertainty": pred.get("uncertainty"),
            "top_factors": pred.get("top_factors", []),
            "recommendation": pred.get("recommendation"),
            "low_confidence": pred.get("low_confidence", False),
            "latency_ms": pred.get("latency_ms", 0)
        })

    # Xếp hạng giảng viên từ xác suất rủi ro thấp nhất -> cao nhất (tối ưu phân công)
    candidates.sort(key=lambda c: (c["probability"] if c["probability"] is not None else 9.9, c["current_open_tasks"]))
    for idx, c in enumerate(candidates):
        c["rank"] = idx + 1

    return {
        "candidates": candidates,
        "thresholds": {"low": 0.22, "high": 0.44},
        "evaluated_at": datetime.now()
    }


@router.get("/extensions")
def list_extensions(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    """Danh sách yêu cầu gia hạn công việc (FR-08, UC-03)."""
    query = db.query(ExtensionRequest).join(Task)
    if user.role == ROLE_LECTURER:
        query = query.filter(ExtensionRequest.requested_by == user.id)
    elif user.role == ROLE_MANAGER and user.department_id is not None:
        scope = lecturer_scope(db, user)
        if scope is not None:
            query = query.filter(ExtensionRequest.requested_by.in_(scope))

    if status_filter:
        query = query.filter(ExtensionRequest.status == status_filter)

    exts = query.order_by(desc(ExtensionRequest.created_at)).all()
    res = []

    for e in exts:
        requester = db.get(User, e.requested_by)
        reviewer = db.get(User, e.reviewed_by) if e.reviewed_by else None
        assign = db.query(TaskAssignment).filter_by(task_id=e.task_id, lecturer_id=e.requested_by).first()
        ml_info = None
        if assign and can_see_risk(db, user, e.requested_by):
            pred = (
                db.query(RiskPrediction)
                .filter_by(assignment_id=assign.id)
                .order_by(desc(RiskPrediction.id))
                .first()
            )
            if pred:
                ml_info = {
                    "probability": pred.probability,
                    "level": pred.level,
                    "uncertainty": pred.uncertainty,
                    "recommendation": pred.recommendation
                }

        res.append({
            "id": e.id,
            "task_id": e.task_id,
            "task_code": e.task.code,
            "task_title": e.task.title,
            "task_priority": e.task.priority,
            "requested_by": e.requested_by,
            "requester_name": requester.full_name if requester else "",
            "department_name": requester.department.name if requester and requester.department else "",
            "progress_pct": assign.progress_pct if assign else 0,
            "reason": e.reason,
            "old_deadline": e.old_deadline,
            "proposed_deadline": e.proposed_deadline,
            "extra_days": (e.proposed_deadline - e.old_deadline).days,
            "status": e.status,
            "requested_at": e.requested_at,
            "reviewed_by_name": reviewer.full_name if reviewer else None,
            "reviewed_at": e.reviewed_at,
            "review_note": e.review_note,
            "ml_prediction": ml_info
        })
    return res


@router.get("/{task_id}/detail")
def get_task_detail(task_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Lấy chi tiết công việc kèm nhật ký tiến độ, lịch sử gia hạn và lịch sử dự đoán ML."""
    t = db.get(Task, task_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy công việc")

    progress_logs = []
    for a in t.assignments:
        for p in a.progress_updates:
            u = db.get(User, p.created_by) if p.created_by else None
            progress_logs.append({
                "id": p.id,
                "lecturer_name": a.lecturer.full_name,
                "progress_pct": p.progress_pct,
                "note": p.note,
                "created_by_name": u.full_name if u else a.lecturer.full_name,
                "created_at": p.created_at
            })
    progress_logs.sort(key=lambda x: x["created_at"], reverse=True)

    ext_logs = []
    for e in t.extensions:
        req_u = db.get(User, e.requested_by)
        rev_u = db.get(User, e.reviewed_by) if e.reviewed_by else None
        ext_logs.append({
            "id": e.id,
            "requester_name": req_u.full_name if req_u else "",
            "reason": e.reason,
            "old_deadline": e.old_deadline,
            "proposed_deadline": e.proposed_deadline,
            "status": e.status,
            "requested_at": e.requested_at,
            "reviewer_name": rev_u.full_name if rev_u else None,
            "reviewed_at": e.reviewed_at,
            "review_note": e.review_note
        })

    return {
        "id": t.id,
        "code": t.code,
        "title": t.title,
        "description": t.description,
        "task_type_name": t.task_type.name,
        "task_group": t.task_type.task_group,
        "scale": t.scale,
        "priority": t.priority,
        "complexity": t.complexity,
        "assigned_at": t.assigned_at,
        "original_deadline": t.original_deadline,
        "current_deadline": t.current_deadline,
        "status": t.status,
        "school_catalog_name": t.school_item.name if t.school_item else None,
        "progress_logs": progress_logs,
        "extensions": ext_logs
    }


@router.post("", dependencies=[Depends(manager_or_admin)])
def create_task(req: TaskCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Giao việc mới (FR-01, FR-02) + Gọi dự đoán rủi ro ML (FR-10)."""
    if req.original_deadline <= date.today():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Thời hạn hoàn thành phải sau ngày giao ít nhất 1 ngày")

    code = f"CV-{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    task = Task(
        code=code,
        title=req.title,
        description=req.description,
        task_type_id=req.task_type_id,
        scale=req.scale or "quy mô chuẩn",
        school_catalog_id=req.school_catalog_id,
        priority=req.priority or "Trung bình",
        complexity=req.complexity or "Trung bình",
        assignment_mode="Group" if len(req.lecturer_ids) > 1 else "Individual",
        assignment_level=req.assignment_level or "Khoa",
        assignment_channel=req.assignment_channel or "Hệ thống",
        subtask_count=req.subtask_count or 1,
        dependency_count=req.dependency_count or 0,
        require_external_input=req.require_external_input or False,
        require_approval=req.require_approval or False,
        estimated_effort_hours=req.estimated_effort_hours,
        assigned_at=datetime.now(),
        original_deadline=req.original_deadline,
        current_deadline=req.original_deadline,
        status=ST_NEW,
        created_by=user.id,
        plan_id=req.plan_id
    )
    db.add(task)
    db.flush()

    predictions_summary = []
    for lid in req.lecturer_ids:
        assign = TaskAssignment(
            task_id=task.id,
            lecturer_id=lid,
            progress_pct=0,
            status=ST_NEW
        )
        db.add(assign)
        db.flush()

        notif = Notification(
            user_id=lid,
            kind="new_task",
            title=f"Công việc mới: {task.title}",
            content=f"Bạn được giao công việc '{task.title}' với mức ưu tiên {task.priority}. Hạn chót: {task.current_deadline}.",
            task_id=task.id,
            dedupe_key=f"new_task:{task.id}:{lid}"
        )
        db.add(notif)

        pred = predict_and_record_risk(db, task.id, assign.id, lid, trigger="assign")
        predictions_summary.append({
            "lecturer_id": lid,
            "status": pred.status,
            "probability": pred.probability,
            "level": pred.level,
            "uncertainty": pred.uncertainty,
            "top_factors": json.loads(pred.top_factors) if pred.top_factors else [],
            "recommendation": pred.recommendation,
            "notes": pred.notes,
            "low_confidence": pred.low_confidence
        })

    db.commit()
    return {
        "message": "Giao việc thành công",
        "task_id": task.id,
        "code": task.code,
        "predictions": predictions_summary
    }


@router.post("/{task_id}/progress")
def update_progress(
    task_id: int,
    req: ProgressUpdateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    """Cập nhật tiến độ hoàn thành theo % (FR-04)."""
    assign = db.query(TaskAssignment).filter_by(task_id=task_id, lecturer_id=user.id).first()
    if not assign and user.role not in (ROLE_MANAGER, ROLE_ADMIN):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bạn không phụ trách công việc này")

    if not assign:
        assign = db.query(TaskAssignment).filter_by(task_id=task_id).first()
        if not assign:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy phân công")

    assign.progress_pct = req.progress_pct
    if assign.progress_pct > 0 and assign.status == ST_NEW:
        assign.status = ST_DOING
        assign.task.status = ST_DOING

    now = datetime.now()
    if assign.progress_pct == 100:
        assign.status = ST_DONE
        assign.completed_at = now
        assign.is_late = now.date() > assign.task.original_deadline
        assign.is_late_current = now.date() > assign.task.current_deadline
        assign.delay_days = (now.date() - assign.task.original_deadline).days

        preds = db.query(RiskPrediction).filter_by(assignment_id=assign.id).all()
        for p in preds:
            p.actual_is_late = assign.is_late
            p.resolved_at = now

        all_done = all(a.status == ST_DONE for a in assign.task.assignments)
        if all_done:
            assign.task.status = ST_DONE

    prog = ProgressUpdate(
        assignment_id=assign.id,
        progress_pct=req.progress_pct,
        note=req.note,
        created_by=user.id,
        created_at=now
    )
    db.add(prog)
    db.commit()
    return {"message": "Cập nhật tiến độ thành công", "progress_pct": assign.progress_pct, "status": assign.status}


@router.post("/{task_id}/extensions")
def request_extension(
    task_id: int,
    req: ExtensionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy công việc")

    if req.proposed_deadline <= task.current_deadline:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Thời hạn đề xuất phải sau hạn hiện tại")

    ext = ExtensionRequest(
        task_id=task.id,
        requested_by=user.id,
        reason=req.reason,
        old_deadline=task.current_deadline,
        proposed_deadline=req.proposed_deadline,
        status=EXT_PENDING
    )
    db.add(ext)
    db.flush()

    managers = db.query(User).filter(User.role == ROLE_MANAGER, User.is_active == True).all()
    for m in managers:
        if m.department_id is None or m.department_id == user.department_id:
            notif = Notification(
                user_id=m.id,
                kind="extension",
                title=f"Yêu cầu gia hạn: {task.title}",
                content=f"Giảng viên {user.full_name} xin gia hạn đến {req.proposed_deadline}. Lý do: {req.reason}",
                task_id=task.id,
                dedupe_key=f"ext_req:{ext.id}:{m.id}"
            )
            db.add(notif)

    db.commit()
    return {"message": "Đã gửi yêu cầu gia hạn", "extension_id": ext.id}


@router.put("/extensions/{ext_id}/review", dependencies=[Depends(manager_or_admin)])
def review_extension(
    ext_id: int,
    req: ExtensionReview,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    ext = db.get(ExtensionRequest, ext_id)
    if not ext or ext.status != EXT_PENDING:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Yêu cầu gia hạn không hợp lệ hoặc đã xử lý")

    if req.status not in (EXT_APPROVED, EXT_REJECTED):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Trạng thái phải là 'Đã duyệt' hoặc 'Từ chối'")

    ext.status = req.status
    ext.reviewed_by = user.id
    ext.reviewed_at = datetime.now()
    ext.review_note = req.review_note

    task = ext.task
    if req.status == EXT_APPROVED:
        task.current_deadline = ext.proposed_deadline
        for a in task.assignments:
            if a.status != ST_DONE:
                predict_and_record_risk(db, task.id, a.id, a.lecturer_id, trigger="extension")

    notif = Notification(
        user_id=ext.requested_by,
        kind="extension",
        title=f"Kết quả duyệt gia hạn: {task.title}",
        content=f"Yêu cầu gia hạn công việc '{task.title}' của bạn đã được {req.status}. Ghi chú: {req.review_note or 'Không có'}",
        task_id=task.id,
        dedupe_key=f"ext_res:{ext.id}:{datetime.now().timestamp()}"
    )
    db.add(notif)

    db.commit()
    return {"message": f"Đã {req.status} yêu cầu gia hạn"}


