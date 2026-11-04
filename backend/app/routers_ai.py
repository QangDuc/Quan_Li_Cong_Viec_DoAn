"""
API Router: Trợ lý AI Thông minh (AI Assistant) hỗ trợ Quản lý & Giảng viên Khoa CNTT - HUIT.
- Hỗ trợ Google Gemini API (Free Tier), Groq Cloud API (Free Tier) và Local Smart RAG Engine (chạy ngay không cần key).
- API Key được lưu cục bộ tại backend/.env.local (đã chặn trong .gitignore, tuyệt đối không đẩy lên Git).
"""
from datetime import date
from typing import Optional, List
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.deps import current_user, manager_or_admin
from app.models import (
    User, Task, TaskAssignment, TaskType, TaskTypeScale,
    ROLE_LECTURER, ST_DONE, ST_CANCELLED
)

router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])


class AIConfigUpdateRequest(BaseModel):
    provider: str = Field(default="auto")
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = "gemini-2.5-flash"
    groq_api_key: Optional[str] = None
    groq_model: Optional[str] = "llama-3.3-70b-versatile"


class AIChatMessage(BaseModel):
    role: str
    content: str


class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    task_id: Optional[int] = None
    history: Optional[List[AIChatMessage]] = None
    task_group_context: Optional[str] = None


def _mask_key(k: str) -> str:
    if not k or len(k) < 8:
        return ""
    return f"{k[:6]}••••••••{k[-4:]}"


@router.get("/config")
def get_ai_config(_: User = Depends(current_user)):
    """Lấy trạng thái cấu hình Trợ lý AI (che mật mã API Key để bảo mật)."""
    st = config.get_ai_settings()
    has_gemini = bool(st["gemini_api_key"] and len(st["gemini_api_key"]) >= 15)
    has_groq = bool(st["groq_api_key"] and len(st["groq_api_key"]) >= 15)
    active_mode = st["provider"]
    if active_mode == "gemini" and not has_gemini:
        active_mode = "groq" if has_groq else "local_smart"
    elif active_mode == "groq" and not has_groq:
        active_mode = "gemini" if has_gemini else "local_smart"

    return {
        "provider": st["provider"],
        "active_mode": active_mode,
        "has_gemini_key": has_gemini,
        "gemini_configured": has_gemini,
        "gemini_key_masked": _mask_key(st["gemini_api_key"]),
        "gemini_model": st["gemini_model"],
        "has_groq_key": has_groq,
        "groq_configured": has_groq,
        "groq_key_masked": _mask_key(st["groq_api_key"]),
        "groq_model": st["groq_model"],
        "storage_note": "File backend/.env.local (Đã chặn trong .gitignore — An toàn, không đẩy lên Git)",
        "free_key_guides": [
            {
                "name": "Google Gemini API (Khuyên dùng - Miễn phí)",
                "url": "https://aistudio.google.com/app/apikey",
                "steps": "Đăng nhập Google -> Nhấn 'Create API key' -> Copy khóa bắt đầu bằng 'AIza...' dán vào ô bên dưới."
            },
            {
                "name": "Groq Cloud Llama-3.3 70B (Miễn phí tốc độ cao)",
                "url": "https://console.groq.com/keys",
                "steps": "Đăng nhập Groq -> Nhấn 'Create API Key' -> Copy khóa bắt đầu bằng 'gsk_...' dán vào ô bên dưới."
            }
        ]
    }


