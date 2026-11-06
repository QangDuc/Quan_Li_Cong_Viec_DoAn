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
    Task, TaskAssignment, TaskApprovalLog, TaskType, TaskTypeScale, User, ProgressUpdate,
    ExtensionRequest, Notification, RiskPrediction, ST_NEW, ST_DOING, ST_DONE,
    EXT_PENDING, EXT_APPROVED, EXT_REJECTED, ROLE_MANAGER, ROLE_ADMIN, ROLE_LECTURER
)
from app.deps import current_user, manager_or_admin, lecturer_scope, can_see_lecturer, can_see_risk
from app.rbac import calculate_project_progress_from_assignments, is_task_in_manager_department_scope
from app.schemas import (
    TaskCreate, TaskRiskPreviewRequest, ProgressUpdateCreate,
    ExtensionCreate, ExtensionReview, GroupDelegateRequest,
    MemberEvidenceSubmitRequest, TaskFeedbackRequest,
    LeadGroupApproveRequest, ReviewerApproveLeadRequest
)
from app.ml_client import predict_and_record_risk, preview_risk_for_features, preview_risk_for_features_batch
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
    elif user.role == ROLE_MANAGER and user.department_id is not None:
        # Trưởng Bộ môn chỉ quản lý được các công việc thuộc Bộ môn đó của Khoa
        query = query.outerjoin(TaskAssignment).filter(
            or_(
                Task.department_id == user.department_id,
                TaskAssignment.lecturer_id.in_(scope or []),
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
                "member_evidence_status": a.member_evidence_status,
                "review_feedback": a.review_feedback,
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

        task_dept_id = t.department_id
        task_dept_name = t.department.name if t.department else None
        if not task_dept_id and lead_user and lead_user.department_id:
            task_dept_id = lead_user.department_id
            task_dept_name = lead_user.department.name if lead_user.department else None

        res.append({
            "id": t.id,
            "code": t.code,
            "title": t.title,
            "description": t.description,
            "task_type_id": t.task_type_id,
            "task_type_name": t.task_type.name,
            "task_group": t.task_type.task_group,
            "department_id": task_dept_id,
            "department_name": task_dept_name or "Khoa CNTT",
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
            "progress_pct": t.progress_pct,
            "lead_approval_status": t.lead_approval_status,
            "lead_decision_note": t.lead_decision_note,
            "reviewer_approval_status": t.reviewer_approval_status,
            "reviewer_decision_note": t.reviewer_decision_note,
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
    # Ưu tiên đưa các công việc đang thực hiện / việc nhóm lên trên cùng để dễ theo dõi và thao tác
    res.sort(key=lambda item: (
        0 if (item["status"] != ST_DONE and item["assignment_mode"] == "Group") else (1 if item["status"] != ST_DONE else 2),
        -item["id"]
    ))
    return res


@router.post("/preview-risk", dependencies=[Depends(manager_or_admin)])
def preview_task_risk(
    req: TaskRiskPreviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    """
    Xem trước dự đoán rủi ro trễ hạn ML & Gợi ý tối ưu:
    1. Chỉ đề xuất giảng viên có năng lực/kinh nghiệm thuộc Nhóm công việc được chọn (task_group).
    2. Lọc ưu tiên các giảng viên có độ trễ dự báo thấp nhất.
    3. Tự động gợi ý Ứng viên làm Người Phụ trách chính (Trưởng nhóm) kèm bộ 4 tiêu chí/điều kiện xét chọn rõ ràng.
    """
    if req.original_deadline <= date.today():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Thời hạn hoàn thành phải sau ngày giao ít nhất 1 ngày")

    tt = db.get(TaskType, req.task_type_id)
    selected_group = tt.task_group if tt else "Chuyên môn Khoa"
    selected_type_name = tt.name if tt else "Công việc chuyên môn"

    if req.lecturer_ids and len(req.lecturer_ids) > 0:
        lecturers = db.query(User).filter(User.id.in_(req.lecturer_ids), User.is_active == True).all()
    else:
        q = db.query(User).filter(User.role == ROLE_LECTURER, User.is_active == True)
        if user.role == ROLE_MANAGER and user.department_id is not None:
            q = q.filter(User.department_id == user.department_id)
        lecturers = q.all()

    team_size = len(req.lecturer_ids) if req.lecturer_ids and len(req.lecturer_ids) > 1 else 1
    raw_candidates = []
    lec_contexts = []

    for lec in lecturers:
        # Tính số việc đã hoàn thành thuộc đúng Nhóm công việc (task_group) được chọn
        group_assigns = (
            db.query(TaskAssignment)
            .join(Task)
            .join(TaskType, Task.task_type_id == TaskType.id)
            .filter(
                TaskAssignment.lecturer_id == lec.id,
                TaskType.task_group == selected_group,
                TaskAssignment.status == ST_DONE
            )
            .all()
        )
        group_done_cnt = len(group_assigns)
        group_late_cnt = sum(1 for ga in group_assigns if ga.is_late)
        group_on_time_rate = round((group_done_cnt - group_late_cnt) / group_done_cnt * 100, 1) if group_done_cnt > 0 else 100.0

        # Số lần từng làm Trưởng nhóm (Phụ trách chính)
        lead_exp_cnt = (
            db.query(TaskAssignment)
            .filter(TaskAssignment.lecturer_id == lec.id, TaskAssignment.is_lead == True)
            .count()
        )

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
        lec_contexts.append((lec, group_done_cnt, group_on_time_rate, lead_exp_cnt, feats))

    batch_preds = preview_risk_for_features_batch([ctx[4] for ctx in lec_contexts])

    for (lec, group_done_cnt, group_on_time_rate, lead_exp_cnt, feats), pred in zip(lec_contexts, batch_preds):
        prob = float(pred.get("probability") if pred.get("probability") is not None else 0.18)
        open_tasks = int(feats.get("active_tasks") or 0)
        overdue_tasks = int(feats.get("overdue_open_tasks") or 0)
        hist_completed = int(feats.get("hist_count") or 0)
        hist_late_rate = round(float(feats.get("hist_late_rate") or 0.0) * 100, 1)
        mat_type_cnt = int(feats.get("lecturer_task_count") or 0)
        degree_str = lec.profile.degree if lec.profile else "Thạc sĩ"
        rank_str = lec.profile.academic_rank if lec.profile else "Giảng viên"

        # --- ĐÁNH GIÁ 4 ĐIỀU KIỆN ĐỂ GỢI Ý NGƯỜI PHỤ TRÁCH CHÍNH (TRƯỞNG NHÓM) ---
        cond1_pass = prob < 0.23
        cond2_pass = (group_done_cnt >= 1 or mat_type_cnt >= 1) and group_on_time_rate >= 80.0
        cond3_pass = ("Tiến sĩ" in degree_str) or ("PGS" in degree_str) or ("chính" in rank_str.lower()) or (hist_completed >= 8)
        cond4_pass = (overdue_tasks == 0) and (open_tasks <= 3)

        lead_score = 0
        lead_score += max(0, int((1.0 - min(prob, 0.8)) * 40))  # Tối đa 40đ từ độ trễ thấp
        lead_score += min(25, group_done_cnt * 6 + mat_type_cnt * 5) if group_on_time_rate >= 80 else 8
        lead_score += 20 if ("Tiến sĩ" in degree_str or "PGS" in degree_str or "chính" in rank_str.lower()) else 12
        lead_score += 15 if cond4_pass else (5 if overdue_tasks == 0 else 0)
        lead_score = min(99, lead_score)

        lead_conditions = [
            {
                "code": "LOW_DELAY_RISK",
                "title": "1. Độ trễ dự báo ở mức Thấp (< 23%)",
                "criterion": "1. Nguy cơ trễ hạn dự báo thấp nhất (ML Risk)",
                "passed": cond1_pass,
                "detail": f"Xác suất trễ hạn dự báo chỉ {(prob * 100):.1f}% (Mức {pred.get('level', 'Thấp')})"
            },
            {
                "code": "GROUP_EXPERTISE",
                "title": f"2. Sở trường nhóm việc '{selected_group}'",
                "criterion": f"2. Kinh nghiệm thực hiện trong Nhóm công việc '{selected_group}'",
                "passed": cond2_pass,
                "detail": f"Đã hoàn thành {max(group_done_cnt, mat_type_cnt)} việc thuộc nhóm này (Đúng hạn {group_on_time_rate}%)"
            },
            {
                "code": "LEADERSHIP_QUALIFICATION",
                "title": "3. Năng lực học thuật & Kinh nghiệm chủ trì",
                "criterion": "3. Học vị chuyên môn & Kinh nghiệm chủ trì",
                "passed": cond3_pass,
                "detail": f"{degree_str} • {rank_str} • Đã hoàn thành {hist_completed} việc lịch sử ({lead_exp_cnt} lần chủ trì)"
            },
            {
                "code": "WORKLOAD_AVAILABILITY",
                "title": "4. Quỹ thời gian sẵn sàng điều phối nhóm",
                "criterion": "4. Tải công việc hiện tại không quá tải & 0 việc quá hạn",
                "passed": cond4_pass,
                "detail": f"Đang mở {open_tasks} việc • Quá hạn: {overdue_tasks} việc"
            }
        ]

        raw_candidates.append({
            "lecturer_id": lec.id,
            "full_name": lec.full_name,
            "lecturer_code": lec.profile.lecturer_code if lec.profile else f"GV{lec.id:04d}",
            "department_name": lec.department.name if lec.department else "",
            "academic_rank": rank_str,
            "degree": degree_str,
            "teaching_hours_semester": lec.profile.teaching_hours_semester if lec.profile else 0.0,
            "current_open_tasks": open_tasks,
            "current_overdue_tasks": overdue_tasks,
            "hist_completed_count": hist_completed,
            "hist_late_rate": hist_late_rate,
            "mat_type_count": mat_type_cnt,
            "mat_type_late_rate": round(float(feats.get("lecturer_task_late_rate") or 0.0) * 100, 1),
            "task_group_match": selected_group,
            "group_done_count": max(group_done_cnt, mat_type_cnt),
            "group_completed_count": max(group_done_cnt, mat_type_cnt),
            "group_on_time_rate": group_on_time_rate,
            "in_selected_group": (group_done_cnt > 0 or mat_type_cnt > 0),
            "lead_time_days": int(feats.get("available_days") or 0),
            "expected_duration_days": round(float(feats.get("expected_duration_days") or 7.0), 1),
            "lead_vs_expected_ratio": round(float(feats.get("deadline_pressure") or 1.0), 2),
            "status": pred.get("status", "ok"),
            "probability": prob,
            "level": pred.get("level"),
            "uncertainty": pred.get("uncertainty"),
            "top_factors": pred.get("top_factors", []),
            "recommendation": pred.get("recommendation"),
            "low_confidence": pred.get("low_confidence", False),
            "latency_ms": pred.get("latency_ms", 0),
            "lead_score": lead_score,
            "lead_conditions_passed": sum(1 for c in lead_conditions if c["passed"]),
            "lead_conditions": lead_conditions,
            "conditions": lead_conditions,
            "is_recommended_lead": False,
        })

    # 1. Lọc giảng viên thuộc nhóm công việc được chọn (có kinh nghiệm nhóm việc đó)
    group_matched = [c for c in raw_candidates if c["in_selected_group"]]
    pool = group_matched if len(group_matched) >= 2 else raw_candidates

    # 2. Sắp xếp từ độ trễ dự báo thấp nhất -> cao nhất
    pool.sort(key=lambda c: (c["probability"], c["current_open_tasks"], -c["lead_score"]))

    # 3. Chỉ lọc ra các giảng viên có độ trễ thấp nhất (Mức Thấp hoặc Top 5 người độ trễ thấp nhất trong nhóm việc)
    low_risk_only = [c for c in pool if c["probability"] < 0.30]
    final_candidates = low_risk_only[:6] if len(low_risk_only) >= 2 else pool[:5]

    for idx, c in enumerate(final_candidates):
        c["rank"] = idx + 1

    # 4. Chọn Người Phụ trách chính được đề xuất tốt nhất (điểm lead_score cao nhất trong nhóm độ trễ thấp)
    recommended_lead = None
    if final_candidates:
        best_lead = max(final_candidates, key=lambda c: (c["lead_conditions_passed"], c["lead_score"], -c["probability"]))
        best_lead["is_recommended_lead"] = True
        best_lead["reason_summary"] = (
            f"Đạt điểm tiêu chí Phụ trách chính cao nhất ({best_lead['lead_score']}/100): "
            f"độ trễ dự báo thấp ({(best_lead['probability'] * 100):.1f}%), "
            f"đã hoàn thành {best_lead['group_done_count']} việc thuộc nhóm '{selected_group}' "
            f"và đang mở {best_lead['current_open_tasks']} việc ({best_lead['current_overdue_tasks']} việc quá hạn)."
        )
        recommended_lead = best_lead

    lead_criteria_rules = [
        "1. Độ trễ dự báo thấp nhất: Xác suất trễ hạn ML đạt ngưỡng an toàn (< 23%).",
        f"2. Đúng nhóm chuyên môn: Có lịch sử hoàn thành tốt các đầu việc thuộc nhóm '{selected_group}' (tỷ lệ đúng hạn ≥ 80%).",
        "3. Năng lực chủ trì & Học thuật: Ưu tiên Tiến sĩ / PGS / Giảng viên chính hoặc có kinh nghiệm chủ trì nhiều đầu việc.",
        "4. Quỹ thời gian khả dụng: Không có công việc đang quá hạn (0 việc quá hạn) và tải hiện tại ≤ 3 việc."
    ]

    return {
        "selected_task_group": selected_group,
        "selected_task_type_name": selected_type_name,
        "total_evaluated": len(raw_candidates),
        "candidates": final_candidates,
        "recommended_lead": recommended_lead,
        "lead_criteria_rules": lead_criteria_rules,
        "thresholds": {"low": 0.23, "high": 0.52},
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
            "member_evidence_status": a.member_evidence_status,
            "review_feedback": a.review_feedback,
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

    # Ràng buộc Trưởng Bộ môn: chỉ được giao và quản lý công việc thuộc Bộ môn của mình trong Khoa
    lead_user_obj = db.get(User, lead_id)
    if user.role == ROLE_MANAGER and user.department_id is not None:
        assigned_users = db.query(User).filter(User.id.in_(unique_lecturer_ids)).all()
        for au in assigned_users:
            if au.department_id != user.department_id:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "Phân quyền CSDL (RBAC): Trưởng Bộ môn chỉ quản lý và giao được các công việc thuộc Bộ môn đó của Khoa!"
                )
        task_department_id = user.department_id
    else:
        task_department_id = lead_user_obj.department_id if lead_user_obj else user.department_id

    code = f"CV-{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    task = Task(
        code=code,
        title=req.title,
        description=req.description,
        task_type_id=req.task_type_id,
        department_id=task_department_id,
        scale=req.scale or "quy mô chuẩn",
        school_catalog_id=req.school_catalog_id,
        priority=req.priority or "Trung bình",
        complexity=req.complexity or "Trung bình",
        assignment_mode="Group" if len(unique_lecturer_ids) > 1 else "Individual",
        assignment_level=req.assignment_level or ("Bộ môn" if user.department_id else "Khoa"),
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
    cho các thành viên hiện có trong nhóm (không thêm người ngoài nhóm).
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
            "Chỉ Người phụ trách chính của nhóm hoặc Người quản lý/kiểm tra mới có quyền phân chia nhiệm vụ cho các thành viên."
        )

    existing_map = {a.lecturer_id: a for a in task.assignments}
    updated_count = 0

    for item in req.members:
        if item.lecturer_id not in existing_map:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Không được phép thêm giảng viên ngoài nhóm vào phân công nhiệm vụ nhóm."
            )
        assign = existing_map[item.lecturer_id]
        new_note = (item.member_task_note or "").strip()
        if assign.member_task_note != new_note:
            assign.member_task_note = new_note
            updated_count += 1
            if item.lecturer_id != user.id and new_note:
                db.add(Notification(
                    user_id=item.lecturer_id,
                    kind="new_task",
                    title=f"Phân công nhiệm vụ nhóm [{task.code}]: {task.title}",
                    content=f"Người phụ trách ({user.full_name}) đã giao nhiệm vụ chi tiết cho bạn trong '{task.title}': {new_note}",
                    task_id=task.id,
                    dedupe_key=f"delegate_upd:{task.id}:{item.lecturer_id}:{uuid.uuid4().hex[:6]}"
                ))

    db.flush()
    all_assigns = db.query(TaskAssignment).filter_by(task_id=task.id).all()
    if req.lead_lecturer_id and req.lead_lecturer_id in existing_map:
        task.lead_lecturer_id = req.lead_lecturer_id
        for a in all_assigns:
            a.is_lead = (a.lecturer_id == req.lead_lecturer_id)

    db.commit()
    return {
        "message": f"Đã lưu phân công nhiệm vụ cho các thành viên nhóm '{task.code}' thành công ({updated_count} nhiệm vụ được cập nhật).",
        "updated_count": updated_count
    }


@router.post("/{task_id}/member-evidence")
def submit_member_evidence(
    task_id: int,
    req: MemberEvidenceSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    """
    Thành viên trong nhóm gửi file minh chứng phần việc của mình lên cho Trưởng nhóm (Người phụ trách chính) kiểm tra trước.
    """
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy công việc")

    assign = db.query(TaskAssignment).filter_by(task_id=task_id, lecturer_id=user.id).first()
    if not assign:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Chỉ giảng viên là thành viên của nhóm mới được gửi minh chứng phần việc của mình.")

    now = datetime.now()
    assign.latest_evidence_name = req.evidence_file_name
    assign.latest_evidence_url = req.evidence_file_url
    assign.member_evidence_status = "Đã gửi Trưởng nhóm"
    if assign.status == ST_NEW:
        assign.status = ST_DOING
        task.status = ST_DOING

    prog = ProgressUpdate(
        assignment_id=assign.id,
        progress_pct=assign.progress_pct,
        note=f"[Gửi Trưởng nhóm duyệt] {req.note}",
        evidence_file_name=req.evidence_file_name,
        evidence_file_url=req.evidence_file_url,
        created_by=user.id,
        created_at=now
    )
    db.add(prog)

    # Thông báo cho Trưởng nhóm (Người phụ trách chính)
    lead_id = task.lead_lecturer_id
    if not lead_id:
        lead_assign = next((a for a in task.assignments if a.is_lead), None)
        lead_id = lead_assign.lecturer_id if lead_assign else None

    if lead_id and lead_id != user.id:
        db.add(Notification(
            user_id=lead_id,
            kind="new_task",
            title=f"Minh chứng thành viên nhóm [{task.code}]: {user.full_name}",
            content=f"Thành viên {user.full_name} đã nộp file minh chứng '{req.evidence_file_name}' lên Trưởng nhóm cho công việc '{task.title}'. Ghi chú: {req.note}",
            task_id=task.id,
            dedupe_key=f"mem_ev:{task.id}:{user.id}:{uuid.uuid4().hex[:6]}"
        ))

    db.commit()
    return {
        "message": f"Đã gửi file minh chứng '{req.evidence_file_name}' lên Người phụ trách chính (Trưởng nhóm) để kiểm tra và cập nhật tiến độ!",
        "evidence_file_name": assign.latest_evidence_name,
        "member_evidence_status": assign.member_evidence_status
    }


@router.post("/{task_id}/feedback")
def send_task_feedback(
    task_id: int,
    req: TaskFeedbackRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    """
    Người phụ trách chính (Trưởng nhóm) hoặc Người kiểm tra / Quản lý gửi thông báo nhắc nhở thiếu sót
    để thành viên / nhóm kịp thời bổ sung hoàn thiện.
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
            "Chỉ Người phụ trách chính hoặc Người kiểm tra / Quản lý mới có quyền gửi thông báo rà soát thiếu sót."
        )

    sender_role = "Người phụ trách chính" if is_lead_user and user.role == ROLE_LECTURER else "Người kiểm tra / Quản lý"
    targets = []
    if req.lecturer_id:
        t_assign = db.query(TaskAssignment).filter_by(task_id=task_id, lecturer_id=req.lecturer_id).first()
        if t_assign:
            targets.append(t_assign)
    else:
        targets = list(task.assignments)

    if not targets:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Không tìm thấy thành viên nhận thông báo")

    status_val = req.mark_status or req.status_action or "Cần bổ sung"
    for a in targets:
        a.review_feedback = f"[{sender_role} - {user.full_name}]: {req.feedback}"
        if status_val:
            a.member_evidence_status = status_val
        if req.progress_pct is not None:
            a.progress_pct = req.progress_pct
        if a.lecturer_id != user.id:
            db.add(Notification(
                user_id=a.lecturer_id,
                kind="overdue" if status_val == "Cần bổ sung" else "new_task",
                title=f"Yêu cầu bổ sung / Rà soát [{task.code}]: {task.title}",
                content=f"{sender_role} ({user.full_name}) thông báo về phần việc trong '{task.title}': {req.feedback}. Vui lòng kiểm tra và kịp thời hoàn thiện.",
                task_id=task.id,
                dedupe_key=f"fb:{task.id}:{a.lecturer_id}:{uuid.uuid4().hex[:6]}"
            ))

    db.commit()
    return {
        "message": f"Đã gửi thông báo rà soát / nhắc nhở thiếu sót tới {len(targets)} thành viên trong công việc '{task.code}'."
    }


@router.post("/{task_id}/progress")
def update_progress(
    task_id: int,
    req: ProgressUpdateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    """
    Quy tắc phân quyền chuẩn:
    1. Nộp file minh chứng chính thức:
       - Quản lý (manager / admin) hoặc Người kiểm tra (reviewer) KHÔNG thuộc nhóm thực hiện: KHÔNG được nộp thay file minh chứng của tài khoản khác!
       - Công việc nhóm (Group): Chỉ Trưởng nhóm (Người phụ trách chính) mới được nộp file minh chứng tổng hợp của nhóm lên Người kiểm tra.
         Nếu thành viên thường gửi file minh chứng thì tự động chuyển về trạng thái 'Đã gửi Trưởng nhóm' chờ Trưởng nhóm duyệt.
    2. Cập nhật thanh tiến độ (%):
       - Do Người kiểm tra (reviewer / manager) hoặc Người phụ trách chính (Trưởng nhóm) cập nhật cho từng thành viên nhóm (hoặc giảng viên tự cập nhật nếu là việc cá nhân 1 người).
    """
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy công việc")

    is_group = (task.assignment_mode == "Group") or (len(task.assignments) >= 2)
    my_assign = db.query(TaskAssignment).filter_by(task_id=task_id, lecturer_id=user.id).first()
    is_user_lead = bool(
        (task.lead_lecturer_id == user.id)
        or (my_assign and my_assign.is_lead)
        or (not is_group and my_assign is not None)
    )
    is_reviewer_or_mgr = (
        user.role in (ROLE_MANAGER, ROLE_ADMIN)
        or task.reviewer_id == user.id
        or task.created_by == user.id
    )

    target_lecturer_id = req.lecturer_id or user.id
    assign = db.query(TaskAssignment).filter_by(task_id=task_id, lecturer_id=target_lecturer_id).first()

    if not assign:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bạn không tham gia hoặc không có quyền trên công việc này")

    # QUY TẮC PHÂN QUYỀN MỚI:
    # 1. Mỗi tài khoản giảng viên (thành viên trong nhóm) TỰ CẬP NHẬT % tiến độ của chính mình.
    # 2. Trưởng nhóm (Người phụ trách chính) chỉ PHÊ DUYỆT tiến độ của thành viên (qua endpoint /lead-approve), không nhập hộ % của thành viên khác.
    if assign.lecturer_id != user.id and user.role != ROLE_ADMIN:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Mỗi giảng viên tự cập nhật % tiến độ của chính mình. Trưởng nhóm (Người phụ trách chính) thực hiện phê duyệt tiến độ thành viên thay vì nhập thay!"
        )

    now = datetime.now()
    assign.progress_pct = req.progress_pct
    assign.self_updated_at = now

    if req.evidence_file_url:
        assign.latest_evidence_name = req.evidence_file_name or "File minh chứng"
        assign.latest_evidence_url = req.evidence_file_url
        assign.member_evidence_status = (
            "Minh chứng chính thức của Nhóm" if (is_group and is_user_lead) else "Đã gửi Trưởng nhóm"
        )

    if is_group:
        assign.lead_approval_status = "Trưởng nhóm đã duyệt" if is_user_lead else "Chờ Trưởng nhóm duyệt"
        if not is_user_lead:
            task.lead_approval_status = "Chờ Trưởng nhóm duyệt"
    else:
        assign.lead_approval_status = "Trưởng nhóm đã duyệt"

    if assign.progress_pct > 0 and assign.status == ST_NEW:
        assign.status = ST_DOING
        if task.status == ST_NEW:
            task.status = ST_DOING

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

    # HỆ THỐNG TỰ ĐỘNG TÍNH TOÁN % TIẾN ĐỘ DỰ ÁN DỰA TRÊN TIẾN ĐỘ CỦA CÁC THÀNH VIÊN (VD: 3 NGƯỜI)
    calculated_project_pct = calculate_project_progress_from_assignments(task.assignments)
    task.progress_pct = calculated_project_pct
    if calculated_project_pct > 0 and task.status == ST_NEW:
        task.status = ST_DOING

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

    db.add(TaskApprovalLog(
        task_id=task.id,
        assignment_id=assign.id,
        actor_user_id=user.id,
        actor_role="GROUP_LEAD" if is_user_lead else "LECTURER_MEMBER",
        action_type="MEMBER_SELF_UPDATE_PROGRESS",
        member_progress_pct=req.progress_pct,
        calculated_project_pct=calculated_project_pct,
        approval_status=assign.lead_approval_status,
        note=req.note or f"Giảng viên tự cập nhật tiến độ cá nhân {req.progress_pct}%. Hệ thống tự tính tiến độ dự án = {calculated_project_pct}%.",
        created_at=now
    ))

    if is_group and task.lead_lecturer_id and task.lead_lecturer_id != user.id:
        db.add(Notification(
            user_id=task.lead_lecturer_id,
            kind="new_task",
            title=f"Thành viên tự cập nhật tiến độ [{task.code}]: {assign.progress_pct}%",
            content=(
                f"Giảng viên {user.full_name} vừa tự cập nhật tiến độ cá nhân đạt {assign.progress_pct}%. "
                f"Tiến độ dự án tự động tính từ {len(task.assignments)} thành viên hiện là {calculated_project_pct}%. "
                f"Đề nghị Trưởng nhóm xem xét phê duyệt."
            ),
            task_id=task.id,
            dedupe_key=f"self_prog:{task.id}:{user.id}:{uuid.uuid4().hex[:6]}"
        ))

    db.commit()
    return {
        "message": (
            f"Đã tự cập nhật tiến độ cá nhân đạt {assign.progress_pct}%. "
            f"Hệ thống tự động tính tiến độ chung dự án ({len(task.assignments)} thành viên) đạt {calculated_project_pct}%!"
        ),
        "progress_pct": assign.progress_pct,
        "project_progress_pct": calculated_project_pct,
        "lead_approval_status": assign.lead_approval_status,
        "status": assign.status,
        "evidence_file_name": assign.latest_evidence_name,
        "evidence_file_url": assign.latest_evidence_url,
        "member_evidence_status": assign.member_evidence_status
    }


@router.post("/{task_id}/lead-approve")
def lead_approve_group_progress(
    task_id: int,
    req: LeadGroupApproveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    """
    Trưởng nhóm (Người phụ trách chính) phê duyệt tiến độ tự cập nhật của từng thành viên,
    sau đó gửi lên hệ thống tự động tính toán % tiến độ dự án dựa trên 3 người và trình Người kiểm tra.
    """
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy công việc")

    my_assign = db.query(TaskAssignment).filter_by(task_id=task_id, lecturer_id=user.id).first()
    is_user_lead = bool((task.lead_lecturer_id == user.id) or (my_assign and my_assign.is_lead) or user.role == ROLE_ADMIN)
    if not is_user_lead:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Chỉ Trưởng nhóm (Người phụ trách chính) mới có quyền phê duyệt tiến độ của các thành viên trong nhóm!"
        )

    now = datetime.now()
    for item in req.member_approvals:
        member_assign = db.query(TaskAssignment).filter_by(task_id=task_id, lecturer_id=item.lecturer_id).first()
        if member_assign:
            member_assign.lead_approval_status = item.approval_status
            member_assign.lead_approved_by = user.id
            member_assign.lead_approved_at = now
            if item.review_note:
                member_assign.review_feedback = f"[Trưởng nhóm - {user.full_name}]: {item.review_note}"
            if item.approval_status == "Trưởng nhóm đã duyệt":
                member_assign.member_evidence_status = "Đã xác nhận"
            elif item.approval_status == "Yêu cầu chỉnh sửa":
                member_assign.member_evidence_status = "Cần bổ sung"

    # Hệ thống tự động tính toán tiến độ chung của dự án dựa trên 3 thành viên
    calculated_project_pct = calculate_project_progress_from_assignments(task.assignments)
    task.progress_pct = calculated_project_pct

    all_approved = all(a.lead_approval_status == "Trưởng nhóm đã duyệt" for a in task.assignments)
    if req.submit_to_reviewer and all_approved:
        task.lead_approval_status = "Đã duyệt & Trình Người kiểm tra"
        task.lead_submitted_at = now
        task.lead_decision_note = req.lead_decision_note or f"Đã phê duyệt tiến độ {len(task.assignments)} thành viên (Tiến độ dự án tự tính: {calculated_project_pct}%)."
        task.reviewer_approval_status = "Chờ Người kiểm tra duyệt"
        if task.reviewer_id:
            db.add(Notification(
                user_id=task.reviewer_id,
                kind="new_task",
                title=f"Trưởng nhóm trình duyệt tiến độ [{task.code}] ({calculated_project_pct}%)",
                content=(
                    f"Trưởng nhóm {user.full_name} đã phê duyệt tiến độ của {len(task.assignments)} thành viên "
                    f"(Hệ thống tự tính tiến độ dự án = {calculated_project_pct}%) và trình Người kiểm tra phê duyệt."
                ),
                task_id=task.id,
                dedupe_key=f"lead_sub:{task.id}:{uuid.uuid4().hex[:6]}"
            ))
    else:
        task.lead_approval_status = "Yêu cầu thành viên chỉnh sửa" if not all_approved else "Đã duyệt & Trình Người kiểm tra"
        task.lead_decision_note = req.lead_decision_note

    db.add(TaskApprovalLog(
        task_id=task.id,
        assignment_id=my_assign.id if my_assign else None,
        actor_user_id=user.id,
        actor_role="GROUP_LEAD",
        action_type="LEAD_SUBMIT_GROUP_DECISION",
        calculated_project_pct=calculated_project_pct,
        approval_status=task.lead_approval_status,
        note=task.lead_decision_note,
        created_at=now
    ))

    db.commit()
    return {
        "message": (
            f"Trưởng nhóm đã phê duyệt! Hệ thống tự động tính tiến độ dự án từ {len(task.assignments)} thành viên = {calculated_project_pct}% "
            f"và gửi lên Người kiểm tra."
        ),
        "project_progress_pct": calculated_project_pct,
        "lead_approval_status": task.lead_approval_status,
        "reviewer_approval_status": task.reviewer_approval_status
    }


@router.post("/{task_id}/reviewer-approve")
def reviewer_approve_lead_decision(
    task_id: int,
    req: ReviewerApproveLeadRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    """
    Người kiểm tra quan sát tiến độ từng thành viên và phê duyệt quyết định của Trưởng nhóm.
    """
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy công việc")

    is_reviewer = bool(task.reviewer_id == user.id or user.role in (ROLE_MANAGER, ROLE_ADMIN))
    if not is_reviewer:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Chỉ Người kiểm tra được phân công mới có quyền phê duyệt quyết định của Trưởng nhóm!"
        )

    now = datetime.now()
    calculated_project_pct = calculate_project_progress_from_assignments(task.assignments)
    task.progress_pct = calculated_project_pct
    task.reviewer_approval_status = req.approval_status
    task.reviewer_decision_note = req.reviewer_decision_note
    task.reviewer_approved_at = now

    if req.approval_status == "Đã phê duyệt quyết định Trưởng nhóm":
        if calculated_project_pct >= 100:
            task.status = ST_DONE
    else:
        task.lead_approval_status = "Chờ Trưởng nhóm duyệt"

    db.add(TaskApprovalLog(
        task_id=task.id,
        actor_user_id=user.id,
        actor_role="TASK_REVIEWER",
        action_type=(
            "REVIEWER_APPROVE_LEAD_DECISION"
            if req.approval_status == "Đã phê duyệt quyết định Trưởng nhóm"
            else "REVIEWER_REJECT_LEAD_DECISION"
        ),
        calculated_project_pct=calculated_project_pct,
        approval_status=req.approval_status,
        note=req.reviewer_decision_note,
        created_at=now
    ))

    if task.lead_lecturer_id:
        db.add(Notification(
            user_id=task.lead_lecturer_id,
            kind="new_task",
            title=f"Kết quả kiểm tra [{task.code}]: {req.approval_status}",
            content=f"Người kiểm tra {user.full_name} đã xử lý quyết định của Trưởng nhóm ({calculated_project_pct}%): {req.approval_status}. Ghi chú: {req.reviewer_decision_note or 'Không có'}",
            task_id=task.id,
            dedupe_key=f"rev_app:{task.id}:{uuid.uuid4().hex[:6]}"
        ))

    db.commit()
    return {
        "message": f"Người kiểm tra đã xác nhận: {req.approval_status} (Tiến độ dự án: {calculated_project_pct}%)",
        "project_progress_pct": calculated_project_pct,
        "reviewer_approval_status": task.reviewer_approval_status,
        "status": task.status
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
    if user.role == ROLE_MANAGER and user.department_id is not None and not is_task_in_manager_department_scope(user, task):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Phân quyền CSDL (RBAC): Trưởng Bộ môn chỉ quản lý và duyệt gia hạn cho các công việc thuộc Bộ môn đó của Khoa!"
        )
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
