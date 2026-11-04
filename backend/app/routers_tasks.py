"""API Router: Nghiệp vụ công việc, tiến độ, minh chứng, phân việc nhóm, gia hạn, thông báo, ML risk."""
import os
import re
import uuid
import json
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from app.db import get_db
from app.models import (
    Task, TaskAssignment, TaskType, TaskTypeScale, User, ProgressUpdate,
    ExtensionRequest, Notification, RiskPrediction, ST_NEW, ST_DOING, ST_DONE,
    EXT_PENDING, EXT_APPROVED, EXT_REJECTED, ROLE_MANAGER, ROLE_ADMIN, ROLE_LECTURER
)
from app.deps import current_user, manager_or_admin, lecturer_scope, can_see_lecturer, can_see_risk
from app.schemas import (
    TaskCreate, TaskRiskPreviewRequest, ProgressUpdateCreate,
    ExtensionCreate, ExtensionReview, GroupDelegateRequest
)
from app.ml_client import predict_and_record_risk, preview_risk_for_features
from app.ml_extract import extract_features_for_preview

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

UPLOAD_EVIDENCE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "uploads",
    "evidence"
)
os.makedirs(UPLOAD_EVIDENCE_DIR, exist_ok=True)


@router.post("/upload-evidence")
async def upload_evidence_file(
    file: UploadFile = File(...),
    user: User = Depends(current_user)
):
    """Tải lên file minh chứng kết quả tiến độ công việc."""
    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Vui lòng chọn file minh chứng hợp lệ")

    raw_name = os.path.basename(file.filename)
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", raw_name)
    unique_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}_{safe_name}"
    dest_path = os.path.join(UPLOAD_EVIDENCE_DIR, unique_name)

    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kích thước file minh chứng tối đa là 25MB")

    with open(dest_path, "wb") as f:
        f.write(content)

    return {
        "file_name": raw_name,
        "file_url": f"/uploads/evidence/{unique_name}",
        "size_bytes": len(content),
        "uploaded_by": user.full_name,
        "uploaded_at": datetime.now().isoformat()
    }


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

    if user.role == ROLE_LECTURER:
        # Giảng viên xem được việc mình được giao, việc mình phụ trách chính, hoặc việc mình được chỉ định kiểm tra
        query = query.outerjoin(TaskAssignment).filter(
            or_(
                TaskAssignment.lecturer_id == user.id,
                Task.lead_lecturer_id == user.id,
                Task.reviewer_id == user.id
            )
        )
    elif scope is not None:
        query = query.outerjoin(TaskAssignment).filter(
            or_(
                TaskAssignment.lecturer_id.in_(scope),
                Task.created_by == user.id,
                Task.reviewer_id == user.id
            )
        )
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
            if can_see_risk(db, user, a.lecturer_id) or t.lead_lecturer_id == user.id or t.reviewer_id == user.id:
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

            is_lead_flag = bool(a.is_lead or (t.lead_lecturer_id == a.lecturer_id))
            assignees.append({
                "assignment_id": a.id,
                "lecturer_id": a.lecturer_id,
                "lecturer_name": a.lecturer.full_name,
                "lecturer_code": a.lecturer.profile.lecturer_code if a.lecturer.profile else "",
                "department_name": a.lecturer.department.name if a.lecturer.department else "",
                "is_lead": is_lead_flag,
                "member_task_note": a.member_task_note,
                "latest_evidence_name": a.latest_evidence_name,
                "latest_evidence_url": a.latest_evidence_url,
                "progress_pct": a.progress_pct,
                "status": a.status,
                "is_late": a.is_late,
                "delay_days": a.delay_days,
                "completed_at": a.completed_at,
                "ml_prediction": ml_info
            })

        # Sắp xếp người phụ trách chính lên đầu danh sách assignees
        assignees.sort(key=lambda x: (0 if x["is_lead"] else 1, x["assignment_id"]))

        conv_hours = (
            t.school_item.conversion_hours
            if t.school_item
            else scales.get((t.task_type_id, t.scale), 0.0)
        )

        creator_name = t.creator.full_name if t.creator else "Hệ thống"
        reviewer_user = t.reviewer if t.reviewer else t.creator
        reviewer_name = reviewer_user.full_name if reviewer_user else creator_name
        lead_user = t.lead_lecturer
        if not lead_user and assignees:
            lead_item = next((x for x in assignees if x["is_lead"]), assignees[0])
            lead_name = lead_item["lecturer_name"]
            lead_id = lead_item["lecturer_id"]
        else:
            lead_name = lead_user.full_name if lead_user else None
            lead_id = t.lead_lecturer_id

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
            "created_by": t.created_by,
            "creator_name": creator_name,
            "reviewer_id": t.reviewer_id or t.created_by,
            "reviewer_name": reviewer_name,
            "lead_lecturer_id": lead_id,
            "lead_lecturer_name": lead_name,
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
        query = query.filter(
            or_(
                ExtensionRequest.requested_by == user.id,
                Task.reviewer_id == user.id,
                Task.lead_lecturer_id == user.id
            )
        )
    elif user.role == ROLE_MANAGER and user.department_id is not None:
        scope = lecturer_scope(db, user)
        if scope is not None:
            query = query.filter(
                or_(
                    ExtensionRequest.requested_by.in_(scope),
                    Task.reviewer_id == user.id,
                    Task.created_by == user.id
                )
            )

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
    """Lấy chi tiết công việc kèm nhật ký tiến độ, file minh chứng, lịch sử gia hạn và phân công nhóm."""
    t = db.get(Task, task_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy công việc")

    progress_logs = []
    assignees_detail = []
    for a in t.assignments:
        is_lead_flag = bool(a.is_lead or (t.lead_lecturer_id == a.lecturer_id))
        assignees_detail.append({
            "assignment_id": a.id,
            "lecturer_id": a.lecturer_id,
            "lecturer_name": a.lecturer.full_name,
            "lecturer_code": a.lecturer.profile.lecturer_code if a.lecturer.profile else "",
            "is_lead": is_lead_flag,
            "member_task_note": a.member_task_note,
            "progress_pct": a.progress_pct,
            "status": a.status,
            "latest_evidence_name": a.latest_evidence_name,
            "latest_evidence_url": a.latest_evidence_url,
            "completed_at": a.completed_at,
            "is_late": a.is_late,
            "delay_days": a.delay_days
        })
        for p in a.progress_updates:
            u = db.get(User, p.created_by) if p.created_by else None
            progress_logs.append({
                "id": p.id,
                "lecturer_name": a.lecturer.full_name,
                "progress_pct": p.progress_pct,
                "note": p.note,
                "evidence_file_name": p.evidence_file_name,
                "evidence_file_url": p.evidence_file_url,
                "created_by_name": u.full_name if u else a.lecturer.full_name,
                "created_at": p.created_at
            })
    progress_logs.sort(key=lambda x: x["created_at"], reverse=True)
    assignees_detail.sort(key=lambda x: (0 if x["is_lead"] else 1, x["assignment_id"]))

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

    creator_name = t.creator.full_name if t.creator else "Hệ thống"
    reviewer_user = t.reviewer if t.reviewer else t.creator
    reviewer_name = reviewer_user.full_name if reviewer_user else creator_name

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
        "assignment_mode": t.assignment_mode,
        "assigned_at": t.assigned_at,
        "original_deadline": t.original_deadline,
        "current_deadline": t.current_deadline,
        "status": t.status,
        "creator_name": creator_name,
        "reviewer_id": t.reviewer_id or t.created_by,
        "reviewer_name": reviewer_name,
        "lead_lecturer_id": t.lead_lecturer_id,
        "lead_lecturer_name": t.lead_lecturer.full_name if t.lead_lecturer else None,
        "school_catalog_name": t.school_item.name if t.school_item else None,
        "assignees": assignees_detail,
        "progress_logs": progress_logs,
        "extensions": ext_logs
    }