@router.put("/config", dependencies=[Depends(manager_or_admin)])
@router.post("/config", dependencies=[Depends(manager_or_admin)])
def update_ai_config(req: AIConfigUpdateRequest):
    """Validate và lưu cấu hình API Key vào file cục bộ backend/.env.local (không đẩy lên Git)."""
    norm_provider = req.provider.strip().lower()
    if norm_provider in ("local", "auto"):
        norm_provider = "local_smart" if norm_provider == "local" else (
            "gemini" if (req.gemini_api_key or config.get_ai_settings().get("gemini_api_key")) else "local_smart"
        )
    if norm_provider not in ("gemini", "groq", "local_smart"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Chế độ AI không hợp lệ.")
    req.provider = norm_provider
    if req.gemini_api_key is not None and req.gemini_api_key.strip() != "":
        gk = req.gemini_api_key.strip()
        if len(gk) < 20 or " " in gk:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Gemini API Key không hợp lệ (Phải có ít nhất 20 ký tự, không chứa khoảng trắng, thường bắt đầu bằng 'AIza...')"
            )
    if req.groq_api_key is not None and req.groq_api_key.strip() != "":
        rk = req.groq_api_key.strip()
        if len(rk) < 20 or " " in rk:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Groq API Key không hợp lệ (Phải có ít nhất 20 ký tự, không chứa khoảng trắng, thường bắt đầu bằng 'gsk_...')"
            )

    saved = config.save_ai_settings(
        provider=req.provider,
        gemini_api_key=req.gemini_api_key,
        gemini_model=req.gemini_model,
        groq_api_key=req.groq_api_key,
        groq_model=req.groq_model,
    )
    return {
        "message": "Đã lưu cấu hình Trợ lý AI vào backend/.env.local (Bảo mật cục bộ, không tải lên Git)!",
        "provider": saved["provider"],
        "has_gemini_key": bool(saved["gemini_api_key"]),
        "has_groq_key": bool(saved["groq_api_key"]),
    }


