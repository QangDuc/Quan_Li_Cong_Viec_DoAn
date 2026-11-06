import React, { useEffect, useState } from "react";
import {
  CheckSquare,
  CalendarPlus,
  Check,
  X,
  Search,
  FileDown,
  Upload,
  FileText,
  Users,
  AlertCircle,
  ShieldCheck,
  UserCheck,
  Eye,
  BellRing,
} from "lucide-react";

import { API_BASE } from "../types";
import {
  calculateProjectProgressFromMembers,
  evaluateTaskRoleAndVisibility,
  filterTasksByRoleAndDepartment,
} from "../rbacWorkflow";

const BACKEND_ORIGIN = API_BASE.replace(/\/api$/, "");

interface Props {
  token: string;
  currentUser: any;
  tasks: any[];
  schoolCatalog: any[];
  users?: any[];
  onRefresh: () => void;
}

export const TasksAndExtensionsView: React.FC<Props> = ({
  token,
  currentUser,
  tasks,
  schoolCatalog,
  onRefresh,
}) => {
  const [subView, setSubView] = useState<"tasks" | "extensions">("tasks");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [search, setSearch] = useState<string>("");
  const [extensions, setExtensions] = useState<any[]>([]);
  const [actionMsg, setActionMsg] = useState<{ type: "ok" | "err"; text: string } | null>(
    null
  );

  // Modal 1: Cập nhật tiến độ (%) & Nộp minh chứng chính thức (Chỉ Trưởng nhóm nộp minh chứng; Người kiểm tra/Trưởng nhóm cập nhật %)
  const [progTask, setProgTask] = useState<any | null>(null);
  const [progLecturerId, setProgLecturerId] = useState<number | null>(null);
  const [progPct, setProgPct] = useState<number>(50);
  const [progNote, setProgNote] = useState<string>("");
  const [evidenceFileName, setEvidenceFileName] = useState<string>("");
  const [evidenceFileUrl, setEvidenceFileUrl] = useState<string>("");
  const [uploadingFile, setUploadingFile] = useState<boolean>(false);

  // Modal 1b: Thành viên nhóm gửi minh chứng lên Trưởng nhóm trước
  const [memberEvTask, setMemberEvTask] = useState<any | null>(null);
  const [memberEvNote, setMemberEvNote] = useState<string>("");
  const [memberEvFileName, setMemberEvFileName] = useState<string>("");
  const [memberEvFileUrl, setMemberEvFileUrl] = useState<string>("");

  // Modal 1c: Người kiểm tra / Trưởng nhóm thông báo thiếu sót để nhóm kịp thời làm
  const [feedbackTask, setFeedbackTask] = useState<any | null>(null);
  const [feedbackLecturerId, setFeedbackLecturerId] = useState<number | "">("");
  const [feedbackContent, setFeedbackContent] = useState<string>("");
  const [feedbackProgressPct, setFeedbackProgressPct] = useState<number | "">("");

  // Modal 2: Phân việc cho thành viên hiện có trong nhóm (ĐÃ BỎ phần thêm giảng viên ngoài nhóm)
  const [delegateTask, setDelegateTask] = useState<any | null>(null);
  const [delegateLeadId, setDelegateLeadId] = useState<number | null>(null);
  const [delegateMembers, setDelegateMembers] = useState<
    { lecturer_id: number; lecturer_name: string; member_task_note: string }[]
  >([]);

  // Modal 3: Xin gia hạn
  const [extTask, setExtTask] = useState<any | null>(null);
  const [proposedDeadline, setProposedDeadline] = useState<string>("");
  const [extReason, setExtReason] = useState<string>("");

  // Modal 4: Ánh xạ việc Trường
  const [mapTask, setMapTask] = useState<any | null>(null);
  const [selectedSchoolId, setSelectedSchoolId] = useState<number>(
    schoolCatalog[0]?.id || 1
  );

  // Modal 5: Chi tiết & Nhật ký tiến độ
  const [detailData, setDetailData] = useState<any | null>(null);

  const deptHeadDeptId = currentUser?.department_id
    ? Number(currentUser.department_id)
    : null;

  // Modal 6: Trưởng nhóm (Người phụ trách chính) phê duyệt tiến độ thành viên & gửi hệ thống tự tính % dự án
  const [leadApproveTask, setLeadApproveTask] = useState<any | null>(null);
  const [leadMemberDecisions, setLeadMemberDecisions] = useState<
    Record<number, { approval_status: string; review_note: string }>
  >({});
  const [leadDecisionNote, setLeadDecisionNote] = useState<string>("");

  // Modal 7: Người kiểm tra quan sát tiến độ từng thành viên & phê duyệt quyết định của Trưởng nhóm
  const [reviewerApproveTask, setReviewerApproveTask] = useState<any | null>(null);
  const [reviewerDecisionStatus, setReviewerDecisionStatus] = useState<string>(
    "Đã phê duyệt quyết định Trưởng nhóm"
  );
  const [reviewerDecisionNote, setReviewerDecisionNote] = useState<string>("");

  useEffect(() => {
    fetchExtensions();
  }, [tasks]);

  const fetchExtensions = async () => {
    try {
      const res = await fetch(`${API_BASE}/tasks/extensions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setExtensions(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const openDetail = async (taskId: number) => {
    try {
      const res = await fetch(`${API_BASE}/tasks/${taskId}/detail`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setDetailData(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const uploadFileHelper = async (
    file: File,
    onSuccess: (name: string, url: string) => void
  ) => {
    setUploadingFile(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_BASE}/tasks/upload-evidence`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        onSuccess(data.file_name || file.name, data.file_url || "");
      } else {
        setActionMsg({
          type: "err",
          text: data.detail || "Không thể tải file minh chứng",
        });
      }
    } catch {
      setActionMsg({ type: "err", text: "Lỗi kết nối khi tải file minh chứng" });
    } finally {
      setUploadingFile(false);
    }
  };

  // Kiểm tra quyền trên từng công việc theo mô hình RBAC 5 cấp & Phạm vi Bộ môn
  const getTaskRoleInfo = (t: any) => {
    const isGroup =
      t.assignment_mode === "Group" || (t.assignees?.length || 0) >= 2;
    const evalRole = evaluateTaskRoleAndVisibility(
      currentUser,
      t,
      "AUTO",
      deptHeadDeptId
    );
    const myAssign =
      evalRole.targetSelfAssignee ||
      t.assignees?.find((a: any) => a.lecturer_id === currentUser?.id);
    const isUserLead =
      evalRole.effectiveRole === "GROUP_LEAD" ||
      t.lead_lecturer_id === currentUser?.id ||
      Boolean(myAssign?.is_lead);
    const isSingleAssignee = !isGroup && Boolean(myAssign);
    const canSubmitOfficialEvidence = evalRole.canSelfUpdateProgress;
    const isRegularGroupMember = isGroup && evalRole.effectiveRole === "MEMBER";
    const isReviewerOrManager =
      evalRole.effectiveRole === "REVIEWER" ||
      evalRole.effectiveRole === "DEPT_HEAD" ||
      evalRole.effectiveRole === "DEAN";
    const canUpdateProgress = evalRole.canSelfUpdateProgress;
    const canSendFeedback =
      evalRole.effectiveRole === "GROUP_LEAD" ||
      evalRole.effectiveRole === "REVIEWER";
    const canDelegate = isGroup && evalRole.effectiveRole === "GROUP_LEAD";

    return {
      isGroup,
      myAssign,
      isUserLead,
      isSingleAssignee,
      canSubmitOfficialEvidence,
      isRegularGroupMember,
      isReviewerOrManager,
      canUpdateProgress,
      canSendFeedback,
      canDelegate,
      ...evalRole,
    };
  };

  const openProgressModal = (t: any) => {
    setProgTask(t);
    const roleInfo = getTaskRoleInfo(t);
    const target = roleInfo.targetSelfAssignee || t.assignees?.[0];
    setProgLecturerId(target ? target.lecturer_id : currentUser?.id);
    setProgPct(target?.progress_pct ?? 50);
    setProgNote("");
    setEvidenceFileName(target?.latest_evidence_name || "");
    setEvidenceFileUrl(target?.latest_evidence_url || "");
  };

  const openLeadApproveModal = (t: any) => {
    setLeadApproveTask(t);
    const initMap: Record<number, { approval_status: string; review_note: string }> = {};
    (t.assignees || []).forEach((a: any) => {
      initMap[a.lecturer_id] = {
        approval_status:
          a.lead_approval_status === "Yêu cầu chỉnh sửa"
            ? "Yêu cầu chỉnh sửa"
            : "Trưởng nhóm đã duyệt",
        review_note: "",
      };
    });
    setLeadMemberDecisions(initMap);
    const autoPct = calculateProjectProgressFromMembers(t.assignees, t.progress_pct);
    setLeadDecisionNote(
      `Đã rà soát và phê duyệt kết quả thực hiện của các thành viên trong nhóm (Tiến độ dự án: ${autoPct}%).`
    );
  };

  const handleSaveLeadApproval = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!leadApproveTask) return;
    const member_approvals = (leadApproveTask.assignees || []).map((a: any) => ({
      lecturer_id: a.lecturer_id,
      approval_status:
        leadMemberDecisions[a.lecturer_id]?.approval_status || "Trưởng nhóm đã duyệt",
      review_note: leadMemberDecisions[a.lecturer_id]?.review_note || "",
    }));
    const res = await fetch(`${API_BASE}/tasks/${leadApproveTask.id}/lead-approve`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        member_approvals,
        submit_to_reviewer: true,
        lead_decision_note: leadDecisionNote,
      }),
    });
    const data = await res.json();
    if (res.ok) {
      setActionMsg({
        type: "ok",
        text: data.message || "Đã phê duyệt tiến độ các thành viên trong nhóm.",
      });
      setLeadApproveTask(null);
      onRefresh();
    } else {
      setActionMsg({
        type: "err",
        text: data.detail || "Không thể phê duyệt tiến độ nhóm",
      });
    }
  };

  const openReviewerApproveModal = (t: any) => {
    setReviewerApproveTask(t);
    setReviewerDecisionStatus("Đã phê duyệt quyết định Trưởng nhóm");
    const autoPct = calculateProjectProgressFromMembers(t.assignees, t.progress_pct);
    setReviewerDecisionNote(
      `Đã kiểm tra kết quả của các thành viên và thống nhất với quyết định phê duyệt của Trưởng nhóm (${autoPct}%).`
    );
  };

  const handleSaveReviewerApproval = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewerApproveTask) return;
    const res = await fetch(
      `${API_BASE}/tasks/${reviewerApproveTask.id}/reviewer-approve`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          approval_status: reviewerDecisionStatus,
          reviewer_decision_note: reviewerDecisionNote,
        }),
      }
    );
    const data = await res.json();
    if (res.ok) {
      setActionMsg({
        type: "ok",
        text:
          data.message ||
          "Người kiểm tra đã phê duyệt quyết định của Trưởng nhóm thành công!",
      });
      setReviewerApproveTask(null);
      onRefresh();
    } else {
      setActionMsg({
        type: "err",
        text: data.detail || "Không thể phê duyệt quyết định Trưởng nhóm",
      });
    }
  };

  const handleSaveProgress = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!progTask) return;

    const payload: any = {
      progress_pct: progPct,
      note: progNote,
      lecturer_id: progLecturerId,
      evidence_file_name: evidenceFileName || null,
      evidence_file_url: evidenceFileUrl || null,
    };

    const res = await fetch(`${API_BASE}/tasks/${progTask.id}/progress`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (res.ok) {
      setActionMsg({
        type: "ok",
        text:
          data.message ||
          `Đã cập nhật tiến độ đạt ${progPct}%.`,
      });
      setProgTask(null);
      setProgNote("");
      onRefresh();
    } else {
      setActionMsg({
        type: "err",
        text: data.detail || "Không thể cập nhật tiến độ",
      });
    }
  };

  const handleSubmitMemberEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!memberEvTask) return;
    if (!memberEvFileName) {
      setActionMsg({
        type: "err",
        text: "Vui lòng đính kèm file minh chứng trước khi gửi lên Trưởng nhóm.",
      });
      return;
    }
    const res = await fetch(
      `${API_BASE}/tasks/${memberEvTask.id}/member-evidence`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          note: memberEvNote,
          evidence_file_name: memberEvFileName,
          evidence_file_url: memberEvFileUrl,
        }),
      }
    );
    const data = await res.json();
    if (res.ok) {
      setActionMsg({
        type: "ok",
        text:
          data.message ||
          "Đã gửi minh chứng thành viên lên Trưởng nhóm chờ kiểm duyệt!",
      });
      setMemberEvTask(null);
      onRefresh();
    } else {
      setActionMsg({
        type: "err",
        text: data.detail || "Không thể gửi minh chứng lên Trưởng nhóm",
      });
    }
  };

  const openFeedbackModal = (t: any, defaultLecturerId?: number) => {
    setFeedbackTask(t);
    setFeedbackLecturerId(defaultLecturerId ?? "");
    setFeedbackContent("");
    if (defaultLecturerId) {
      const found = t.assignees?.find(
        (a: any) => a.lecturer_id === defaultLecturerId
      );
      setFeedbackProgressPct(found ? found.progress_pct : "");
    } else {
      setFeedbackProgressPct("");
    }
  };

  const handleSendFeedback = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedbackTask) return;
    const res = await fetch(`${API_BASE}/tasks/${feedbackTask.id}/feedback`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        lecturer_id:
          feedbackLecturerId === "" ? null : Number(feedbackLecturerId),
        feedback: feedbackContent,
        progress_pct:
          feedbackProgressPct === "" ? null : Number(feedbackProgressPct),
        mark_status: "Cần bổ sung",
      }),
    });
    const data = await res.json();
    if (res.ok) {
      setActionMsg({
        type: "ok",
        text:
          data.message ||
          "Đã gửi thông báo nhắc nhở thiếu sót tới các thành viên nhóm!",
      });
      setFeedbackTask(null);
      onRefresh();
    } else {
      setActionMsg({
        type: "err",
        text: data.detail || "Không thể gửi thông báo thiếu sót",
      });
    }
  };

  const openDelegateModal = (t: any) => {
    setDelegateTask(t);
    setDelegateLeadId(
      t.lead_lecturer_id || t.assignees?.[0]?.lecturer_id || null
    );
    setDelegateMembers(
      (t.assignees || []).map((a: any) => ({
        lecturer_id: a.lecturer_id,
        lecturer_name: a.lecturer_name,
        member_task_note: a.member_task_note || "",
      }))
    );
  };

  const handleSaveDelegate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!delegateTask) return;
    const res = await fetch(`${API_BASE}/tasks/${delegateTask.id}/delegate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        lead_lecturer_id: delegateLeadId,
        members: delegateMembers.map((m) => ({
          lecturer_id: m.lecturer_id,
          member_task_note: m.member_task_note,
        })),
      }),
    });
    const data = await res.json();
    if (res.ok) {
      setActionMsg({
        type: "ok",
        text: data.message || "Đã cập nhật phân công nhiệm vụ trong nhóm",
      });
      setDelegateTask(null);
      onRefresh();
    } else {
      setActionMsg({
        type: "err",
        text: data.detail || "Không thể lưu phân việc nhóm",
      });
    }
  };

  const handleRequestExtension = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!extTask) return;
    const res = await fetch(`${API_BASE}/tasks/${extTask.id}/extensions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        proposed_deadline: proposedDeadline,
        reason: extReason,
      }),
    });
    const data = await res.json();
    if (res.ok) {
      setActionMsg({
        type: "ok",
        text: `Đã gửi yêu cầu xin gia hạn cho công việc ${extTask.code}`,
      });
      setExtTask(null);
      setExtReason("");
      fetchExtensions();
      onRefresh();
    } else {
      setActionMsg({
        type: "err",
        text: data.detail || "Lỗi gửi yêu cầu gia hạn",
      });
    }
  };

  const isActingAsDeptHead =
    currentUser?.role === "manager" &&
    currentUser?.department_id !== null &&
    currentUser?.department_id !== undefined;

  const handleReviewExtension = async (extId: number, statusDecision: string) => {
    const res = await fetch(`${API_BASE}/tasks/extensions/${extId}/review`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        status: statusDecision,
        acting_dept_head_department_id: isActingAsDeptHead ? deptHeadDeptId : null,
        review_note:
          statusDecision === "Đã duyệt"
            ? "Đồng ý gia hạn và cập nhật lại hạn hoàn thành"
            : "Không đồng ý gia hạn, yêu cầu bám sát tiến độ gốc",
      }),
    });
    const data = await res.json();
    if (res.ok) {
      setActionMsg({
        type: "ok",
        text: data.message || `Đã ${statusDecision} yêu cầu gia hạn`,
      });
      fetchExtensions();
      onRefresh();
    } else {
      setActionMsg({
        type: "err",
        text: data.detail || "Không thể duyệt yêu cầu gia hạn",
      });
    }
  };

  const handleMapSchool = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mapTask) return;
    const res = await fetch(
      `${API_BASE}/reports/school-catalog/map-task?task_id=${mapTask.id}&school_catalog_id=${selectedSchoolId}`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    const data = await res.json();
    if (res.ok) {
      setActionMsg({ type: "ok", text: data.message });
      setMapTask(null);
      onRefresh();
    } else {
      setActionMsg({
        type: "err",
        text: data.detail || "Không thể ánh xạ danh mục Trường",
      });
    }
  };

  const handleExportLateExcel = async () => {
    const res = await fetch(`${API_BASE}/reports/export-late-excel`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `DanhSach_GiangVien_TreHan_HUIT_${new Date()
        .toISOString()
        .slice(0, 10)}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
    } else {
      setActionMsg({
        type: "err",
        text: "Không thể xuất file Excel danh sách trễ hạn",
      });
    }
  };

  const todayStr = new Date().toISOString().slice(0, 10);
  const isTaskLateOrOverdue = (t: any) => {
    const hasLateDone = t.assignees?.some((a: any) => a.is_late === true);
    const isOverdueOpen =
      t.status !== "Hoàn thành" &&
      t.current_deadline &&
      String(t.current_deadline) < todayStr;
    return Boolean(hasLateDone || isOverdueOpen);
  };

  const isGroupTask = (t: any) =>
    t.assignment_mode === "Group" || (t.assignees?.length || 0) >= 2;

  // Lọc công việc & gia hạn theo phạm vi Bộ môn nếu đang ở vai trò Trưởng Bộ môn (DEPT_HEAD)
  const roleScopedTasks = filterTasksByRoleAndDepartment(
    tasks,
    currentUser,
    "AUTO",
    deptHeadDeptId
  );

  const scopedExtensions = isActingAsDeptHead
    ? extensions.filter(
        (e) => Number(e.department_id || 1) === Number(deptHeadDeptId)
      )
    : extensions;

  const countAll = roleScopedTasks.length;
  const countGroup = roleScopedTasks.filter(isGroupTask).length;
  const countDoing = roleScopedTasks.filter(
    (t) => t.status === "Đang thực hiện" || t.status === "Mới giao"
  ).length;
  const countDone = roleScopedTasks.filter((t) => t.status === "Hoàn thành").length;
  const countLate = roleScopedTasks.filter(isTaskLateOrOverdue).length;
  const pendingExtCount = scopedExtensions.filter((e) => e.status === "Chờ duyệt").length;

  const filteredTasks = roleScopedTasks.filter((t) => {
    if (statusFilter === "GROUP") {
      if (!isGroupTask(t)) return false;
    } else if (statusFilter === "DOING") {
      if (t.status !== "Đang thực hiện" && t.status !== "Mới giao") return false;
    } else if (statusFilter === "LATE") {
      if (!isTaskLateOrOverdue(t)) return false;
    } else if (statusFilter !== "ALL" && t.status !== statusFilter) {
      return false;
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchTitle =
        t.title?.toLowerCase().includes(q) || t.code?.toLowerCase().includes(q);
      const matchAssignee = t.assignees?.some((a: any) =>
        a.lecturer_name?.toLowerCase().includes(q)
      );
      if (!matchTitle && !matchAssignee) return false;
    }
    return true;
  });

  return (
    <div className="space-y-4">
      {/* THANH ĐIỀU HƯỚNG VIEW & BỘ LỌC CÔNG VIỆC CHỐNG NHẢY BỐ CỤC */}
      <div className="bg-white p-3.5 rounded-2xl border border-slate-200 shadow-2xs space-y-3">
        {/* HÀNG 1: CHUYỂN ĐỔI CHẾ ĐỘ VIEW (CÔNG VIỆC / DUYỆT GIA HẠN / DS TRỄ) */}
        <div className="flex flex-wrap items-center justify-between gap-2.5 pb-2.5 border-b border-slate-100">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setSubView("tasks")}
              className={`h-9 flex items-center gap-2 px-3.5 rounded-xl text-xs font-bold border cursor-pointer transition ${
                subView === "tasks"
                  ? "bg-blue-600 text-white border-blue-600 shadow-xs"
                  : "bg-slate-100 text-slate-700 border-slate-200/80 hover:bg-slate-200"
              }`}
            >
              <CheckSquare className="w-4 h-4 shrink-0" />
              Công việc ({countAll})
            </button>

            <button
              type="button"
              onClick={() => setSubView("extensions")}
              className={`h-9 flex items-center gap-2 px-3.5 rounded-xl text-xs font-bold border cursor-pointer transition ${
                subView === "extensions"
                  ? "bg-blue-600 text-white border-blue-600 shadow-xs"
                  : "bg-slate-100 text-slate-700 border-slate-200/80 hover:bg-slate-200"
              }`}
            >
              <CalendarPlus className="w-4 h-4 shrink-0" />
              Duyệt Gia hạn ({scopedExtensions.length})
              {pendingExtCount > 0 && (
                <span className="px-2 py-0.5 text-[10px] rounded-full bg-rose-500 text-white font-bold">
                  {pendingExtCount} chờ
                </span>
              )}
            </button>

            {currentUser?.role !== "lecturer" && countLate > 0 && (
              <button
                type="button"
                onClick={handleExportLateExcel}
                title="Xuất danh sách các công việc đang trễ hạn ra Excel"
                className="h-9 flex items-center gap-1.5 px-2.5 rounded-xl text-xs font-semibold bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 cursor-pointer transition"
              >
                <FileDown className="w-3.5 h-3.5 shrink-0" />
                DS Trễ ({countLate})
              </button>
            )}
          </div>
        </div>

        {/* HÀNG 2: TÌM KIẾM & BỘ LỌC TRẠNG THÁI CÔNG VIỆC (NẰM SÁT Ô TÌM KIẾM) */}
        {subView === "tasks" ? (
          <div className="flex flex-wrap items-center gap-1.5">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
              <input
                type="text"
                placeholder="Tìm mã CV, tên việc, giảng viên..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="h-9 pl-8 pr-3 border border-slate-300 rounded-xl text-xs w-56 outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {[
              { key: "ALL", label: `Tất cả (${countAll})` },
              {
                key: "GROUP",
                label: `Việc Nhóm (${countGroup})`,
              },
              { key: "DOING", label: `Đang mở (${countDoing})` },
              { key: "Hoàn thành", label: `Hoàn thành (${countDone})` },
              {
                key: "LATE",
                label: `Trễ / Quá hạn (${countLate})`,
                isDanger: true,
              },
            ].map((st) => (
              <button
                key={st.key}
                type="button"
                onClick={() => setStatusFilter(st.key)}
                className={`h-9 px-3 rounded-xl text-xs font-semibold border cursor-pointer transition whitespace-nowrap ${
                  statusFilter === st.key
                    ? st.isDanger
                      ? "bg-rose-600 text-white border-rose-600 shadow-xs"
                      : "bg-blue-600 text-white border-blue-600 shadow-xs"
                    : st.isDanger
                    ? "bg-rose-50 text-rose-700 hover:bg-rose-100 border-rose-200"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200 border-slate-200/80"
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>
        ) : (
          <div className="h-9 flex items-center text-xs text-slate-500 px-1">
            Phê duyệt hoặc từ chối các đề xuất xin gia hạn thời hạn công việc của giảng viên
          </div>
        )}
      </div>

      {actionMsg && (
        <div
          className={`p-3 rounded-xl text-xs font-semibold flex items-center justify-between border ${
            actionMsg.type === "ok"
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : "bg-rose-50 border-rose-200 text-rose-700"
          }`}
        >
          <span>{actionMsg.text}</span>
          <button
            onClick={() => setActionMsg(null)}
            className="font-bold cursor-pointer px-2"
          >
            ✕
          </button>
        </div>
      )}

      {/* BẢNG 1: DANH SÁCH CÔNG VIỆC */}
      {subView === "tasks" && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden">
          <div
            tabIndex={0}
            role="region"
            aria-labelledby="tasks-table-caption"
            className="overflow-x-auto min-h-[500px] max-h-[680px] focus:outline-2 focus:outline-blue-600"
          >
            <span id="tasks-table-caption" className="sr-only">
              Bảng danh sách công việc, tiến độ thành viên nhóm, minh chứng và thời hạn
            </span>
            <table className="w-full text-left border-collapse text-sm">
              <thead className="sticky top-0 z-10 bg-slate-50 border-b border-slate-200 text-slate-600 text-[11px] uppercase tracking-wider">
                <tr>
                  <th className="p-3.5 w-[27%]">Công việc & Phân loại</th>
                  <th className="p-3.5 w-[33%]">Thành viên, Tiến độ (%) & Minh chứng</th>
                  <th className="p-3.5 w-[14%]">Hạn & Kiểm tra</th>
                  <th className="p-3.5 w-[11%]">Rủi ro AI</th>
                  <th className="p-3.5 text-right w-[15%]">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredTasks.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-24 text-center text-slate-400">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <CheckSquare className="w-8 h-8 text-slate-300" />
                        <span className="text-sm font-medium">Không tìm thấy công việc nào phù hợp với bộ lọc</span>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredTasks.map((t) => {
                  const roleInfo = getTaskRoleInfo(t);

                  return (
                    <tr key={t.id} className="hover:bg-slate-50/70 transition align-top">
                      {/* CỘT 1: CÔNG VIỆC */}
                      <td className="p-3.5">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-xs font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-md border border-blue-200">
                            {t.code}
                          </span>
                          {roleInfo.isGroup ? (
                            <span className="text-[11px] px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200 font-semibold">
                              Nhóm ({t.assignees?.length} GV)
                            </span>
                          ) : (
                            <span className="text-[11px] px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 font-medium">
                              Cá nhân
                            </span>
                          )}
                          <span className="text-[11px] px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 font-semibold">
                            {t.conversion_hours}h chuẩn
                          </span>
                          <span className="text-[11px] px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200 font-medium">
                            {roleInfo.taskDepartmentName}
                          </span>
                        </div>

                        <p className="font-bold text-slate-900 mt-1.5 leading-snug text-sm">
                          {t.title}
                        </p>

                        <div className="flex flex-wrap items-center gap-1.5 mt-1.5 text-[11px] text-slate-500">
                          <span>{t.task_type_name}</span>
                          <span>•</span>
                          <span
                            className={`font-semibold ${
                              t.priority === "Khẩn cấp" || t.priority === "Cao"
                                ? "text-rose-600"
                                : "text-slate-600"
                            }`}
                          >
                            Ưu tiên {t.priority}
                          </span>
                          {t.school_catalog_code && (
                            <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold">
                              Trường: {t.school_catalog_code}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* CỘT 2: HIỂN THỊ TIẾN ĐỘ CÔNG VIỆC */}
                      <td className="p-3.5">
                        {!roleInfo.showIndividualMemberProgress ? (
                          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                            <div className="flex items-center justify-between gap-2">
                              <div>
                                <div className="text-xs font-bold text-slate-900">
                                  Tiến độ công việc
                                </div>
                                <div className="text-[11px] text-slate-600 mt-0.5">
                                  Phụ trách chính:{" "}
                                  <b className="text-slate-800">
                                    {t.lead_lecturer_name ||
                                      t.assignees?.[0]?.lecturer_name ||
                                      "—"}
                                  </b>{" "}
                                  {roleInfo.isGroup
                                    ? `• Nhóm ${t.assignees?.length || 3} giảng viên`
                                    : "• Cá nhân"}
                                </div>
                              </div>
                              <div className="text-right">
                                <span className="inline-block px-2.5 py-0.5 rounded-lg bg-blue-600 text-white font-bold text-xs">
                                  {roleInfo.projectProgressPct}%
                                </span>
                              </div>
                            </div>

                            <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${
                                  t.status === "Hoàn thành" || roleInfo.projectProgressPct >= 100
                                    ? "bg-emerald-500"
                                    : "bg-blue-600"
                                }`}
                                style={{ width: `${roleInfo.projectProgressPct}%` }}
                              />
                            </div>

                            <div className="flex flex-wrap items-center justify-between gap-1.5 text-[11px] text-slate-600 pt-0.5">
                              <span>
                                Trưởng nhóm: <b className="text-slate-800">{t.lead_approval_status || "Đã duyệt"}</b>
                              </span>
                              <span>
                                Kiểm tra: <b className="text-slate-800">{t.reviewer_approval_status || "Đang theo dõi"}</b>
                              </span>
                            </div>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {roleInfo.isGroup && (
                              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
                                <div className="flex items-center justify-between gap-2 text-xs">
                                  <span className="font-bold text-slate-800">
                                    Tiến độ dự án
                                  </span>
                                  <span className="px-2 py-0.5 rounded-md bg-blue-600 text-white font-bold text-xs">
                                    {roleInfo.projectProgressPct}%
                                  </span>
                                </div>
                                <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                                  <div
                                    className={`h-full rounded-full transition-all ${
                                      roleInfo.projectProgressPct >= 100
                                        ? "bg-emerald-500"
                                        : "bg-blue-600"
                                    }`}
                                    style={{ width: `${roleInfo.projectProgressPct}%` }}
                                  />
                                </div>
                                <div className="flex flex-wrap items-center justify-between gap-1 text-[11px] text-slate-600">
                                  <span>
                                    Trưởng nhóm:{" "}
                                    <b className="text-slate-800">
                                      {t.lead_approval_status || "Chờ Trưởng nhóm duyệt"}
                                    </b>
                                  </span>
                                  <span>
                                    Người kiểm tra:{" "}
                                    <b className="text-slate-800">
                                      {t.reviewer_approval_status || "Chờ Người kiểm tra duyệt"}
                                    </b>
                                  </span>
                                </div>
                              </div>
                            )}

                            {t.assignees?.map((a: any) => {
                              const isLead =
                                a.is_lead || t.lead_lecturer_id === a.lecturer_id;
                              const pct = Number(a.progress_pct ?? 0);
                              const leadAppStatus =
                                a.lead_approval_status ||
                                (isLead ? "Trưởng nhóm đã duyệt" : "Chờ Trưởng nhóm duyệt");

                              return (
                                <div
                                  key={a.assignment_id || a.lecturer_id}
                                  className="p-2.5 rounded-xl border bg-white border-slate-200"
                                >
                                  <div className="flex items-center justify-between gap-2 text-xs mb-1">
                                    <div className="flex items-center gap-1.5 flex-wrap">
                                      <span className="font-bold text-slate-800">
                                        {a.lecturer_name}
                                      </span>
                                      {roleInfo.isGroup && isLead && (
                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 font-semibold">
                                          Trưởng nhóm
                                        </span>
                                      )}
                                      {roleInfo.isGroup && (
                                        <span
                                          className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                                            leadAppStatus === "Yêu cầu chỉnh sửa"
                                              ? "bg-rose-50 text-rose-700 border border-rose-200"
                                              : leadAppStatus === "Trưởng nhóm đã duyệt"
                                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                              : "bg-slate-100 text-slate-700 border border-slate-200"
                                          }`}
                                        >
                                          {leadAppStatus}
                                        </span>
                                      )}
                                    </div>
                                    <span className="font-bold text-blue-700 shrink-0">
                                      {pct}%
                                    </span>
                                  </div>

                                  <div className="w-full h-1.5 bg-slate-200 rounded-full overflow-hidden">
                                    <div
                                      className={`h-full rounded-full ${
                                        a.status === "Hoàn thành"
                                          ? a.is_late
                                            ? "bg-rose-500"
                                            : "bg-emerald-500"
                                          : "bg-blue-600"
                                      }`}
                                      style={{ width: `${pct}%` }}
                                    />
                                  </div>

                                  {a.member_task_note && (
                                    <div className="text-[11px] text-slate-600 mt-1 truncate">
                                      📌 <span className="italic">{a.member_task_note}</span>
                                    </div>
                                  )}

                                  {a.review_feedback && (
                                    <div className="mt-1 px-2 py-1 rounded bg-rose-50 border border-rose-200 text-[11px] text-rose-700 flex items-center gap-1">
                                      <AlertCircle className="w-3 h-3 shrink-0" />
                                      <span>{a.review_feedback}</span>
                                    </div>
                                  )}

                                  <div className="flex items-center justify-between gap-2 mt-1">
                                    <span className="text-[11px] text-slate-500">
                                      {a.status}
                                      {a.status === "Hoàn thành" && a.is_late
                                        ? ` (Trễ ${a.delay_days || 1} ngày)`
                                        : ""}
                                    </span>

                                    {a.latest_evidence_name && (
                                      <a
                                        href={
                                          a.latest_evidence_url?.startsWith("http")
                                            ? a.latest_evidence_url
                                            : `${BACKEND_ORIGIN}${a.latest_evidence_url}`
                                        }
                                        target="_blank"
                                        rel="noreferrer"
                                        className="inline-flex items-center gap-1 text-[11px] text-emerald-700 hover:underline font-semibold truncate max-w-[170px]"
                                      >
                                        <FileText className="w-3 h-3 shrink-0" />
                                        {a.latest_evidence_name}
                                      </a>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </td>

                      {/* CỘT 3: HẠN & NGƯỜI KIỂM TRA */}
                      <td className="p-3.5 text-xs text-slate-600 space-y-1">
                        <div>
                          Hạn: <b className="text-slate-900">{t.current_deadline}</b>
                        </div>
                        {t.current_deadline !== t.original_deadline && (
                          <div className="text-[11px] text-amber-700">
                            (Gốc: {t.original_deadline})
                          </div>
                        )}
                        <div className="pt-1 border-t border-slate-100 text-[11px] text-slate-500">
                          Kiểm tra:{" "}
                          <b className="text-slate-800">
                            {t.reviewer_name || t.creator_name || "TS. Phạm Quốc Tuấn"}
                          </b>
                        </div>
                      </td>

                      {/* CỘT 4: RỦI RO TRỄ HẠN */}
                      <td className="p-3.5">
                        {t.assignees?.slice(0, 1).map((a: any) => {
                          const ml = a.ml_prediction || t.ml_prediction;
                          if (!ml || ml.probability === null || ml.probability === undefined) {
                            return (
                              <span
                                key={a.assignment_id || a.lecturer_id}
                                className="text-xs text-slate-400"
                              >
                                —
                              </span>
                            );
                          }
                          return (
                            <span
                              key={a.assignment_id || a.lecturer_id}
                              className={`inline-block px-2.5 py-1 rounded-lg text-xs font-bold ${
                                ml.level === "Cao"
                                  ? "bg-rose-100 text-rose-700 border border-rose-200"
                                  : ml.level === "Trung bình"
                                  ? "bg-amber-100 text-amber-800 border border-amber-200"
                                  : "bg-emerald-100 text-emerald-700 border border-emerald-200"
                              }`}
                            >
                              {ml.level} ({(Number(ml.probability) * 100).toFixed(0)}%)
                            </span>
                          );
                        })}
                      </td>

                      {/* CỘT 5: THAO TÁC PHÂN QUYỀN 5 CẤP RÕ RÀNG */}
                      <td className="p-3.5 text-right">
                        <div className="flex flex-col items-end gap-1.5">
                          {/* 1. Giảng viên (Thành viên hoặc Trưởng nhóm): Cập nhật % tiến độ */}
                          {t.status !== "Hoàn thành" && roleInfo.canSelfUpdateProgress && (
                            <button
                              onClick={() => openProgressModal(t)}
                              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold cursor-pointer shadow-2xs"
                            >
                              <Upload className="w-3 h-3" />
                              Cập nhật Tiến độ
                            </button>
                          )}

                          {/* 2. Trưởng nhóm (Người phụ trách chính): Phê duyệt tiến độ thành viên */}
                          {t.status !== "Hoàn thành" &&
                            roleInfo.isGroup &&
                            roleInfo.canLeadApproveMembers && (
                              <button
                                onClick={() => openLeadApproveModal(t)}
                                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold cursor-pointer shadow-2xs"
                              >
                                <UserCheck className="w-3.5 h-3.5" />
                                Duyệt Tiến độ Nhóm
                              </button>
                            )}

                          {/* 3. Người kiểm tra: Phê duyệt quyết định của Trưởng nhóm */}
                          {t.status !== "Hoàn thành" &&
                            roleInfo.canReviewerApproveDecision && (
                              <button
                                onClick={() => openReviewerApproveModal(t)}
                                className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold cursor-pointer shadow-2xs"
                              >
                                <ShieldCheck className="w-3.5 h-3.5" />
                                Duyệt QĐ Trưởng nhóm
                              </button>
                            )}

                          {/* 4. Phân việc nhóm (Dành cho Trưởng nhóm trên việc Nhóm) */}
                          {t.status !== "Hoàn thành" && roleInfo.canDelegate && (
                            <button
                              onClick={() => openDelegateModal(t)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 text-xs font-semibold cursor-pointer"
                            >
                              <Users className="w-3.5 h-3.5" />
                              Phân việc nhóm
                            </button>
                          )}

                          {/* 5. Báo thiếu sót / Nhắc nhóm (Dành cho Người kiểm tra / Trưởng nhóm) */}
                          {t.status !== "Hoàn thành" && roleInfo.canSendFeedback && (
                            <button
                              onClick={() => openFeedbackModal(t)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-xs font-semibold cursor-pointer"
                            >
                              <BellRing className="w-3 h-3" />
                              Báo thiếu sót
                            </button>
                          )}

                          <div className="flex flex-wrap items-center justify-end gap-1">
                            {t.status !== "Hoàn thành" && (
                              <button
                                onClick={() => {
                                  setExtTask(t);
                                  const baseDate = t.current_deadline
                                    ? new Date(t.current_deadline)
                                    : new Date();
                                  const nextWeek = new Date(
                                    baseDate.getTime() + 7 * 86400000
                                  )
                                    .toISOString()
                                    .slice(0, 10);
                                  setProposedDeadline(nextWeek);
                                }}
                                className="px-2 py-1 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-800 text-[11px] font-semibold cursor-pointer"
                              >
                                Gia hạn
                              </button>
                            )}

                            <button
                              onClick={() => openDetail(t.id)}
                              className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-semibold cursor-pointer"
                            >
                              <Eye className="w-3 h-3" />
                              Chi tiết
                            </button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                }))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* BẢNG 2: DANH SÁCH GIA HẠN */}
      {subView === "extensions" && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50 text-slate-600 text-xs uppercase border-b">
                  <th className="p-3.5">Công việc & Người xin</th>
                  <th className="p-3.5">Lý do xin gia hạn</th>
                  <th className="p-3.5 text-center">Hạn cũ → Đề xuất</th>
                  <th className="p-3.5 text-center">Trạng thái</th>
                  <th className="p-3.5 text-right">Xử lý</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {scopedExtensions.map((e) => (
                  <tr key={e.id} className="hover:bg-slate-50">
                    <td className="p-3.5">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-xs font-mono font-bold text-blue-700">
                          {e.task_code}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
                          {e.department_name || "Bộ môn CNPM (K01)"}
                        </span>
                      </div>
                      <div className="font-semibold text-slate-900 mt-0.5">{e.task_title}</div>
                      <div className="text-xs text-slate-500">
                        Người xin: <b>{e.requester_name}</b> ({e.progress_pct}%)
                      </div>
                    </td>
                    <td className="p-3.5 text-xs text-slate-700 max-w-xs">{e.reason}</td>
                    <td className="p-3.5 text-center text-xs">
                      <div className="text-slate-400 line-through">{e.old_deadline}</div>
                      <div className="font-bold text-amber-700">
                        {e.proposed_deadline} (+{e.extra_days} ngày)
                      </div>
                    </td>
                    <td className="p-3.5 text-center">
                      <span
                        className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                          e.status === "Đã duyệt"
                            ? "bg-emerald-100 text-emerald-700"
                            : e.status === "Từ chối"
                            ? "bg-rose-100 text-rose-700"
                            : "bg-amber-100 text-amber-800"
                        }`}
                      >
                        {e.status}
                      </span>
                    </td>
                    <td className="p-3.5 text-right">
                      {e.status === "Chờ duyệt" && currentUser?.role !== "lecturer" ? (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleReviewExtension(e.id, "Đã duyệt")}
                            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold cursor-pointer"
                          >
                            <Check className="w-3.5 h-3.5" /> Duyệt
                          </button>
                          <button
                            onClick={() => handleReviewExtension(e.id, "Từ chối")}
                            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold cursor-pointer"
                          >
                            <X className="w-3.5 h-3.5" /> Từ chối
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">
                          {e.reviewed_by_name || "Đang chờ"}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* MODAL 1: GIẢNG VIÊN TỰ CẬP NHẬT TIẾN ĐỘ CÁ NHÂN (%) & ĐÍNH KÈM MINH CHỨNG */}
      {progTask && (
        <div
          onClick={(e) => {
            if (e.target === e.currentTarget) setProgTask(null);
          }}
          className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4"
        >
          <form
            role="dialog"
            aria-modal="true"
            onSubmit={handleSaveProgress}
            className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4"
          >
            {(() => {
              const previewAssignees = (progTask.assignees || []).map((a: any) =>
                Number(a.lecturer_id) === Number(progLecturerId)
                  ? { ...a, progress_pct: progPct }
                  : a
              );
              const previewProjectPct = calculateProjectProgressFromMembers(
                previewAssignees,
                progPct
              );
              return (
                <>
                  <div>
                    <h3 className="text-base font-bold text-slate-900">
                      Giảng viên Tự Cập nhật Tiến độ Cá nhân ({progTask.code})
                    </h3>
                    <p className="text-xs text-slate-600 mt-0.5">{progTask.title}</p>
                  </div>

                  {progTask.assignees?.length > 1 && (
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Tài khoản Giảng viên đang tự cập nhật tiến độ cá nhân
                      </label>
                      <select
                        value={progLecturerId || ""}
                        onChange={(e) => {
                          const lid = Number(e.target.value);
                          setProgLecturerId(lid);
                          const found = progTask.assignees.find(
                            (a: any) => a.lecturer_id === lid
                          );
                          if (found) {
                            setProgPct(found.progress_pct ?? 50);
                          }
                        }}
                        className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs bg-white font-semibold"
                      >
                        {progTask.assignees.map((a: any) => (
                          <option key={a.lecturer_id} value={a.lecturer_id}>
                            {a.lecturer_name}{" "}
                            {a.is_lead || progTask.lead_lecturer_id === a.lecturer_id
                              ? "(Trưởng nhóm)"
                              : "(Thành viên)"}{" "}
                            — Hiện tại: {a.progress_pct}%
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <div>
                    <div className="flex justify-between text-xs font-semibold mb-1">
                      <span>Tiến độ cá nhân của bạn (%)</span>
                      <span className="text-blue-600 font-bold text-sm">{progPct}%</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={100}
                      step={5}
                      value={progPct}
                      onChange={(e) => setProgPct(Number(e.target.value))}
                      className="w-full"
                    />
                    <div className="flex justify-between gap-2 mt-2">
                      {[25, 50, 75, 100].map((v) => (
                        <button
                          key={v}
                          type="button"
                          onClick={() => setProgPct(v)}
                          className={`flex-1 py-1 text-xs rounded-lg font-semibold cursor-pointer ${
                            progPct === v
                              ? "bg-blue-600 text-white"
                              : "bg-slate-100 hover:bg-slate-200 text-slate-700"
                          }`}
                        >
                          {v}%
                        </button>
                      ))}
                    </div>
                  </div>

                  {progTask.assignees?.length > 1 && (
                    <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 flex items-center justify-between">
                      <span className="font-semibold">Tiến độ dự án sau cập nhật:</span>
                      <span className="px-2.5 py-0.5 rounded-md bg-blue-600 text-white font-bold">
                        {previewProjectPct}%
                      </span>
                    </div>
                  )}

                  <div className="p-3 rounded-xl bg-amber-50/70 border border-amber-200 space-y-2">
                    <label className="block text-xs font-bold text-amber-900">
                      Đính kèm File Minh chứng Kết quả Công việc
                    </label>
                    <label className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-dashed border-amber-400 bg-white hover:bg-amber-50 text-xs font-semibold text-amber-800 cursor-pointer transition">
                      <Upload className="w-4 h-4" />
                      <span>
                        {uploadingFile
                          ? "Đang tải file lên..."
                          : "Chọn file minh chứng (.pdf, .docx, .zip...)"}
                      </span>
                      <input
                        type="file"
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          if (f) {
                            uploadFileHelper(f, (name, url) => {
                              setEvidenceFileName(name);
                              setEvidenceFileUrl(url);
                            });
                          }
                        }}
                        className="hidden"
                      />
                    </label>
                    {evidenceFileName && (
                      <div className="flex items-center justify-between text-xs bg-emerald-50 border border-emerald-200 text-emerald-800 px-2.5 py-1.5 rounded-lg">
                        <span className="truncate font-medium">
                          Đã chọn: <b>{evidenceFileName}</b>
                        </span>
                        <button
                          type="button"
                          onClick={() => {
                            setEvidenceFileName("");
                            setEvidenceFileUrl("");
                          }}
                          className="text-rose-600 font-bold ml-2 cursor-pointer"
                        >
                          ✕
                        </button>
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Báo cáo kết quả thực hiện gửi Trưởng nhóm phê duyệt *
                    </label>
                    <textarea
                      value={progNote}
                      onChange={(e) => setProgNote(e.target.value)}
                      rows={3}
                      placeholder="Nhập kết quả phần việc bạn đã thực hiện..."
                      className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs"
                      required
                    />
                  </div>

                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setProgTask(null)}
                      className="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 text-xs font-semibold cursor-pointer"
                    >
                      Hủy
                    </button>
                    <button
                      type="submit"
                      disabled={uploadingFile}
                      className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-semibold cursor-pointer"
                    >
                      Lưu & Gửi Trưởng nhóm duyệt
                    </button>
                  </div>
                </>
              );
            })()}
          </form>
        </div>
      )}

      {/* MODAL 1B: THÀNH VIÊN NHÓM GỬI MINH CHỨNG LÊN TRƯỞNG NHÓM TRƯỚC */}
      {memberEvTask && (
        <div
          onClick={(e) => {
            if (e.target === e.currentTarget) setMemberEvTask(null);
          }}
          className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4"
        >
          <form
            role="dialog"
            aria-modal="true"
            onSubmit={handleSubmitMemberEvidence}
            className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4"
          >
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Gửi Minh chứng Thành viên lên Trưởng nhóm ({memberEvTask.code})
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Minh chứng của bạn sẽ được gửi lên{" "}
                <b className="text-amber-800">
                  Trưởng nhóm ({memberEvTask.lead_lecturer_name || "Phụ trách chính"})
                </b>{" "}
                để rà soát, cập nhật % tiến độ và tổng hợp nộp cho Khoa.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 space-y-2">
              <label className="block text-xs font-semibold text-blue-900">
                Đính kèm File Minh chứng phần việc của bạn *
              </label>
              <label className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-dashed border-blue-400 bg-white hover:bg-blue-50 text-xs font-semibold text-blue-700 cursor-pointer transition">
                <Upload className="w-4 h-4" />
                <span>
                  {uploadingFile
                    ? "Đang tải file..."
                    : "Chọn file minh chứng gửi Trưởng nhóm"}
                </span>
                <input
                  type="file"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) {
                      uploadFileHelper(f, (name, url) => {
                        setMemberEvFileName(name);
                        setMemberEvFileUrl(url);
                      });
                    }
                  }}
                  className="hidden"
                />
              </label>
              {memberEvFileName && (
                <div className="text-xs font-semibold text-emerald-700">
                  ✓ Đã đính kèm: {memberEvFileName}
                </div>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Báo cáo kết quả phần việc gửi Trưởng nhóm *
              </label>
              <textarea
                value={memberEvNote}
                onChange={(e) => setMemberEvNote(e.target.value)}
                rows={3}
                placeholder="Mô tả kết quả phần việc đã hoàn thành để Trưởng nhóm kiểm tra..."
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs"
                required
              />
            </div>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setMemberEvTask(null)}
                className="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 text-xs font-semibold cursor-pointer"
              >
                Đóng
              </button>
              <button
                type="submit"
                disabled={uploadingFile}
                className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-semibold cursor-pointer"
              >
                Gửi lên Trưởng nhóm
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL 1C: NGƯỜI KIỂM TRA / TRƯỞNG NHÓM BÁO THIẾU SÓT ĐỂ NHÓM KỊP THỜI LÀM */}
      {feedbackTask && (
        <div
          onClick={(e) => {
            if (e.target === e.currentTarget) setFeedbackTask(null);
          }}
          className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4"
        >
          <form
            role="dialog"
            aria-modal="true"
            onSubmit={handleSendFeedback}
            className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4"
          >
            <div>
              <h3 className="text-base font-bold text-rose-700 flex items-center gap-2">
                <BellRing className="w-4 h-4" />
                Thông báo Thiếu sót & Nhắc nhở Nhóm ({feedbackTask.code})
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Gửi cảnh báo thiếu sót trực tiếp đến thành viên hoặc toàn nhóm để kịp thời bổ sung minh chứng.
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Phạm vi nhắc nhở
              </label>
              <select
                value={feedbackLecturerId}
                onChange={(e) =>
                  setFeedbackLecturerId(
                    e.target.value === "" ? "" : Number(e.target.value)
                  )
                }
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs bg-white font-semibold"
              >
                <option value="">-- Nhắc nhở toàn bộ các thành viên trong nhóm --</option>
                {feedbackTask.assignees?.map((a: any) => (
                  <option key={a.lecturer_id} value={a.lecturer_id}>
                    Chỉ nhắc: {a.lecturer_name} (Hiện tại {a.progress_pct}%)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Điều chỉnh lại % tiến độ thực tế (Tùy chọn)
              </label>
              <input
                type="number"
                min={0}
                max={100}
                value={feedbackProgressPct}
                onChange={(e) =>
                  setFeedbackProgressPct(
                    e.target.value === "" ? "" : Number(e.target.value)
                  )
                }
                placeholder="Để trống nếu giữ nguyên % hiện tại..."
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Nội dung thiếu sót cần bổ sung gấp *
              </label>
              <textarea
                value={feedbackContent}
                onChange={(e) => setFeedbackContent(e.target.value)}
                rows={3}
                placeholder="VD: Thiếu bảng ma trận chuẩn đầu ra PLO-PI ở mục 3, yêu cầu bổ sung trước 17h hôm nay..."
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs"
                required
              />
            </div>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setFeedbackTask(null)}
                className="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 text-xs font-semibold cursor-pointer"
              >
                Hủy
              </button>
              <button
                type="submit"
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold cursor-pointer"
              >
                Gửi Thông báo Thiếu sót
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL 2: PHÂN VIỆC TRONG NHÓM (ĐÃ BỎ THÊM GIẢNG VIÊN NGOÀI NHÓM) */}
      {delegateTask && (
        <div
          onClick={(e) => {
            if (e.target === e.currentTarget) setDelegateTask(null);
          }}
          className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4"
        >
          <form
            role="dialog"
            aria-modal="true"
            onSubmit={handleSaveDelegate}
            className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4 max-h-[85vh] overflow-y-auto"
          >
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Giao Nhiệm vụ Chi tiết cho Thành viên Nhóm ({delegateTask.code})
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">{delegateTask.title}</p>
            </div>

            {currentUser?.role !== "lecturer" && (
              <div className="p-3 rounded-xl bg-amber-50 border border-amber-200">
                <label className="block text-xs font-semibold text-amber-900 mb-1">
                  Trưởng nhóm (Người phụ trách chính)
                </label>
                <select
                  value={delegateLeadId || ""}
                  onChange={(e) => setDelegateLeadId(Number(e.target.value))}
                  className="w-full px-3 py-1.5 border border-amber-300 rounded-lg text-xs bg-white font-semibold"
                >
                  {delegateMembers.map((m) => (
                    <option key={m.lecturer_id} value={m.lecturer_id}>
                      {m.lecturer_name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="space-y-2.5">
              <label className="block text-xs font-semibold text-slate-700">
                Phân chia phần việc cho các thành viên trong nhóm ({delegateMembers.length} GV):
              </label>
              {delegateMembers.map((m, idx) => {
                const isLead = delegateLeadId === m.lecturer_id;
                return (
                  <div
                    key={m.lecturer_id}
                    className={`p-3 rounded-xl border ${
                      isLead
                        ? "bg-amber-50/50 border-amber-300"
                        : "bg-slate-50 border-slate-200"
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <span className="font-semibold text-slate-900">
                        {idx + 1}. {m.lecturer_name}
                      </span>
                      {isLead && (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300 font-bold">
                          Trưởng nhóm (Phụ trách chính)
                        </span>
                      )}
                    </div>
                    <input
                      type="text"
                      value={m.member_task_note}
                      onChange={(e) => {
                        const val = e.target.value;
                        setDelegateMembers((prev) =>
                          prev.map((x) =>
                            x.lecturer_id === m.lecturer_id
                              ? { ...x, member_task_note: val }
                              : x
                          )
                        );
                      }}
                      placeholder="Nhập phần việc cụ thể giao cho thành viên này..."
                      className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs bg-white"
                      required
                    />
                  </div>
                );
              })}
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setDelegateTask(null)}
                className="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 text-xs font-semibold cursor-pointer"
              >
                Đóng
              </button>
              <button
                type="submit"
                className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-semibold cursor-pointer"
              >
                Lưu Phân việc Nhóm
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL 3: XIN GIA HẠN */}
      {extTask && (
        <div
          onClick={(e) => {
            if (e.target === e.currentTarget) setExtTask(null);
          }}
          className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4"
        >
          <form
            role="dialog"
            aria-modal="true"
            onSubmit={handleRequestExtension}
            className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4"
          >
            <h3 className="text-base font-bold text-slate-900">
              Gửi Yêu cầu Gia hạn ({extTask.code})
            </h3>
            <p className="text-xs text-slate-600">
              Hạn hiện tại: <b>{extTask.current_deadline}</b>
            </p>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Hạn hoàn thành mới đề xuất *
              </label>
              <input
                type="date"
                value={proposedDeadline}
                onChange={(e) => setProposedDeadline(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Lý do xin gia hạn *
              </label>
              <textarea
                value={extReason}
                onChange={(e) => setExtReason(e.target.value)}
                rows={3}
                placeholder="Nêu rõ nguyên nhân và cam kết tiến độ..."
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs"
                required
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setExtTask(null)}
                className="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 text-xs font-semibold cursor-pointer"
              >
                Đóng
              </button>
              <button
                type="submit"
                className="px-4 py-2 rounded-xl bg-amber-600 text-white text-xs font-semibold cursor-pointer"
              >
                Gửi Yêu cầu
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL 4: ÁNH XẠ DANH MỤC TRƯỜNG */}
      {mapTask && (
        <div
          onClick={(e) => {
            if (e.target === e.currentTarget) setMapTask(null);
          }}
          className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4"
        >
          <form
            role="dialog"
            aria-modal="true"
            onSubmit={handleMapSchool}
            className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4"
          >
            <h3 className="text-base font-bold text-slate-900">
              Ánh xạ Danh mục Công việc Cấp Trường
            </h3>
            <p className="text-xs text-slate-600">{mapTask.title}</p>
            <select
              value={selectedSchoolId}
              onChange={(e) => setSelectedSchoolId(Number(e.target.value))}
              className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs bg-white"
            >
              {schoolCatalog.map((sc) => (
                <option key={sc.id} value={sc.id}>
                  [{sc.code}] {sc.name} ({sc.conversion_hours} giờ chuẩn)
                </option>
              ))}
            </select>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setMapTask(null)}
                className="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 text-xs font-semibold cursor-pointer"
              >
                Hủy
              </button>
              <button
                type="submit"
                className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-semibold cursor-pointer"
              >
                Xác nhận
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL 5: XEM CHI TIẾT & NHẬT KÝ TIẾN ĐỘ + MINH CHỨNG */}
      {detailData && (
        <div
          onClick={(e) => {
            if (e.target === e.currentTarget) setDetailData(null);
          }}
          className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4"
        >
          <div
            role="dialog"
            aria-modal="true"
            className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-xl space-y-4 max-h-[85vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <span className="text-xs font-mono font-bold text-blue-700">
                  {detailData.code}
                </span>
                <h3 className="text-base font-bold text-slate-900">
                  {detailData.title}
                </h3>
              </div>
              <button
                onClick={() => setDetailData(null)}
                className="px-3 py-1 rounded-lg bg-slate-100 text-slate-600 text-xs font-bold cursor-pointer"
              >
                Đóng
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                <div className="text-slate-500">Người giao việc</div>
                <div className="font-semibold text-slate-800 mt-0.5">
                  {detailData.creator_name || "Hệ thống"}
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                <div className="text-slate-500">Người kiểm tra tiến độ</div>
                <div className="font-semibold text-blue-800 mt-0.5">
                  {detailData.reviewer_name || detailData.creator_name || "Trưởng đơn vị"}
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                <div className="text-slate-500">Trưởng nhóm (Phụ trách chính)</div>
                <div className="font-semibold text-amber-800 mt-0.5">
                  {detailData.lead_lecturer_name ||
                    detailData.assignees?.[0]?.lecturer_name ||
                    "—"}
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-800 uppercase">
                Nhật ký Cập nhật Tiến độ & Minh chứng ({detailData.progress_logs?.length || 0})
              </h4>
              {detailData.progress_logs?.length === 0 ? (
                <p className="text-xs text-slate-400 italic">
                  Chưa có lịch sử cập nhật tiến độ.
                </p>
              ) : (
                <div className="space-y-2">
                  {detailData.progress_logs.map((p: any) => (
                    <div
                      key={p.id}
                      className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs"
                    >
                      <div className="flex justify-between font-semibold text-slate-800">
                        <span>
                          {p.lecturer_name} — Đạt {p.progress_pct}%
                        </span>
                        <span className="text-slate-500">
                          {String(p.created_at).slice(0, 16).replace("T", " ")}
                        </span>
                      </div>
                      <p className="text-slate-600 mt-1">{p.note}</p>
                      {p.evidence_file_name && (
                        <div className="mt-1.5">
                          <a
                            href={
                              p.evidence_file_url?.startsWith("http")
                                ? p.evidence_file_url
                                : `${BACKEND_ORIGIN}${p.evidence_file_url}`
                            }
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-emerald-700 hover:underline font-semibold"
                          >
                            <FileText className="w-3.5 h-3.5" />
                            Minh chứng: {p.evidence_file_name}
                          </a>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* MODAL 6: TRƯỞNG NHÓM (NGƯỜI PHỤ TRÁCH CHÍNH) PHÊ DUYỆT TIẾN ĐỘ TỪNG THÀNH VIÊN & GỬI HỆ THỐNG TỰ TÍNH % DỰ ÁN */}
      {leadApproveTask && (
        <div
          onClick={(e) => {
            if (e.target === e.currentTarget) setLeadApproveTask(null);
          }}
          className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4"
        >
          <form
            role="dialog"
            aria-modal="true"
            onSubmit={handleSaveLeadApproval}
            className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-xl space-y-4 max-h-[90vh] overflow-y-auto text-xs"
          >
            {(() => {
              const autoPct = calculateProjectProgressFromMembers(
                leadApproveTask.assignees,
                leadApproveTask.progress_pct
              );
              return (
                <>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <span className="inline-block px-2.5 py-0.5 rounded-md bg-emerald-100 text-emerald-800 font-bold text-[11px] mb-1">
                        Quyền Trưởng nhóm (Người phụ trách chính)
                      </span>
                      <h3 className="text-base font-bold text-slate-900">
                        Phê duyệt Tiến độ Thành viên & Gửi Hệ thống ({leadApproveTask.code})
                      </h3>
                      <p className="text-xs text-slate-600 mt-0.5">
                        {leadApproveTask.title}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setLeadApproveTask(null)}
                      className="px-2.5 py-1 rounded-lg bg-slate-100 font-bold"
                    >
                      ✕
                    </button>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
                    <span className="font-bold text-slate-800">
                      Tiến độ dự án
                    </span>
                    <span className="px-3 py-1 rounded-lg bg-blue-600 text-white font-bold text-sm">
                      {autoPct}%
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    <div className="font-bold text-slate-800">
                      Tiến độ các thành viên trong nhóm:
                    </div>
                    {(leadApproveTask.assignees || []).map((a: any) => {
                      const dec = leadMemberDecisions[a.lecturer_id] || {
                        approval_status: "Trưởng nhóm đã duyệt",
                        review_note: "",
                      };
                      return (
                        <div
                          key={a.lecturer_id}
                          className="p-3 rounded-xl border border-slate-200 bg-slate-50 space-y-2"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div>
                              <span className="font-bold text-slate-900">
                                {a.lecturer_name}
                              </span>{" "}
                              {a.is_lead && (
                                <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-bold text-[10px]">
                                  Trưởng nhóm
                                </span>
                              )}
                              <div className="text-[11px] text-slate-500">
                                Phần việc: {a.member_task_note || "Thực hiện chuyên môn nhóm"}
                              </div>
                            </div>
                            <span className="px-2.5 py-1 rounded-lg bg-blue-100 text-blue-800 font-extrabold text-xs">
                              Tự cập nhật: {a.progress_pct}%
                            </span>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            <select
                              value={dec.approval_status}
                              onChange={(e) =>
                                setLeadMemberDecisions((prev) => ({
                                  ...prev,
                                  [a.lecturer_id]: {
                                    ...dec,
                                    approval_status: e.target.value,
                                  },
                                }))
                              }
                              className="px-3 py-1.5 rounded-xl border border-slate-300 bg-white font-bold text-slate-800"
                            >
                              <option value="Trưởng nhóm đã duyệt">
                                ✓ Trưởng nhóm đã duyệt ({a.progress_pct}%)
                              </option>
                              <option value="Yêu cầu chỉnh sửa">
                                ⚠ Yêu cầu thành viên chỉnh sửa / bổ sung
                              </option>
                            </select>
                            <input
                              type="text"
                              value={dec.review_note}
                              onChange={(e) =>
                                setLeadMemberDecisions((prev) => ({
                                  ...prev,
                                  [a.lecturer_id]: {
                                    ...dec,
                                    review_note: e.target.value,
                                  },
                                }))
                              }
                              placeholder="Nhận xét của Trưởng nhóm (nếu có)..."
                              className="px-3 py-1.5 rounded-xl border border-slate-300 bg-white"
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      Ghi chú trình Người kiểm tra ({leadApproveTask.reviewer_name || "TS. Phạm Quốc Tuấn"})
                    </label>
                    <textarea
                      value={leadDecisionNote}
                      onChange={(e) => setLeadDecisionNote(e.target.value)}
                      rows={2}
                      className="w-full px-3 py-2 border border-slate-300 rounded-xl"
                    />
                  </div>

                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setLeadApproveTask(null)}
                      className="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 font-semibold cursor-pointer"
                    >
                      Hủy
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold cursor-pointer"
                    >
                      Xác nhận Phê duyệt ({autoPct}%)
                    </button>
                  </div>
                </>
              );
            })()}
          </form>
        </div>
      )}

      {/* MODAL 7: NGƯỜI KIỂM TRA QUAN SÁT TIẾN ĐỘ TỪNG THÀNH VIÊN & PHÊ DUYỆT QUYẾT ĐỊNH TRƯỞNG NHÓM */}
      {reviewerApproveTask && (
        <div
          onClick={(e) => {
            if (e.target === e.currentTarget) setReviewerApproveTask(null);
          }}
          className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4"
        >
          <form
            role="dialog"
            aria-modal="true"
            onSubmit={handleSaveReviewerApproval}
            className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-xl space-y-4 max-h-[90vh] overflow-y-auto text-xs"
          >
            {(() => {
              const autoPct = calculateProjectProgressFromMembers(
                reviewerApproveTask.assignees,
                reviewerApproveTask.progress_pct
              );
              return (
                <>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <span className="inline-block px-2.5 py-0.5 rounded-md bg-indigo-100 text-indigo-800 font-bold text-[11px] mb-1">
                        Quyền Người kiểm tra ({reviewerApproveTask.reviewer_name || "TS. Phạm Quốc Tuấn"})
                      </span>
                      <h3 className="text-base font-bold text-slate-900">
                        Phê duyệt Quyết định của Trưởng nhóm ({reviewerApproveTask.code})
                      </h3>
                      <p className="text-xs text-slate-600 mt-0.5">
                        {reviewerApproveTask.title}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setReviewerApproveTask(null)}
                      className="px-2.5 py-1 rounded-lg bg-slate-100 font-bold"
                    >
                      ✕
                    </button>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-700">
                        Trưởng nhóm ({reviewerApproveTask.lead_lecturer_name}):
                      </span>
                      <span className="px-2.5 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200 font-bold">
                        {reviewerApproveTask.lead_approval_status || "Đã duyệt & Trình Người kiểm tra"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-xs border-t border-slate-200 pt-2">
                      <span className="font-semibold text-slate-700">Tiến độ dự án:</span>
                      <span className="font-bold text-blue-700 text-sm">
                        {autoPct}%
                      </span>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="font-bold text-slate-800">
                      Quan sát chi tiết tiến độ từng thành viên trong nhóm:
                    </div>
                    {(reviewerApproveTask.assignees || []).map((a: any) => (
                      <div
                        key={a.lecturer_id}
                        className="p-2.5 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between gap-2"
                      >
                        <div>
                          <div className="font-bold text-slate-900">
                            {a.lecturer_name}{" "}
                            {a.is_lead && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-bold">
                                Trưởng nhóm
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-500">
                            Trạng thái Trưởng nhóm duyệt:{" "}
                            <b>{a.lead_approval_status || "Trưởng nhóm đã duyệt"}</b>
                          </div>
                        </div>
                        <span className="px-2.5 py-1 rounded-lg bg-blue-600 text-white font-extrabold">
                          {a.progress_pct}%
                        </span>
                      </div>
                    ))}
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      Quyết định của Người kiểm tra
                    </label>
                    <select
                      value={reviewerDecisionStatus}
                      onChange={(e) => setReviewerDecisionStatus(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-xl bg-white font-bold text-slate-900"
                    >
                      <option value="Đã phê duyệt quyết định Trưởng nhóm">
                        ✓ Phê duyệt quyết định của Trưởng nhóm (Công nhận tiến độ dự án {autoPct}%)
                      </option>
                      <option value="Yêu cầu Trưởng nhóm rà soát lại">
                        ⚠ Yêu cầu Trưởng nhóm rà soát / bổ sung minh chứng
                      </option>
                    </select>
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">
                      Nhận xét của Người kiểm tra
                    </label>
                    <textarea
                      value={reviewerDecisionNote}
                      onChange={(e) => setReviewerDecisionNote(e.target.value)}
                      rows={2}
                      className="w-full px-3 py-2 border border-slate-300 rounded-xl"
                    />
                  </div>

                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setReviewerApproveTask(null)}
                      className="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 font-semibold cursor-pointer"
                    >
                      Hủy
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold cursor-pointer"
                    >
                      Xác nhận Quyết định Kiểm tra
                    </button>
                  </div>
                </>
              );
            })()}
          </form>
        </div>
      )}
    </div>
  );
};

export default TasksAndExtensionsView;