@router.post("", dependencies=[Depends(manager_or_admin)])
def create_task(req: TaskCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """
    Giao việc mới (FR-01, FR-02) + Gọi dự đoán rủi ro ML (FR-10):
    - Nếu phân từ 2 người trở lên: bắt buộc có 1 người phụ trách chính (lead_lecturer_id).
    - Nếu không chọn người kiểm tra (reviewer_id): mặc định người giao (user.id) là người kiểm tra.
    """
    if req.original_deadline <= date.today():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Thời hạn hoàn thành phải sau ngày giao ít nhất 1 ngày")

    unique_lecturer_ids = list(dict.fromkeys(req.lecturer_ids))
    if len(unique_lecturer_ids) >= 2:
        if not req.lead_lecturer_id or req.lead_lecturer_id not in unique_lecturer_ids:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Khi phân công từ 2 người trở lên, bắt buộc phải chọn 1 người phụ trách chính trong danh sách nhận việc."
            )
        lead_id = req.lead_lecturer_id
    else:
        lead_id = unique_lecturer_ids[0]

    # Nếu không chọn người kiểm tra thì người giao chính là người kiểm tra
    reviewer_id = req.reviewer_id if req.reviewer_id else user.id
    reviewer_user = db.get(User, reviewer_id) or user

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
        assignment_mode="Group" if len(unique_lecturer_ids) > 1 else "Individual",
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
        reviewer_id=reviewer_id,
        lead_lecturer_id=lead_id,
        plan_id=req.plan_id
    )
    db.add(task)
    db.flush()

    predictions_summary = []
    member_notes_map = req.member_notes or {}

    for lid in unique_lecturer_ids:
        is_lead_member = (lid == lead_id)
        member_note = member_notes_map.get(str(lid))
        assign = TaskAssignment(
            task_id=task.id,
            lecturer_id=lid,
            is_lead=is_lead_member,
            member_task_note=member_note,
            progress_pct=0,
            status=ST_NEW
        )
        db.add(assign)
        db.flush()

        role_label = "Người phụ trách chính (Chủ trì nhóm)" if (len(unique_lecturer_ids) > 1 and is_lead_member) else (
            "Thành viên nhóm" if len(unique_lecturer_ids) > 1 else "Người thực hiện"
        )
        note_suffix = f" Nhiệm vụ chi tiết: {member_note}." if member_note else ""
        notif = Notification(
            user_id=lid,
            kind="new_task",
            title=f"Công việc mới [{role_label}]: {task.title}",
            content=(
                f"Bạn được giao công việc '{task.title}' ({role_label}) với mức ưu tiên {task.priority}. "
                f"Hạn chót: {task.current_deadline}. Người kiểm tra tiến độ: {reviewer_user.full_name}.{note_suffix}"
            ),
            task_id=task.id,
            dedupe_key=f"new_task:{task.id}:{lid}"
        )
        db.add(notif)

        pred = predict_and_record_risk(db, task.id, assign.id, lid, trigger="assign")
        predictions_summary.append({
            "lecturer_id": lid,
            "is_lead": is_lead_member,
            "status": pred.status,
            "probability": pred.probability,
            "level": pred.level,
            "uncertainty": pred.uncertainty,
            "top_factors": json.loads(pred.top_factors) if pred.top_factors else [],
            "recommendation": pred.recommendation,
            "notes": pred.notes,
            "low_confidence": pred.low_confidence
        })

    if reviewer_id != user.id:
        db.add(Notification(
            user_id=reviewer_id,
            kind="new_task",
            title=f"Phân công kiểm tra tiến độ: {task.title}",
            content=f"{user.full_name} đã chỉ định bạn làm Người kiểm tra tiến độ cho công việc '{task.title}' (Mã {task.code}).",
            task_id=task.id,
            dedupe_key=f"reviewer_assign:{task.id}:{reviewer_id}"
        ))

    db.commit()
    return {
        "message": "Giao việc thành công",
        "task_id": task.id,
        "code": task.code,
        "lead_lecturer_id": lead_id,
        "reviewer_id": reviewer_id,
        "reviewer_name": reviewer_user.full_name,
        "predictions": predictions_summary
    }