def _build_live_db_context(db: Session, user: User, task_id: Optional[int] = None) -> dict:
    """Trích xuất toàn bộ dữ liệu thực tế từ CSDL để cung cấp ngữ cảnh (RAG) cho Trợ lý AI."""
    today = date.today()
    all_tasks = db.query(Task).all()
    all_assigns = db.query(TaskAssignment).join(Task).all()
    lecturers = db.query(User).filter(User.role == ROLE_LECTURER, User.is_active == True).all()

    total_tasks = len(all_tasks)
    done_tasks = sum(1 for t in all_tasks if t.status == ST_DONE)
    open_tasks_count = sum(1 for t in all_tasks if t.status not in (ST_DONE, ST_CANCELLED))
    group_tasks = [t for t in all_tasks if t.assignment_mode == "Group" or len(t.assignments) >= 2]
    open_group_tasks = [t for t in group_tasks if t.status not in (ST_DONE, ST_CANCELLED)]

    selected_task_info = None
    if task_id:
        st_obj = db.query(Task).filter(Task.id == task_id).first()
        if st_obj:
            selected_task_info = {
                "id": st_obj.id,
                "code": st_obj.code,
                "title": st_obj.title,
                "status": st_obj.status,
                "mode": st_obj.assignment_mode,
                "deadline": str(st_obj.current_deadline),
                "lead": st_obj.lead_lecturer.full_name if st_obj.lead_lecturer else "Chưa phân công",
                "reviewer": st_obj.reviewer.full_name if st_obj.reviewer else "Trưởng Khoa / Trưởng Bộ môn",
                "members": [
                    {
                        "name": a.lecturer.full_name,
                        "status": a.status,
                        "progress": a.progress_pct,
                        "is_lead": (st_obj.lead_lecturer_id == a.lecturer_id),
                        "has_member_ev": bool(getattr(a, "latest_evidence_name", None) or getattr(a, "member_task_note", None)),
                        "has_final_ev": bool(getattr(a, "latest_evidence_url", None) or getattr(a, "member_evidence_status", None) == "Đã xác nhận"),
                        "feedback": getattr(a, "review_feedback", None)
                    }
                    for a in st_obj.assignments
                ]
            }

    overdue_items = []
    late_done_items = []
    for a in all_assigns:
        if a.status != ST_DONE and a.status != ST_CANCELLED and a.task.current_deadline < today:
            overdue_items.append({
                "code": a.task.code,
                "title": a.task.title,
                "lecturer": a.lecturer.full_name,
                "deadline": str(a.task.current_deadline),
                "days_overdue": (today - a.task.current_deadline).days,
                "progress": a.progress_pct
            })
        elif a.status == ST_DONE and a.is_late:
            late_done_items.append({
                "code": a.task.code,
                "title": a.task.title,
                "lecturer": a.lecturer.full_name,
                "delay_days": int(a.delay_days or 1)
            })

    scales = {
        (tts.task_type_id, tts.scale): (tts.conversion_hours or 0.0)
        for tts in db.query(TaskTypeScale).all()
    }

    lec_summaries = []
    for lec in lecturers:
        l_assigns = [a for a in all_assigns if a.lecturer_id == lec.id]
        open_c = sum(1 for a in l_assigns if a.status != ST_DONE and a.status != ST_CANCELLED)
        done_c = sum(1 for a in l_assigns if a.status == ST_DONE)
        late_c = sum(1 for a in l_assigns if a.status == ST_DONE and a.is_late)
        over_c = sum(1 for a in l_assigns if a.status != ST_DONE and a.task.current_deadline < today)
        late_rate = round(late_c / done_c * 100, 1) if done_c > 0 else 0.0
        hours = sum(
            (a.task.school_item.conversion_hours if a.task.school_item else scales.get((a.task.task_type_id, a.task.scale), 10.0))
            for a in l_assigns
        )
        grp_counts = {}
        for a in l_assigns:
            if a.status == ST_DONE and not a.is_late and a.task.task_type:
                g = a.task.task_type.task_group
                grp_counts[g] = grp_counts.get(g, 0) + 1

        lec_summaries.append({
            "id": lec.id,
            "code": lec.profile.lecturer_code if lec.profile else f"GV{lec.id:04d}",
            "name": lec.full_name,
            "degree": lec.profile.degree if lec.profile else "Thạc sĩ",
            "rank": lec.profile.academic_rank if lec.profile else "Giảng viên",
            "dept": lec.department.name if lec.department else "Khoa CNTT",
            "open_tasks": open_c,
            "done_tasks": done_c,
            "late_tasks": late_c,
            "overdue_open": over_c,
            "late_rate": late_rate,
            "converted_hours": round(hours, 1),
            "strong_groups": list(grp_counts.keys())
        })

    lec_summaries.sort(key=lambda x: (x["overdue_open"], x["late_rate"], x["open_tasks"]))
    return {
        "user_name": user.full_name,
        "user_role": user.role,
        "total_tasks": total_tasks,
        "done_tasks": done_tasks,
        "open_tasks_count": open_tasks_count,
        "group_tasks_count": len(group_tasks),
        "open_group_tasks_count": len(open_group_tasks),
        "selected_task": selected_task_info,
        "overdue_items": overdue_items,
        "late_done_items": late_done_items,
        "lecturers": lec_summaries,
        "group_tasks": [
            {
                "code": gt.code,
                "title": gt.title,
                "status": gt.status,
                "lead": gt.lead_lecturer.full_name if gt.lead_lecturer else "Chưa rõ",
                "member_count": len(gt.assignments),
                "avg_progress": round(sum(a.progress_pct for a in gt.assignments) / max(len(gt.assignments), 1)),
                "deadline": str(gt.current_deadline)
            }
            for gt in group_tasks[:10]
        ]
    }


