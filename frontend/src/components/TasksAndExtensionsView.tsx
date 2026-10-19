import React, { useEffect, useState } from "react";
import {
  CheckSquare, CalendarPlus, Check, X, Search
} from "lucide-react";

import { API_BASE, formatFeatureName } from "../types";

interface Props {
  token: string;
  currentUser: any;
  tasks: any[];
  schoolCatalog: any[];
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
  const [actionMsg, setActionMsg] = useState<string>("");

  // Modal Cập nhật tiến độ
  const [progTask, setProgTask] = useState<any | null>(null);
  const [progPct, setProgPct] = useState<number>(50);
  const [progNote, setProgNote] = useState<string>("");

  // Modal Xin gia hạn
  const [extTask, setExtTask] = useState<any | null>(null);
  const [proposedDeadline, setProposedDeadline] = useState<string>("");
  const [extReason, setExtReason] = useState<string>("");

  // Modal Ánh xạ việc Trường
  const [mapTask, setMapTask] = useState<any | null>(null);
  const [selectedSchoolId, setSelectedSchoolId] = useState<number>(schoolCatalog[0]?.id || 1);

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
    const res = await fetch(`${API_BASE}/tasks/${taskId}/detail`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setDetailData(await res.json());
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
      body: JSON.stringify({ progress_pct: progPct, note: progNote }),
    });
    if (res.ok) {
      setActionMsg(`Đã cập nhật tiến độ công việc ${progTask.code} lên ${progPct}%`);
      setProgTask(null);
      setProgNote("");
      onRefresh();
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
      setActionMsg(`Đã gửi yêu cầu gia hạn cho công việc ${extTask.code}`);
      setExtTask(null);
      setExtReason("");
      fetchExtensions();
      onRefresh();
    } else {
      alert(data.detail || "Không thể gửi yêu cầu gia hạn");
    }
  };

  const handleReviewExtension = async (extId: number, decision: "Đã duyệt" | "Từ chối") => {
    const note =
      decision === "Đã duyệt"
        ? "Đồng ý gia hạn và cập nhật lại dự báo rủi ro ML."
        : "Không đồng ý gia hạn do cần đảm bảo tiến độ chung của Khoa.";
    const res = await fetch(`${API_BASE}/tasks/extensions/${extId}/review`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ status: decision, review_note: note }),
    });
    if (res.ok) {
      setActionMsg(`Đã ${decision.toLowerCase()} yêu cầu gia hạn #${extId}`);
      fetchExtensions();
      onRefresh();
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
    }
  };

  const pendingExtCount = extensions.filter((e) => e.status === "Chờ duyệt").length;

  const filteredTasks = tasks.filter((t) => {
    if (statusFilter !== "ALL" && t.status !== statusFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchTitle = t.title?.toLowerCase().includes(q) || t.code?.toLowerCase().includes(q);
      const matchAssignee = t.assignees?.some((a: any) => a.lecturer_name?.toLowerCase().includes(q));
      if (!matchTitle && !matchAssignee) return false;
    }
    return true;
  });

  return (
    <div className="space-y-5">
      {/* Thanh chuyển đổi Công việc <-> Phê duyệt Gia hạn */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSubView("tasks")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold cursor-pointer transition ${
              subView === "tasks"
                ? "bg-blue-600 text-white shadow-sm"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            <CheckSquare className="w-4 h-4" />
            Danh sách Công việc & Tiến độ ({tasks.length})
          </button>

          <button
            onClick={() => setSubView("extensions")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold cursor-pointer transition ${
              subView === "extensions"
                ? "bg-blue-600 text-white shadow-sm"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            <CalendarPlus className="w-4 h-4" />
            Quản lý & Phê duyệt Gia hạn ({extensions.length})
            {pendingExtCount > 0 && (
              <span className="px-2 py-0.5 text-xs rounded-full bg-rose-500 text-white font-bold">
                {pendingExtCount} chờ duyệt
              </span>
            )}
          </button>
        </div>

        {subView === "tasks" && (
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Tìm mã CV, tên việc, giảng viên..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 pr-3 py-1.5 border border-slate-300 rounded-xl text-xs w-60 outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            {["ALL", "Mới giao", "Đang thực hiện", "Hoàn thành"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold cursor-pointer ${
                  statusFilter === st
                    ? "bg-slate-900 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {st === "ALL" ? "Tất cả" : st}
              </button>
            ))}
          </div>
        )}
      </div>

      {actionMsg && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center justify-between">
          <span>{actionMsg}</span>
          <button onClick={() => setActionMsg("")} className="text-emerald-600 font-bold cursor-pointer">
            ✕
          </button>
        </div>
      )}

      {/* BẢNG 1: DANH SÁCH CÔNG VIỆC */}
      {subView === "tasks" && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 text-xs uppercase">
                  <th className="p-4">Công việc & Danh mục</th>
                  <th className="p-4">Giảng viên & Tiến độ (%)</th>
                  <th className="p-4">Thời hạn</th>
                  <th className="p-4">Dự báo Nguy cơ Trễ hạn</th>
                  <th className="p-4 text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredTasks.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-50/80 transition">
                    <td className="p-4 max-w-md">
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
                        {t.school_catalog_code && (
                          <span className="text-xs px-2 py-0.5 rounded bg-purple-100 text-purple-800 font-semibold">
                            Trường: {t.school_catalog_code}
                          </span>
                        )}
                      </div>
                      <p className="font-semibold text-slate-900 mt-1">{t.title}</p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {t.task_type_name} • {t.scale}
                      </p>
                    </td>

                    <td className="p-4">
                      {t.assignees?.map((a: any) => (
                        <div key={a.assignment_id} className="mb-2 last:mb-0">
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className="font-semibold text-slate-800">{a.lecturer_name}</span>
                            <span className="font-bold text-blue-700">{a.progress_pct}%</span>
                          </div>
                          <div className="w-36 h-2 bg-slate-200 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                a.status === "Hoàn thành"
                                  ? a.is_late
                                    ? "bg-rose-500"
                                    : "bg-emerald-500"
                                  : "bg-blue-600"
                              }`}
                              style={{ width: `${a.progress_pct}%` }}
                            />
                          </div>
                          <span className="text-[11px] text-slate-500">{a.status}</span>
                        </div>
                      ))}
                    </td>

                    <td className="p-4 text-xs text-slate-600">
                      <div>Hạn gốc: <b>{t.original_deadline}</b></div>
                      <div className={t.current_deadline !== t.original_deadline ? "text-amber-700 font-bold" : ""}>
                        Hạn hiện tại: <b>{t.current_deadline}</b>
                      </div>
                      {t.pending_extensions > 0 && (
                        <span className="inline-block mt-1 px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-bold text-[11px]">
                          Đang xin gia hạn
                        </span>
                      )}
                    </td>

                    <td className="p-4 max-w-xs">
                      {t.assignees?.map((a: any) => {
                        const ml = a.ml_prediction;
                        if (!ml) {
                          return (
                            <span key={a.assignment_id} className="text-xs text-slate-400 italic">
                              Ẩn theo phân quyền / Chưa có
                            </span>
                          );
                        }
                        return (
                          <div key={a.assignment_id} className="text-xs space-y-1">
                            <span
                              className={`inline-block px-2.5 py-0.5 rounded font-bold ${
                                ml.level === "Cao"
                                  ? "bg-rose-100 text-rose-700 border border-rose-200"
                                  : ml.level === "Trung bình"
                                  ? "bg-amber-100 text-amber-800 border border-amber-200"
                                  : "bg-emerald-100 text-emerald-700 border border-emerald-200"
                              }`}
                            >
                              Nguy cơ {ml.level}: {ml.probability !== null ? `${(ml.probability * 100).toFixed(1)}%` : "N/A"}
                            </span>
                            {ml.top_factors && ml.top_factors.length > 0 && (
                              <div className="text-[11px] text-slate-600">
                                Nguyên nhân chính: <b>{formatFeatureName(ml.top_factors[0].feature)}</b>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </td>

                    <td className="p-4 text-right">
                      <div className="flex flex-wrap items-center justify-end gap-1.5">
                        <button
                          onClick={() => openDetail(t.id)}
                          className="px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold cursor-pointer"
                          title="Xem chi tiết & Nhật ký tiến độ"
                        >
                          Chi tiết
                        </button>
                        {t.status !== "Hoàn thành" && (
                          <>
                            <button
                              onClick={() => {
                                setProgTask(t);
                                setProgPct(t.assignees?.[0]?.progress_pct || 50);
                              }}
                              className="px-2.5 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-semibold cursor-pointer"
                            >
                              Tiến độ %
                            </button>
                            <button
                              onClick={() => {
                                setExtTask(t);
                                const nextWeek = new Date(
                                  new Date(t.current_deadline).getTime() + 7 * 86400000
                                )
                                  .toISOString()
                                  .slice(0, 10);
                                setProposedDeadline(nextWeek);
                              }}
                              className="px-2.5 py-1.5 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-800 text-xs font-semibold cursor-pointer"
                            >
                              Xin gia hạn
                            </button>
                          </>
                        )}
                        {currentUser?.role !== "lecturer" && (
                          <button
                            onClick={() => {
                              setMapTask(t);
                              setSelectedSchoolId(t.school_catalog_id || schoolCatalog[0]?.id || 1);
                            }}
                            className="px-2.5 py-1.5 rounded-lg bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-semibold cursor-pointer"
                          >
                            Ánh xạ Trường
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* BẢNG 2: DANH SÁCH YÊU CẦU GIA HẠN & PHÊ DUYỆT */}
      {subView === "extensions" && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 bg-slate-50 border-b border-slate-200">
            <h3 className="font-bold text-slate-800 text-sm">
              Danh sách Yêu cầu Gia hạn Công việc & Phê duyệt
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Khi Trưởng Khoa / Trưởng Bộ môn phê duyệt gia hạn, hệ thống tự động cập nhật hạn hoàn thành hiện hành và đánh giá lại nguy cơ trễ hạn theo hạn mới.
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
                  <th className="p-3.5 text-right">Xử lý (Quản lý)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {extensions.map((e) => (
                  <tr key={e.id} className="hover:bg-slate-50">
                    <td className="p-3.5">
                      <div className="text-xs font-mono font-bold text-blue-700">{e.task_code}</div>
                      <div className="font-semibold text-slate-900">{e.task_title}</div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        Giảng viên: <b>{e.requester_name}</b> • Tiến độ: <b>{e.progress_pct}%</b>
                      </div>
                    </td>
                    <td className="p-3.5 text-xs text-slate-700 max-w-xs">{e.reason}</td>
                    <td className="p-3.5 text-center text-xs">
                      <div className="text-slate-500 line-through">{e.old_deadline}</div>
                      <div className="font-bold text-amber-700">{e.proposed_deadline}</div>
                      <span className="text-[11px] text-slate-500">(+{e.extra_days} ngày)</span>
                    </td>
                    <td className="p-3.5 text-xs">
                      {e.ml_prediction ? (
                        <div>
                          <span
                            className={`inline-block px-2 py-0.5 rounded font-bold ${
                              e.ml_prediction.level === "Cao"
                                ? "bg-rose-100 text-rose-700"
                                : "bg-amber-100 text-amber-800"
                            }`}
                          >
                            {e.ml_prediction.level}: {(e.ml_prediction.probability * 100).toFixed(1)}%
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
                        <div className="text-[11px] text-slate-500 mt-1 max-w-[180px] mx-auto">{e.review_note}</div>
                      )}
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
                          {e.reviewed_by_name ? `Duyệt bởi ${e.reviewed_by_name}` : "Đang chờ"}
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

      {/* MODAL 1: CẬP NHẬT TIẾN ĐỘ (%) */}
      {progTask && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4">
          <form
            onSubmit={handleSaveProgress}
            className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4"
          >
            <h3 className="text-base font-bold text-slate-900">
              Cập nhật Tiến độ Công việc ({progTask.code})
            </h3>
            <p className="text-xs text-slate-600">{progTask.title}</p>
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
                    className="flex-1 py-1 text-xs rounded bg-slate-100 hover:bg-slate-200 font-semibold cursor-pointer"
                  >
                    {v}%
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Ghi chú kết quả / Minh chứng</label>
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
                className="px-4 py-2 rounded-xl bg-blue-600 text-white text-xs font-semibold cursor-pointer"
              >
                Lưu Tiến độ
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL 2: GỬI YÊU CẦU GIA HẠN */}
      {extTask && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4">
          <form
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
              <label className="block text-xs font-semibold text-slate-700 mb-1">Hạn hoàn thành mới đề xuất *</label>
              <input
                type="date"
                value={proposedDeadline}
                onChange={(e) => setProposedDeadline(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Lý do xin gia hạn *</label>
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

      {/* MODAL 3: ÁNH XẠ DANH MỤC CẤP TRƯỜNG */}
      {mapTask && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4">
          <form
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

      {/* MODAL 4: XEM CHI TIẾT & NHẬT KÝ TIẾN ĐỘ */}
      {detailData && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-xl space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <span className="text-xs font-mono font-bold text-blue-700">{detailData.code}</span>
                <h3 className="text-base font-bold text-slate-900">{detailData.title}</h3>
              </div>
              <button
                onClick={() => setDetailData(null)}
                className="px-3 py-1 rounded-lg bg-slate-100 text-slate-600 text-xs font-bold cursor-pointer"
              >
                Đóng
              </button>
            </div>

            <div className="text-xs text-slate-600 space-y-1">
              <div>Loại việc: <b>{detailData.task_type_name}</b> ({detailData.scale})</div>
              <div>Hạn gốc: <b>{detailData.original_deadline}</b> • Hạn hiện tại: <b>{detailData.current_deadline}</b></div>
              {detailData.school_catalog_name && (
                <div className="text-purple-700 font-semibold">
                  Danh mục Trường: {detailData.school_catalog_name}
                </div>
              )}
            </div>

            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-800 uppercase">
                Nhật ký Cập nhật Tiến độ ({detailData.progress_logs?.length || 0})
              </h4>
              {detailData.progress_logs?.length === 0 ? (
                <p className="text-xs text-slate-400 italic">Chưa có lịch sử cập nhật tiến độ.</p>
              ) : (
                <div className="space-y-2">
                  {detailData.progress_logs.map((p: any) => (
                    <div key={p.id} className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                      <div className="flex justify-between font-semibold text-slate-800">
                        <span>{p.lecturer_name} — Đạt {p.progress_pct}%</span>
                        <span className="text-slate-500">{String(p.created_at).slice(0, 16).replace("T", " ")}</span>
                      </div>
                      <p className="text-slate-600 mt-1">{p.note}</p>
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