@router.post("/{task_id}/delegate")
def delegate_group_task(
    task_id: int,
    req: GroupDelegateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    """
    Cho phép Người phụ trách chính của nhóm (hoặc Quản lý / Người kiểm tra) phân chia đầu việc cụ thể
    hoặc giao thêm việc cho các thành viên khác trong nhóm.
    """
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy công việc")

    is_lead_user = (task.lead_lecturer_id == user.id) or any(
        a.lecturer_id == user.id and a.is_lead for a in task.assignments
    )
    is_reviewer_or_mgr = (
        user.role in (ROLE_MANAGER, ROLE_ADMIN)
        or task.reviewer_id == user.id
        or task.created_by == user.id
    )
    if not (is_lead_user or is_reviewer_or_mgr):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Chỉ Người phụ trách chính của nhóm hoặc Người quản lý/kiểm tra mới có quyền phân chia công việc cho các thành viên."
        )

    existing_map = {a.lecturer_id: a for a in task.assignments}
    added_count = 0
    updated_count = 0

    for item in req.members:
        if item.lecturer_id in existing_map:
            assign = existing_map[item.lecturer_id]
            if assign.member_task_note != item.member_task_note:
                assign.member_task_note = item.member_task_note
                updated_count += 1
                if item.lecturer_id != user.id and item.member_task_note:
                    db.add(Notification(
                        user_id=item.lecturer_id,
                        kind="new_task",
                        title=f"Phân công nhiệm vụ nhóm: {task.title}",
                        content=f"Người phụ trách ({user.full_name}) đã giao nhiệm vụ chi tiết cho bạn trong '{task.title}': {item.member_task_note}",
                        task_id=task.id,
                        dedupe_key=f"delegate_upd:{task.id}:{item.lecturer_id}:{uuid.uuid4().hex[:6]}"
                    ))
        else:
            # Thêm thành viên mới vào nhóm
            new_assign = TaskAssignment(
                task_id=task.id,
                lecturer_id=item.lecturer_id,
                is_lead=False,
                member_task_note=item.member_task_note,
                progress_pct=0,
                status=ST_NEW
            )
            db.add(new_assign)
            db.flush()
            added_count += 1

            db.add(Notification(
                user_id=item.lecturer_id,
                kind="new_task",
                title=f"Được giao việc vào nhóm: {task.title}",
                content=(
                    f"{user.full_name} đã phân công bạn tham gia nhóm công việc '{task.title}'. "
                    f"Nhiệm vụ: {item.member_task_note or 'Phối hợp thực hiện theo kế hoạch nhóm'}. Hạn chót: {task.current_deadline}."
                ),
                task_id=task.id,
                dedupe_key=f"delegate_new:{task.id}:{item.lecturer_id}"
            ))
            predict_and_record_risk(db, task.id, new_assign.id, item.lecturer_id, trigger="assign")

    # Cập nhật lại chế độ nhóm và người phụ trách chính nếu có thay đổi
    db.flush()
    all_assigns = db.query(TaskAssignment).filter_by(task_id=task.id).all()
    if len(all_assigns) > 1:
        task.assignment_mode = "Group"

    if req.lead_lecturer_id:
        task.lead_lecturer_id = req.lead_lecturer_id
        for a in all_assigns:
            a.is_lead = (a.lecturer_id == req.lead_lecturer_id)

    db.commit()
    return {
        "message": f"Đã cập nhật phân công nhóm thành công (thêm mới {added_count} thành viên, cập nhật {updated_count} nhiệm vụ).",
        "added_count": added_count,
        "updated_count": updated_count
    }