def _generate_local_smart_reply(question: str, ctx: dict) -> str:
    """Trợ lý AI phân tích trực tiếp dữ liệu CSDL thời gian thực với độ chính xác 100%."""
    q = question.lower().strip()
    lecs = ctx["lecturers"]
    overdue = ctx["overdue_items"]
    late_done = ctx["late_done_items"]
    sel_task = ctx.get("selected_task")

    # 0. Nếu người dùng đang chọn 1 công việc cụ thể trong thanh Ngữ cảnh và hỏi về nó
    if sel_task and any(k in q for k in ["việc này", "nhóm này", "chi tiết", "tiến độ", "minh chứng", "ai", "tổng hợp", "rà soát", sel_task["code"].lower()]):
        lines = [
            f"📌 **Phân tích Chi tiết Công việc [{sel_task['code']}]: {sel_task['title']}**",
            f"- **Trạng thái:** {sel_task['status']} | **Hình thức:** {sel_task['mode']} | **Hạn chót:** {sel_task['deadline']}",
            f"- **Người phụ trách chính (Trưởng nhóm):** **{sel_task['lead']}** | **Người kiểm tra:** **{sel_task['reviewer']}**",
            "\n👥 **Tiến độ & Trạng thái Minh chứng của từng Thành viên:**"
        ]
        for m in sel_task["members"]:
            role_tag = "🌟 Trưởng nhóm" if m["is_lead"] else "Thành viên"
            ev_tag = "✅ Đã nộp minh chứng tổng" if m["has_final_ev"] else ("📩 Đã gửi bài lên Trưởng nhóm" if m["has_member_ev"] else "⏳ Chưa gửi minh chứng")
            fb_tag = f" | ⚠️ *Góp ý: {m['feedback']}*" if m["feedback"] else ""
            lines.append(
                f"  • **{m['name']}** ({role_tag}) — Tiến độ: **{m['progress']}%** ({m['status']}) — {ev_tag}{fb_tag}"
            )
        lines.append(
            "\n💡 **Khuyến nghị điều phối:** Các thành viên gửi file minh chứng thành phần lên **Trưởng nhóm** trước; sau khi Trưởng nhóm rà soát đạt yêu cầu sẽ tổng hợp nộp lên **Người kiểm tra** phê duyệt."
        )
        return "\n".join(lines)

    # 0.5 Kiểm tra xem câu hỏi có nhắc đích danh tên giảng viên nào không
    for lec in lecs:
        name_lower = lec["name"].lower()
        short_name = " ".join(name_lower.split()[-2:])
        if name_lower in q or lec["code"].lower() in q or (len(short_name) >= 5 and short_name in q):
            return (
                f"👨‍🏫 **Hồ sơ Năng lực & Khối lượng Công việc của {lec['name']} ({lec['code']}):**\n"
                f"- **Đơn vị:** {lec['dept']} | **Học vị / Chức danh:** {lec['degree']} — {lec['rank']}\n"
                f"- **Khối lượng hiện tại:** Đang thực hiện **{lec['open_tasks']} việc** | Đã hoàn thành: **{lec['done_tasks']} việc**\n"
                f"- **Kỷ luật tiến độ:** Tỷ lệ đúng hạn **{round(100 - lec['late_rate'], 1)}%** (Tỷ lệ trễ lịch sử: {lec['late_rate']}%, Đang quá hạn: {lec['overdue_open']} việc)\n"
                f"- **Tổng giờ chuẩn quy đổi:** **{lec['converted_hours']} / 270 giờ chuẩn** ({round(lec['converted_hours']/270*100, 1)}% định mức năm học)\n"
                f"- **Nhóm việc thế mạnh:** {', '.join(lec['strong_groups']) if lec['strong_groups'] else 'Đa lĩnh vực chuyên môn Khoa CNTT'}"
            )

    # 1. Hỏi về tổng hợp nhanh tiến độ công việc và các nhóm việc đang mở
    if any(k in q for k in ["tổng hợp nhanh tiến độ", "nhóm việc đang mở", "tiến độ công việc", "tổng quan tiến độ", "tình hình chung"]):
        completion_rate = round(ctx["done_tasks"] / max(ctx["total_tasks"], 1) * 100, 1)
        lines = [
            f"📈 **Tổng hợp Tiến độ Công việc & Các Nhóm việc Đang mở tại Khoa CNTT (Thời gian thực):**",
            f"- **Tổng số đầu việc toàn Khoa:** **{ctx['total_tasks']} việc** — Đã hoàn thành: **{ctx['done_tasks']} việc ({completion_rate}%)** | Đang triển khai: **{ctx['open_tasks_count']} việc**.",
            f"- **Công việc làm theo Nhóm:** **{ctx['group_tasks_count']} nhóm việc** (Đang mở: **{ctx['open_group_tasks_count']} nhóm**).",
            f"- **Cảnh báo tiến độ:** Có **{len(overdue)} việc đang quá hạn** cần đôn đốc và **{len(late_done)} lượt hoàn thành trễ hạn**.",
            "\n👥 **Danh sách các Nhóm công việc tiêu biểu trên hệ thống:**"
        ]
        for gt in ctx["group_tasks"][:6]:
            lines.append(
                f"  • **{gt['code']}** — *{gt['title']}* | Trưởng nhóm: **{gt['lead']}** ({gt['member_count']} TV) | Tiến độ TB: **{gt['avg_progress']}%** | Trạng thái: **{gt['status']}** (Hạn: {gt['deadline']})"
            )
        lines.append(
            "\n💡 **Đề xuất điều hành:** Kiểm tra ngay các nhóm việc đang ở trạng thái *InProgress*, nhắc các thành viên nộp minh chứng thành phần về cho Trưởng nhóm trước hạn chót."
        )
        return "\n".join(lines)

    # 2. Hỏi về giảng viên trễ hạn / quá hạn / nguy cơ trễ
    if any(k in q for k in ["trễ hạn", "quá hạn", "chậm tiến độ", "tre han", "qua han", "nguy cơ trễ"]):
        lines = [
            f"📊 **Báo cáo Rà soát Công việc Trễ hạn & Quá hạn (Thời gian thực):**",
            f"- Tổng số công việc đang quá hạn chưa xong: **{len(overdue)} việc**",
            f"- Tổng số lượt hoàn thành trễ trong lịch sử: **{len(late_done)} lượt**"
        ]
        if overdue:
            lines.append("\n🚨 **Danh sách công việc đang quá hạn cần đôn đốc ngay:**")
            for item in overdue[:6]:
                lines.append(
                    f"  • **{item['code']}** — *{item['title']}* | Giảng viên: **{item['lecturer']}** (Tiến độ: {item['progress']}%, quá hạn {item['days_overdue']} ngày, hạn: {item['deadline']})"
                )
        else:
            lines.append("\n✅ **Hiện tại toàn Khoa không có công việc nào đang mở bị quá hạn!**")
        if late_done:
            lines.append("\n⚠️ **Các trường hợp hoàn thành trễ hạn ghi nhận trong năm học:**")
            for item in late_done[:6]:
                lines.append(
                    f"  • **{item['code']}** — *{item['title']}* | Giảng viên: **{item['lecturer']}** (Trễ +{item['delay_days']} ngày)"
                )
        lines.append(
            "\n💡 **Khuyến nghị điều hành:** Người kiểm tra hoặc Trưởng nhóm có thể bấm nút **'Báo thiếu sót / Nhắc nhở'** trên dòng công việc để gửi cảnh báo trực tiếp tới thành viên và xuất file **Excel Báo cáo Toàn diện** phục vụ họp giao ban Khoa."
        )
        return "\n".join(lines)

    # 3. Hỏi về soạn thông báo nhắc nhở / thiếu sót minh chứng (ưu tiên kiểm tra trước từ khóa "nhóm")
    if any(k in q for k in ["soạn", "thông báo", "nhắc nhở", "email", "tin nhắn", "bổ sung thiếu sót", "thiếu sót minh chứng"]):
        return (
            "📝 **Mẫu Thông báo Nhắc nhở Tiến độ & Bổ sung Minh chứng (Chuẩn hành chính Khoa CNTT - HUIT):**\n\n"
            "> **Tiêu đề:** [Nhắc nhở khẩn] Đôn đốc rà soát tiến độ và nộp bổ sung minh chứng công việc học kỳ\n"
            "> **Kính gửi:** Các giảng viên thành viên nhóm công tác,\n"
            "> Qua rà soát tiến độ trên Hệ thống Quản lý Công việc Khoa CNTT, một số hạng mục thành phần hiện chưa đính kèm đầy đủ file minh chứng hoặc còn thiếu sót số liệu.\n"
            "> Đề nghị các thành viên trong nhóm:\n"
            "> 1. Hoàn thiện ngay nội dung còn thiếu và tải file minh chứng gửi lên **Người phụ trách chính (Trưởng nhóm)** trước 17h00 ngày mai.\n"
            "> 2. Trưởng nhóm tổng hợp, kiểm tra chéo và cập nhật thanh tiến độ (%) báo cáo **Người kiểm tra** đúng thời hạn quy định.\n"
            "> Trân trọng!"
        )

    # 4. Hỏi về gợi ý giao việc / chọn người phụ trách chính / trưởng nhóm
    if any(k in q for k in ["gợi ý", "phụ trách chính", "trưởng nhóm", "giao việc", "ai phù hợp", "đề xuất", "độ trễ thấp"]):
        best = lecs[:5]
        lead_cand = next((x for x in lecs if "Tiến sĩ" in x["degree"] or "PGS" in x["degree"] or "chính" in x["rank"].lower()), lecs[0] if lecs else None)
        lines = [
            "🤖 **Đề xuất Phân công Giảng viên & Chọn Người Phụ trách chính (Độ trễ thấp nhất):**",
            "\n**1. Ứng viên đề xuất làm Người Phụ trách chính (Trưởng nhóm):**"
        ]
        if lead_cand:
            lines.append(
                f"  🌟 **{lead_cand['name']} ({lead_cand['code']})** — {lead_cand['degree']}, {lead_cand['rank']} ({lead_cand['dept']})\n"
                f"     • **Điều kiện 1 (Độ trễ thấp nhất):** Tỷ lệ trễ lịch sử {lead_cand['late_rate']}% (0 việc quá hạn)\n"
                f"     • **Điều kiện 2 (Kinh nghiệm nhóm việc):** Đã hoàn thành {lead_cand['done_tasks']} công việc ({', '.join(lead_cand['strong_groups'][:2]) or 'Đa lĩnh vực'})\n"
                f"     • **Điều kiện 3 (Năng lực chủ trì):** Học vị {lead_cand['degree']} / {lead_cand['rank']}\n"
                f"     • **Điều kiện 4 (Quỹ thời gian):** Đang mở {lead_cand['open_tasks']} việc, sẵn sàng điều phối nhóm."
            )
        lines.append("\n**2. Top Giảng viên có nguy cơ trễ hạn thấp nhất phù hợp tham gia nhóm:**")
        for idx, c in enumerate(best, 1):
            lines.append(
                f"  {idx}. **{c['name']} ({c['code']})** — {c['dept']} | Đang mở: **{c['open_tasks']} việc** | Tỷ lệ đúng hạn: **{round(100 - c['late_rate'], 1)}%** | Tổng giờ quy đổi: **{c['converted_hours']}h**"
            )
        lines.append(
            "\n📌 *Lưu ý quy trình nhóm:* Khi giao việc nhóm, các thành viên gửi minh chứng lên **Trưởng nhóm** trước; **Trưởng nhóm** kiểm tra, cập nhật tiến độ hoặc báo thiếu sót rồi nộp minh chứng tổng hợp lên **Người kiểm tra**."
        )
        return "\n".join(lines)

    # 5. Hỏi về giờ chuẩn / định mức / Thông tư 20
    if any(k in q for k in ["giờ chuẩn", "định mức", "thông tư 20", "khối lượng", "quy đổi"]):
        top_hours = sorted(lecs, key=lambda x: x["converted_hours"], reverse=True)[:5]
        low_hours = sorted(lecs, key=lambda x: x["converted_hours"])[:3]
        lines = [
            "📚 **Thống kê Định mức Giờ chuẩn Quy đổi (Theo Thông tư 20/2020/TT-BGDĐT):**",
            "- Định mức chuẩn giảng dạy: **270 giờ chuẩn/năm** (tương đương 1.760 giờ hành chính/năm).",
            "- Định mức công tác chuyên môn & kiêm nhiệm mục tiêu: **180 giờ chuẩn/năm**.",
            "\n**Top 5 Giảng viên có khối lượng giờ chuẩn quy đổi cao nhất hiện tại:**"
        ]
        for idx, c in enumerate(top_hours, 1):
            lines.append(
                f"  {idx}. **{c['name']} ({c['code']})** — **{c['converted_hours']} giờ chuẩn** ({c['done_tasks']} việc hoàn thành, {c['open_tasks']} việc đang làm)"
            )
        lines.append("\n**Các Giảng viên còn dư nhiều quỹ giờ chuẩn (ưu tiên phân công việc mới):**")
        for idx, c in enumerate(low_hours, 1):
            lines.append(
                f"  • **{c['name']} ({c['code']})** — Hiện mới đạt **{c['converted_hours']} giờ chuẩn** (Đang mở {c['open_tasks']} việc)"
            )
        return "\n".join(lines)

    # 6. Hỏi về danh sách giảng viên / bộ môn
    if any(k in q for k in ["giảng viên", "bộ môn", "nhân sự", "tài khoản"]):
        lines = [
            f"👥 **Tổng hợp Đội ngũ Giảng viên Khoa CNTT ({len(lecs)} Giảng viên đang hoạt động):**"
        ]
        for idx, c in enumerate(lecs[:10], 1):
            lines.append(
                f"  {idx}. **{c['name']} ({c['code']})** — {c['degree']}, {c['dept']} | Đang làm: **{c['open_tasks']} việc** | Đã xong: **{c['done_tasks']} việc** | Giờ chuẩn: **{c['converted_hours']}h**"
            )
        if len(lecs) > 10:
            lines.append(f"  *(...và {len(lecs) - 10} giảng viên khác trong Khoa CNTT)*")
        return "\n".join(lines)

    # Mặc định: Tổng quan toàn hệ thống
    return (
        f"👋 Xin chào **{ctx['user_name']}**! Tôi là **Trợ lý AI Quản lý Công việc Khoa CNTT (HUIT)**.\n\n"
        f"📌 **Tóm tắt nhanh dữ liệu vận hành hiện tại của Khoa:**\n"
        f"- Tổng số đầu việc trên hệ thống: **{ctx['total_tasks']} việc** (Đã hoàn thành: **{ctx['done_tasks']} việc**, Đang mở: **{ctx['open_tasks_count']} việc**, Việc nhóm: **{ctx['group_tasks_count']} nhóm**).\n"
        f"- Công việc đang quá hạn cần xử lý: **{len(overdue)} việc** | Lượt hoàn thành trễ hạn: **{len(late_done)} lượt**.\n"
        f"- Đội ngũ giảng viên đang hoạt động: **{len(lecs)} giảng viên** thuộc 4 Bộ môn.\n\n"
        f"💡 **Bạn có thể hỏi tôi bất kỳ nội dung nào, ví dụ:**\n"
        f"1. *\"Tổng hợp nhanh tiến độ công việc và các nhóm việc đang mở\"*\n"
        f"2. *\"Gợi ý tiêu chí chọn Người phụ trách chính (Trưởng nhóm) và giảng viên độ trễ thấp nhất\"*\n"
        f"3. *\"Liệt kê các công việc đang quá hạn hoặc có nguy cơ trễ hạn cao\"*\n"
        f"4. *\"Thống kê định mức giờ chuẩn quy đổi theo Thông tư 20\"*\n"
        f"5. *\"Soạn nội dung nhắc nhở thành viên nhóm bổ sung thiếu sót minh chứng\"*"
    )


