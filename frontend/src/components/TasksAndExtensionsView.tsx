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
} from "lucide-react";

import { API_BASE, formatFeatureName } from "../types";

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
  users = [],
  onRefresh,
}) => {
  const [subView, setSubView] = useState<"tasks" | "extensions">("tasks");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [search, setSearch] = useState<string>("");
  const [extensions, setExtensions] = useState<any[]>([]);
  const [actionMsg, setActionMsg] = useState<string>("");

  // Modal Cập nhật tiến độ & Minh chứng
  const [progTask, setProgTask] = useState<any | null>(null);
  const [progLecturerId, setProgLecturerId] = useState<number | null>(null);
  const [progPct, setProgPct] = useState<number>(50);
  const [progNote, setProgNote] = useState<string>("");
  const [evidenceFileName, setEvidenceFileName] = useState<string>("");
  const [evidenceFileUrl, setEvidenceFileUrl] = useState<string>("");
  const [uploadingFile, setUploadingFile] = useState<boolean>(false);

  // Modal Phân việc cho thành viên nhóm (dành cho Người phụ trách chính / Quản lý)
  const [delegateTask, setDelegateTask] = useState<any | null>(null);
  const [delegateLeadId, setDelegateLeadId] = useState<number | null>(null);
  const [delegateMembers, setDelegateMembers] = useState<
    { lecturer_id: number; lecturer_name: string; member_task_note: string }[]
  >([]);
  const [addMemberId, setAddMemberId] = useState<string>("");
  const [addMemberNote, setAddMemberNote] = useState<string>("");

  // Modal Xin gia hạn
  const [extTask, setExtTask] = useState<any | null>(null);
  const [proposedDeadline, setProposedDeadline] = useState<string>("");
  const [extReason, setExtReason] = useState<string>("");

  // Modal Ánh xạ việc Trường
  const [mapTask, setMapTask] = useState<any | null>(null);
  const [selectedSchoolId, setSelectedSchoolId] = useState<number>(
    schoolCatalog[0]?.id || 1
  );

  // Modal Chi tiết & Nhật ký tiến độ
  const [detailData, setDetailData] = useState<any | null>(null);

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

  const handleUploadEvidence = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
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
        setEvidenceFileName(data.file_name || file.name);
        setEvidenceFileUrl(data.file_url || "");
      } else {
        setActionMsg(data.detail || "Không thể tải file minh chứng");
      }
    } catch {
      setActionMsg("Lỗi kết nối khi tải file minh chứng");
    } finally {
      setUploadingFile(false);
    }
  };

  const openProgressModal = (t: any) => {
    setProgTask(t);
    const myAssign = t.assignees?.find(
      (a: any) => a.lecturer_id === currentUser?.id
    );
    const target = myAssign || t.assignees?.[0];
    setProgLecturerId(target ? target.lecturer_id : currentUser?.id);
    setProgPct(target?.progress_pct ?? 50);
    setProgNote("");
    setEvidenceFileName(target?.latest_evidence_name || "");
    setEvidenceFileUrl(target?.latest_evidence_url || "");
  };

  const handleSaveProgress = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!progTask) return;
    const res = await fetch(`${API_BASE}/tasks/${progTask.id}/progress`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        progress_pct: progPct,
        note: progNote,
        lecturer_id: progLecturerId,
        evidence_file_name: evidenceFileName || null,
        evidence_file_url: evidenceFileUrl || null,
      }),
    });
    const data = await res.json();
    if (res.ok) {
      setActionMsg(
        `Đã cập nhật tiến độ công việc ${progTask.code} lên ${progPct}%${
          evidenceFileName ? ` (kèm minh chứng: ${evidenceFileName})` : ""
        }`
      );
      setProgTask(null);
      setProgNote("");
      onRefresh();
    } else {
      setActionMsg(data.detail || "Không thể cập nhật tiến độ");
    }
  };

  const openDelegateModal = (t: any) => {
    setDelegateTask(t);
    setDelegateLeadId(t.lead_lecturer_id || t.assignees?.[0]?.lecturer_id || null);
    setDelegateMembers(
      (t.assignees || []).map((a: any) => ({
        lecturer_id: a.lecturer_id,
        lecturer_name: a.lecturer_name,
        member_task_note: a.member_task_note || "",
      }))
    );
    setAddMemberId("");
    setAddMemberNote("");
  };

  const handleAddMemberToGroup = () => {
    if (!addMemberId) return;
    const lid = Number(addMemberId);
    if (delegateMembers.some((m) => m.lecturer_id === lid)) return;
    const u = users.find((x) => x.id === lid);
    setDelegateMembers((prev) => [
      ...prev,
      {
        lecturer_id: lid,
        lecturer_name: u ? u.full_name : `Giảng viên #${lid}`,
        member_task_note: addMemberNote.trim() || "Phối hợp thực hiện công việc nhóm",
      },
    ]);
    setAddMemberId("");
    setAddMemberNote("");
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
      setActionMsg(data.message || "Đã cập nhật phân công nhiệm vụ trong nhóm");
      setDelegateTask(null);
      onRefresh();
    } else {
      setActionMsg(data.detail || "Không thể lưu phân việc nhóm");
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
      setActionMsg(`Đã gửi yêu cầu xin gia hạn cho công việc ${extTask.code}`);
      setExtTask(null);
      setExtReason("");
      fetchExtensions();
      onRefresh();
    } else {
      setActionMsg(data.detail || "Lỗi gửi yêu cầu gia hạn");
    }
  };

  const handleReviewExtension = async (extId: number, statusDecision: string) => {
    const res = await fetch(`${API_BASE}/tasks/extensions/${extId}/review`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        status: statusDecision,
        review_note:
          statusDecision === "Đã duyệt"
            ? "Đồng ý gia hạn và cập nhật lại hạn hoàn thành"
            : "Không đồng ý gia hạn, yêu cầu bám sát tiến độ gốc",
      }),
    });
    const data = await res.json();
    if (res.ok) {
      setActionMsg(data.message || `Đã ${statusDecision} yêu cầu gia hạn`);
      fetchExtensions();
      onRefresh();
    } else {
      setActionMsg(data.detail || "Không thể duyệt yêu cầu gia hạn");
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
      setActionMsg(data.message);
      setMapTask(null);
      onRefresh();
    } else {
      setActionMsg(data.detail || "Không thể ánh xạ danh mục Trường");
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
      a.download = `DanhSach_GiangVien_TreHan_HUIT_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
    } else {
      setActionMsg("Không thể xuất file Excel danh sách trễ hạn");
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

  const countAll = tasks.length;
  const countNew = tasks.filter((t) => t.status === "Mới giao").length;
  const countDoing = tasks.filter((t) => t.status === "Đang thực hiện").length;
  const countDone = tasks.filter((t) => t.status === "Hoàn thành").length;
  const countLate = tasks.filter(isTaskLateOrOverdue).length;

  const pendingExtCount = extensions.filter((e) => e.status === "Chờ duyệt").length;

  const filteredTasks = tasks.filter((t) => {
    if (statusFilter === "LATE") {
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
      {/* Thanh chuyển đổi Công việc <-> Phê duyệt Gia hạn & Bộ lọc */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setSubView("tasks")}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold cursor-pointer transition ${
              subView === "tasks"
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            <CheckSquare className="w-4 h-4" />
            Danh sách Công việc ({countAll})
          </button>

          <button
            onClick={() => setSubView("extensions")}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold cursor-pointer transition ${
              subView === "extensions"
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            <CalendarPlus className="w-4 h-4" />
            Quản lý & Phê duyệt Gia hạn ({extensions.length})
            {pendingExtCount > 0 && (
              <span className="px-2 py-0.5 text-[11px] rounded-full bg-rose-500 text-white font-bold">
                {pendingExtCount} chờ duyệt
              </span>
            )}
          </button>

          {currentUser?.role !== "lecturer" && (
            <button
              onClick={handleExportLateExcel}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 cursor-pointer transition"
              title="Xuất riêng file Excel danh sách những người trễ hạn với tiêu đề rõ ràng"
            >
              <FileDown className="w-4 h-4" />
              Xuất Excel DS Trễ hạn ({countLate})
            </button>
          )}
        </div>

        {subView === "tasks" && (
          <div className="flex flex-wrap items-center gap-1.5">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Tìm mã CV, tên việc, giảng viên..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8 pr-3 py-1.5 border border-slate-300 rounded-lg text-xs w-56 outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            {[
              { key: "ALL", label: `Tất cả (${countAll})` },
              { key: "Mới giao", label: `Mới giao (${countNew})` },
              { key: "Đang thực hiện", label: `Đang thực hiện (${countDoing})` },
              { key: "Hoàn thành", label: `Hoàn thành (${countDone})` },
              { key: "LATE", label: `Trễ / Quá hạn (${countLate})`, isDanger: true },
            ].map((st) => (
              <button
                key={st.key}
                onClick={() => setStatusFilter(st.key)}
                className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold cursor-pointer transition ${
                  statusFilter === st.key
                    ? st.isDanger
                      ? "bg-rose-600 text-white"
                      : "bg-slate-800 text-white"
                    : st.isDanger
                    ? "bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {actionMsg && (
        <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center justify-between">
          <span>{actionMsg}</span>
          <button
            onClick={() => setActionMsg("")}
            className="text-emerald-700 font-bold cursor-pointer px-2"
          >
            Đóng
          </button>
        </div>
      )}

      {/* BẢNG 1: DANH SÁCH CÔNG VIỆC */}
      {subView === "tasks" && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <div
            tabIndex={0}
            role="region"
            aria-labelledby="tasks-table-caption"
            className="overflow-x-auto max-h-[680px] focus:outline-2 focus:outline-blue-600"
          >
            <span id="tasks-table-caption" className="sr-only">
              Bảng danh sách công việc, tiến độ, minh chứng và thời hạn
            </span>
            <table className="w-full text-left border-collapse text-sm">
              <thead className="sticky top-0 z-10 bg-slate-50 border-b border-slate-200 text-slate-600 text-xs uppercase">
                <tr>
                  <th className="p-3.5 w-[28%]">Công việc & Danh mục</th>
                  <th className="p-3.5 w-[28%]">Giảng viên & Tiến độ (%)</th>
                  <th className="p-3.5 w-[16%]">Thời hạn & Kiểm tra</th>
                  <th className="p-3.5 w-[14%]">Dự báo Trễ hạn</th>
                  <th className="p-3.5 text-right w-[14%]">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredTasks.map((t) => {
                  const isGroup =
                    t.assignment_mode === "Group" || (t.assignees?.length || 0) >= 2;
                  const isUserLead =
                    t.lead_lecturer_id === currentUser?.id ||
                    t.assignees?.some(
                      (a: any) => a.lecturer_id === currentUser?.id && a.is_lead
                    );
                  const canDelegate =
                    isGroup &&
                    (currentUser?.role !== "lecturer" ||
                      isUserLead ||
                      t.reviewer_id === currentUser?.id);

                  return (
                    <tr key={t.id} className="hover:bg-slate-50/80 transition align-top">
                      {/* CỘT 1: THÔNG TIN CÔNG VIỆC */}
                      <td className="p-3.5">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-xs font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                            {t.code}
                          </span>
                          <span
                            className={`text-xs px-2 py-0.5 rounded font-semibold ${
                              t.priority === "Khẩn cấp" || t.priority === "Cao"
                                ? "bg-rose-100 text-rose-700"
                                : "bg-slate-100 text-slate-600"
                            }`}
                          >
                            {t.priority}
                          </span>
                          <span className="text-xs px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 font-semibold">
                            {t.conversion_hours} giờ chuẩn
                          </span>
                          {isGroup && (
                            <span className="text-xs px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
                              Nhóm ({t.assignees?.length} GV)
                            </span>
                          )}
                          {t.school_catalog_code && (
                            <span className="text-xs px-2 py-0.5 rounded bg-purple-100 text-purple-800 font-semibold">
                              Trường: {t.school_catalog_code}
                            </span>
                          )}
                        </div>
                        <p className="font-semibold text-slate-900 mt-1.5 leading-snug">
                          {t.title}
                        </p>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {t.task_type_name} • {t.scale}
                        </p>
                      </td>

                      {/* CỘT 2: GIẢNG VIÊN, VAI TRÒ NHÓM, TIẾN ĐỘ (%) & MINH CHỨNG */}
                      <td className="p-3.5">
                        <div className="space-y-2.5">
                          {t.assignees?.map((a: any) => {
                            const isLead =
                              a.is_lead || t.lead_lecturer_id === a.lecturer_id;
                            const pct = Number(a.progress_pct ?? 0);
                            return (
                              <div
                                key={a.assignment_id || a.lecturer_id}
                                className="p-2 rounded-lg bg-slate-50 border border-slate-200/80"
                              >
                                <div className="flex items-center justify-between gap-2 text-xs mb-1">
                                  <div className="flex items-center gap-1.5 flex-wrap">
                                    <span className="font-semibold text-slate-800">
                                      {a.lecturer_name}
                                    </span>
                                    {isGroup && isLead && (
                                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300 font-bold">
                                        Phụ trách chính
                                      </span>
                                    )}
                                  </div>
                                  <span className="font-bold text-blue-700 shrink-0">
                                    {pct}%
                                  </span>
                                </div>

                                <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
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
                                  <div className="text-[11px] text-slate-600 mt-1">
                                    Nhiệm vụ: <span className="italic">{a.member_task_note}</span>
                                  </div>
                                )}

                                <div className="flex items-center justify-between gap-2 mt-1">
                                  <span
                                    className={`text-[11px] font-medium ${
                                      a.status === "Hoàn thành"
                                        ? a.is_late
                                          ? "text-rose-600 font-semibold"
                                          : "text-emerald-700 font-semibold"
                                        : "text-slate-500"
                                    }`}
                                  >
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
                                      className="inline-flex items-center gap-1 text-[11px] text-emerald-700 hover:underline font-semibold truncate max-w-[160px]"
                                      title={`Xem minh chứng: ${a.latest_evidence_name}`}
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
                      </td>

                      {/* CỘT 3: THỜI HẠN & NGƯỜI KIỂM TRA TIẾN ĐỘ */}
                      <td className="p-3.5 text-xs text-slate-600 space-y-1">
                        <div>
                          Hạn gốc: <b className="text-slate-800">{t.original_deadline}</b>
                        </div>
                        <div
                          className={
                            t.current_deadline !== t.original_deadline
                              ? "text-amber-700 font-bold"
                              : ""
                          }
                        >
                          Hạn hiện tại: <b className="text-slate-900">{t.current_deadline}</b>
                        </div>
                        <div className="pt-1 border-t border-slate-100 text-[11px] text-slate-500">
                          Người kiểm tra:{" "}
                          <b className="text-slate-700">
                            {t.reviewer_name || t.creator_name || "Trưởng đơn vị"}
                          </b>
                        </div>
                        {t.pending_extensions > 0 && (
                          <span className="inline-block mt-1 px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-bold text-[11px]">
                            Đang xin gia hạn
                          </span>
                        )}
                      </td>

                      {/* CỘT 4: DỰ BÁO NGUY CƠ TRỄ HẠN */}
                      <td className="p-3.5">
                        {t.assignees?.slice(0, 1).map((a: any) => {
                          const ml = a.ml_prediction;
                          if (!ml || ml.probability === null || ml.probability === undefined) {
                            return (
                              <span
                                key={a.assignment_id || a.lecturer_id}
                                className="text-xs text-slate-400 italic"
                              >
                                Chưa có dữ liệu
                              </span>
                            );
                          }
                          return (
                            <div
                              key={a.assignment_id || a.lecturer_id}
                              className="text-xs space-y-1"
                            >
                              <span
                                className={`inline-block px-2.5 py-0.5 rounded font-bold ${
                                  ml.level === "Cao"
                                    ? "bg-rose-100 text-rose-700 border border-rose-200"
                                    : ml.level === "Trung bình"
                                    ? "bg-amber-100 text-amber-800 border border-amber-200"
                                    : "bg-emerald-100 text-emerald-700 border border-emerald-200"
                                }`}
                              >
                                Nguy cơ {ml.level}: {(Number(ml.probability) * 100).toFixed(1)}%
                              </span>
                              {ml.top_factors && ml.top_factors.length > 0 && (
                                <div className="text-[11px] text-slate-500 leading-snug">
                                  Yếu tố chính:{" "}
                                  <b className="text-slate-700">
                                    {formatFeatureName(
                                      typeof ml.top_factors[0] === "string"
                                        ? ml.top_factors[0]
                                        : ml.top_factors[0].feature
                                    )}
                                  </b>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </td>

                      {/* CỘT 5: THAO TÁC */}
                      <td className="p-3.5 text-right">
                        <div className="flex flex-col items-end gap-1.5">
                          {t.status !== "Hoàn thành" && (
                            <button
                              onClick={() => openProgressModal(t)}
                              className="px-2.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold cursor-pointer"
                            >
                              Tiến độ & Minh chứng
                            </button>
                          )}

                          {canDelegate && t.status !== "Hoàn thành" && (
                            <button
                              onClick={() => openDelegateModal(t)}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 text-xs font-semibold cursor-pointer"
                              title="Phân công nhiệm vụ cho các thành viên trong nhóm"
                            >
                              <Users className="w-3.5 h-3.5" />
                              Phân việc nhóm
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
                                className="px-2 py-1 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-800 text-xs font-semibold cursor-pointer"
                              >
                                Xin gia hạn
                              </button>
                            )}

                            {currentUser?.role !== "lecturer" && (
                              <button
                                onClick={() => {
                                  setMapTask(t);
                                  setSelectedSchoolId(
                                    t.school_catalog_id || schoolCatalog[0]?.id || 1
                                  );
                                }}
                                className="px-2 py-1 rounded-lg bg-slate-100 hover:bg-purple-50 hover:text-purple-700 text-slate-600 text-xs font-medium cursor-pointer"
                                title="Ánh xạ vào danh mục công việc cấp Trường"
                              >
                                Ánh xạ
                              </button>
                            )}

                            <button
                              onClick={() => openDetail(t.id)}
                              className="px-2 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold cursor-pointer"
                            >
                              Chi tiết
                            </button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {filteredTasks.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-slate-400 text-xs">
                      Không có công việc nào khớp với bộ lọc hiện tại.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* BẢNG 2: DANH SÁCH YÊU CẦU GIA HẠN & PHÊ DUYỆT */}
      {subView === "extensions" && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="p-4 bg-slate-50 border-b border-slate-200">
            <h3 className="font-bold text-slate-800 text-sm">
              Danh sách Yêu cầu Gia hạn Công việc & Phê duyệt
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Khi Trưởng Khoa / Trưởng Bộ môn hoặc Người kiểm tra phê duyệt gia hạn, hệ thống tự động cập nhật hạn hoàn thành hiện hành và đánh giá lại nguy cơ trễ hạn.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-100 text-slate-600 text-xs uppercase border-b">
                  <th className="p-3.5">Công việc & Người xin</th>
                  <th className="p-3.5">Lý do xin gia hạn</th>
                  <th className="p-3.5 text-center">Hạn cũ → Đề xuất</th>
                  <th className="p-3.5">Dự báo Nguy cơ hiện tại</th>
                  <th className="p-3.5 text-center">Trạng thái</th>
                  <th className="p-3.5 text-right">Xử lý</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {extensions.map((e) => (
                  <tr key={e.id} className="hover:bg-slate-50">
                    <td className="p-3.5">
                      <div className="text-xs font-mono font-bold text-blue-700">
                        {e.task_code}
                      </div>
                      <div className="font-semibold text-slate-900">{e.task_title}</div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        Giảng viên: <b>{e.requester_name}</b> • Tiến độ:{" "}
                        <b>{e.progress_pct}%</b>
                      </div>
                    </td>
                    <td className="p-3.5 text-xs text-slate-700 max-w-xs">{e.reason}</td>
                    <td className="p-3.5 text-center text-xs">
                      <div className="text-slate-500 line-through">{e.old_deadline}</div>
                      <div className="font-bold text-amber-700">
                        {e.proposed_deadline}
                      </div>
                      <span className="text-[11px] text-slate-500">
                        (+{e.extra_days} ngày)
                      </span>
                    </td>
                    <td className="p-3.5 text-xs">
                      {e.ml_prediction && e.ml_prediction.probability !== null ? (
                        <div>
                          <span
                            className={`inline-block px-2 py-0.5 rounded font-bold ${
                              e.ml_prediction.level === "Cao"
                                ? "bg-rose-100 text-rose-700"
                                : "bg-amber-100 text-amber-800"
                            }`}
                          >
                            {e.ml_prediction.level}:{" "}
                            {(e.ml_prediction.probability * 100).toFixed(1)}%
                          </span>
                          <div className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">
                            {e.ml_prediction.recommendation}
                          </div>
                        </div>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
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
                      {e.review_note && (
                        <div className="text-[11px] text-slate-500 mt-1 max-w-[180px] mx-auto">
                          {e.review_note}
                        </div>
                      )}
                    </td>
                    <td className="p-3.5 text-right">
                      {e.status === "Chờ duyệt" &&
                      currentUser?.role !== "lecturer" ? (
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
                          {e.reviewed_by_name
                            ? `Duyệt bởi ${e.reviewed_by_name}`
                            : "Đang chờ"}
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

      {/* MODAL 1: CẬP NHẬT TIẾN ĐỘ (%) & UPLOAD FILE MINH CHỨNG */}
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
            <h3 className="text-base font-bold text-slate-900">
              Cập nhật Tiến độ & Minh chứng ({progTask.code})
            </h3>
            <p className="text-xs text-slate-600">{progTask.title}</p>

            {progTask.assignees?.length > 1 && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Thành viên cập nhật tiến độ
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
                      setEvidenceFileName(found.latest_evidence_name || "");
                      setEvidenceFileUrl(found.latest_evidence_url || "");
                    }
                  }}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs bg-white font-semibold"
                >
                  {progTask.assignees.map((a: any) => (
                    <option key={a.lecturer_id} value={a.lecturer_id}>
                      {a.lecturer_name}{" "}
                      {a.is_lead || progTask.lead_lecturer_id === a.lecturer_id
                        ? "(Phụ trách chính)"
                        : ""}{" "}
                      — hiện tại {a.progress_pct}%
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div>
              <div className="flex justify-between text-xs font-semibold mb-1">
                <span>Mức hoàn thành (%)</span>
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
                    className={`flex-1 py-1 text-xs rounded font-semibold cursor-pointer ${
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

            {/* UPLOAD FILE MINH CHỨNG */}
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
              <label className="block text-xs font-semibold text-slate-700">
                Tải lên File Minh chứng kết quả tiến độ
              </label>
              <label className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-dashed border-blue-400 bg-white hover:bg-blue-50 text-xs font-semibold text-blue-700 cursor-pointer transition">
                <Upload className="w-4 h-4" />
                <span>{uploadingFile ? "Đang tải file lên..." : "Chọn file minh chứng (.pdf, .docx, .xlsx, .zip...)"}</span>
                <input
                  type="file"
                  onChange={handleUploadEvidence}
                  className="hidden"
                />
              </label>
              {evidenceFileName && (
                <div className="flex items-center justify-between text-xs bg-emerald-50 border border-emerald-200 text-emerald-800 px-2.5 py-1.5 rounded-lg">
                  <span className="truncate font-medium">
                    Đã đính kèm: <b>{evidenceFileName}</b>
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
                Ghi chú kết quả thực hiện *
              </label>
              <textarea
                value={progNote}
                onChange={(e) => setProgNote(e.target.value)}
                rows={3}
                placeholder="Nhập nội dung công việc đã thực hiện..."
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
                Lưu Tiến độ & Minh chứng
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL 2: NGƯỜI PHỤ TRÁCH CHÍNH PHÂN VIỆC TRONG NHÓM */}
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
                Phân công Nhiệm vụ Thành viên Nhóm ({delegateTask.code})
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">{delegateTask.title}</p>
            </div>

            {currentUser?.role !== "lecturer" && (
              <div className="p-3 rounded-xl bg-amber-50 border border-amber-200">
                <label className="block text-xs font-semibold text-amber-900 mb-1">
                  Người phụ trách chính (Chủ trì nhóm)
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
                Giao nhiệm vụ chi tiết cho từng thành viên ({delegateMembers.length} GV):
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
                          Phụ trách chính
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
                    />
                  </div>
                );
              })}
            </div>

            {users.length > 0 && (
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                <label className="block text-xs font-semibold text-slate-700">
                  Thêm giảng viên phối hợp vào nhóm
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <select
                    value={addMemberId}
                    onChange={(e) => setAddMemberId(e.target.value)}
                    className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs bg-white"
                  >
                    <option value="">-- Chọn giảng viên --</option>
                    {users
                      .filter(
                        (u) =>
                          u.role === "lecturer" &&
                          !delegateMembers.some((m) => m.lecturer_id === u.id)
                      )
                      .map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.full_name} ({u.department_name || "Khoa CNTT"})
                        </option>
                      ))}
                  </select>
                  <input
                    type="text"
                    value={addMemberNote}
                    onChange={(e) => setAddMemberNote(e.target.value)}
                    placeholder="Nhiệm vụ của thành viên mới..."
                    className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs bg-white"
                  />
                </div>
                <button
                  type="button"
                  onClick={handleAddMemberToGroup}
                  disabled={!addMemberId}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-900 disabled:bg-slate-300 text-white text-xs font-semibold cursor-pointer"
                >
                  + Thêm vào nhóm
                </button>
              </div>
            )}

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
                Lưu Phân công Nhóm
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL 3: GỬI YÊU CẦU GIA HẠN */}
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
                placeholder="Nêu rõ nguyên nhân khách quan / chủ quan và cam kết tiến độ..."
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
                Gửi Yêu cầu Gia hạn
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL 4: ÁNH XẠ DANH MỤC CẤP TRƯỜNG */}
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
                className="px-4 py-2 rounded-xl bg-purple-600 text-white text-xs font-semibold cursor-pointer"
              >
                Xác nhận Ánh xạ
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
                <div className="text-slate-500">Phụ trách chính</div>
                <div className="font-semibold text-amber-800 mt-0.5">
                  {detailData.lead_lecturer_name ||
                    detailData.assignees?.[0]?.lecturer_name ||
                    "—"}
                </div>
              </div>
            </div>

            <div className="text-xs text-slate-600 space-y-1">
              <div>
                Loại việc: <b>{detailData.task_type_name}</b> ({detailData.scale})
              </div>
              <div>
                Hạn gốc: <b>{detailData.original_deadline}</b> • Hạn hiện tại:{" "}
                <b>{detailData.current_deadline}</b>
              </div>
              {detailData.school_catalog_name && (
                <div className="text-purple-700 font-semibold">
                  Danh mục Trường: {detailData.school_catalog_name}
                </div>
              )}
            </div>

            {detailData.assignees && detailData.assignees.length > 0 && (
              <div className="space-y-1.5">
                <h4 className="text-xs font-bold text-slate-800 uppercase">
                  Thành viên Thực hiện ({detailData.assignees.length})
                </h4>
                {detailData.assignees.map((a: any) => (
                  <div
                    key={a.assignment_id || a.lecturer_id}
                    className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs flex flex-wrap items-center justify-between gap-2"
                  >
                    <div>
                      <span className="font-semibold text-slate-900">
                        {a.lecturer_name}
                      </span>
                      {a.is_lead && (
                        <span className="ml-1.5 px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px] font-bold">
                          Phụ trách chính
                        </span>
                      )}
                      {a.member_task_note && (
                        <div className="text-slate-600 mt-0.5">
                          Nhiệm vụ: {a.member_task_note}
                        </div>
                      )}
                    </div>
                    <div className="text-right">
                      <div className="font-bold text-blue-700">{a.progress_pct}%</div>
                      {a.latest_evidence_name && (
                        <a
                          href={
                            a.latest_evidence_url?.startsWith("http")
                              ? a.latest_evidence_url
                              : `${BACKEND_ORIGIN}${a.latest_evidence_url}`
                          }
                          target="_blank"
                          rel="noreferrer"
                          className="text-[11px] text-emerald-700 hover:underline font-semibold"
                        >
                          Minh chứng: {a.latest_evidence_name}
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

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
                            File minh chứng: {p.evidence_file_name}
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
    </div>
  );
};
export default TasksAndExtensionsView;