@router.post("/{task_id}/progress")
def update_progress(
    task_id: int,
    req: ProgressUpdateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    """Cập nhật tiến độ hoàn thành theo % kèm file minh chứng (FR-04)."""
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy công việc")

    target_lecturer_id = req.lecturer_id or user.id
    assign = db.query(TaskAssignment).filter_by(task_id=task_id, lecturer_id=target_lecturer_id).first()

    if not assign:
        # Nếu quản lý/người kiểm tra/trưởng nhóm cập nhật mà không truyền lecturer_id thì lấy dòng của trưởng nhóm hoặc dòng đầu tiên
        if user.role in (ROLE_MANAGER, ROLE_ADMIN) or task.reviewer_id == user.id or task.lead_lecturer_id == user.id:
            assign = (
                db.query(TaskAssignment).filter_by(task_id=task_id, is_lead=True).first()
                or db.query(TaskAssignment).filter_by(task_id=task_id).first()
            )

    if not assign:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bạn không phụ trách công việc này")

    can_edit = (
        assign.lecturer_id == user.id
        or task.lead_lecturer_id == user.id
        or task.reviewer_id == user.id
        or task.created_by == user.id
        or user.role in (ROLE_MANAGER, ROLE_ADMIN)
    )
    if not can_edit:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bạn không có quyền cập nhật tiến độ cho phân công này")

    assign.progress_pct = req.progress_pct
    if req.evidence_file_url:
        assign.latest_evidence_name = req.evidence_file_name or "File minh chứng"
        assign.latest_evidence_url = req.evidence_file_url

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
        evidence_file_name=req.evidence_file_name,
        evidence_file_url=req.evidence_file_url,
        created_by=user.id,
        created_at=now
    )
    db.add(prog)
    db.commit()
    return {
        "message": "Cập nhật tiến độ thành công",
        "progress_pct": assign.progress_pct,
        "status": assign.status,
        "evidence_file_name": assign.latest_evidence_name,
        "evidence_file_url": assign.latest_evidence_url
    }


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

    notify_ids = set()
    if task.reviewer_id:
        notify_ids.add(task.reviewer_id)
    if task.created_by:
        notify_ids.add(task.created_by)
    managers = db.query(User).filter(User.role == ROLE_MANAGER, User.is_active == True).all()
    for m in managers:
        if m.department_id is None or m.department_id == user.department_id:
            notify_ids.add(m.id)

    for uid in notify_ids:
        notif = Notification(
            user_id=uid,
            kind="extension",
            title=f"Yêu cầu gia hạn: {task.title}",
            content=f"Giảng viên {user.full_name} xin gia hạn đến {req.proposed_deadline}. Lý do: {req.reason}",
            task_id=task.id,
            dedupe_key=f"ext_req:{ext.id}:{uid}"
        )
        db.add(notif)

    db.commit()
    return {"message": "Đã gửi yêu cầu gia hạn", "extension_id": ext.id}