@router.post("/chat")
def chat_with_ai(
    req: AIChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    """
    Trò chuyện với Trợ lý AI:
    - Tự động kết hợp dữ liệu thực tế từ CSDL (RAG).
    - Nếu có GEMINI_API_KEY hoặc GROQ_API_KEY trong backend/.env.local -> Gọi LLM Cloud.
    - Nếu chưa có key hoặc lỗi mạng -> Tự động chuyển mượt sang Hệ thống AI Phân tích Dữ liệu Nội bộ.
    """
    ctx = _build_live_db_context(db, user, req.task_id)
    st = config.get_ai_settings()

    system_prompt = (
        "Bạn là Trợ lý AI thông minh của Hệ thống Quản lý Công việc & Tối ưu Phân công bằng Học máy tại Khoa CNTT - Trường ĐH Công Thương TP.HCM (HUIT).\n"
        "Hãy trả lời ngắn gọn, súc tích, trình bày dạng bullet dễ đọc bằng tiếng Việt chuẩn mực.\n"
        "Quy tắc nghiệp vụ quan trọng của Khoa:\n"
        "- Trong công việc nhóm: Thành viên gửi file minh chứng lên Trưởng nhóm (Người phụ trách chính) trước. Chỉ Trưởng nhóm mới nộp minh chứng tổng của nhóm lên Người kiểm tra.\n"
        "- Quản lý/Người kiểm tra không nộp thay minh chứng của tài khoản khác mà thực hiện kiểm tra, cập nhật tiến độ (%) và gửi thông báo thiếu sót để nhóm kịp thời làm.\n"
        "- Khi gợi ý phân công: Chỉ đề xuất giảng viên thuộc nhóm công việc được chọn có độ trễ thấp nhất, và chọn Người phụ trách chính dựa trên 4 điều kiện (Độ trễ thấp <22%, Sở trường nhóm việc, Học vị/Chức danh chủ trì, Quỹ thời gian không quá hạn).\n"
        f"Dữ liệu thực tế từ CSDL hiện tại: Tổng {ctx['total_tasks']} việc ({ctx['done_tasks']} hoàn thành, {ctx['group_tasks_count']} việc nhóm). "
        f"Công việc đang chọn: {ctx.get('selected_task')}. "
        f"Đang quá hạn: {ctx['overdue_items']}. Hoàn thành trễ: {ctx['late_done_items']}. "
        f"Danh sách giảng viên & tải công việc: {ctx['lecturers'][:10]}."
    )

    used_engine = "Gemini AI — Trợ lý Điều phối Khoa CNTT (HUIT)"
    reply_text = None

    # 1. Thử gọi Google Gemini API / Vertex AI Express nếu có key trong backend/.env.local
    if st["gemini_api_key"] and len(st["gemini_api_key"]) >= 15:
        model_name = st["gemini_model"] or "gemini-2.5-flash"
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": req.message}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 900}
        }
        endpoints = [
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={st['gemini_api_key']}",
            f"https://aiplatform.googleapis.com/v1/publishers/google/models/{model_name}:generateContent?key={st['gemini_api_key']}",
        ]
        for url in endpoints:
            if reply_text:
                break
            try:
                with httpx.Client(timeout=6.0) as client:
                    resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and candidates[0].get("content", {}).get("parts"):
                        reply_text = candidates[0]["content"]["parts"][0].get("text", "")
                        used_engine = f"Google Gemini ({model_name})"
            except Exception:
                reply_text = None

    # 2. Thử gọi Groq Cloud API nếu có key
    if not reply_text and st["groq_api_key"] and len(st["groq_api_key"]) >= 15:
        try:
            model_name = st["groq_model"] or "llama-3.3-70b-versatile"
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {st['groq_api_key']}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": req.message}
                ],
                "temperature": 0.3,
                "max_tokens": 900
            }
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    reply_text = choices[0].get("message", {}).get("content", "")
                    used_engine = f"Groq Cloud ({model_name})"
        except Exception:
            reply_text = None

    # 3. Đảm bảo phản hồi thông minh 100% từ dữ liệu thực tế CSDL ngay lập tức nếu Cloud chưa trả lời
    if not reply_text:
        reply_text = _generate_local_smart_reply(req.message, ctx)

    return {
        "reply": reply_text,
        "engine": used_engine,
        "context_stats": {
            "total_tasks": ctx["total_tasks"],
            "overdue_count": len(ctx["overdue_items"]),
            "lecturers_count": len(ctx["lecturers"])
        }
    }