@router.put("/extensions/{ext_id}/review")
def review_extension(
    ext_id: int,
    req: ExtensionReview,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    ext = db.get(ExtensionRequest, ext_id)
    if not ext or ext.status != EXT_PENDING:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Yêu cầu gia hạn không hợp lệ hoặc đã xử lý")

    task = ext.task
    if user.role not in (ROLE_MANAGER, ROLE_ADMIN) and task.reviewer_id != user.id and task.created_by != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Chỉ Quản lý hoặc Người kiểm tra tiến độ của công việc này mới có quyền duyệt gia hạn")

    if req.status not in (EXT_APPROVED, EXT_REJECTED):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Trạng thái phải là 'Đã duyệt' hoặc 'Từ chối'")

    ext.status = req.status
    ext.reviewed_by = user.id
    ext.reviewed_at = datetime.now()
    ext.review_note = req.review_note

    if req.status == EXT_APPROVED:
        task.current_deadline = ext.proposed_deadline
        for a in task.assignments:
            if a.status != ST_DONE:
                predict_and_record_risk(db, task.id, a.id, a.lecturer_id, trigger="extension")

    notif = Notification(
        user_id=ext.requested_by,
        kind="extension",
        title=f"Kết quả duyệt gia hạn: {task.title}",
        content=f"Yêu cầu gia hạn công việc '{task.title}' của bạn đã được {req.status} bởi {user.full_name}. Ghi chú: {req.review_note or 'Không có'}",
        task_id=task.id,
        dedupe_key=f"ext_res:{ext.id}:{datetime.now().timestamp()}"
    )
    db.add(notif)

    db.commit()
    return {"message": f"Đã {req.status} yêu cầu gia hạn"}
