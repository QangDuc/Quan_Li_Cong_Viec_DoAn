import React, { useState, useEffect } from "react";
import {
  Sparkles,
  CheckCircle2,
  Send,
  ChevronDown,
  ChevronUp,
  Crown,
  Filter,
  ShieldCheck,
} from "lucide-react";

import { API_BASE, formatFeatureName } from "../types";

interface Props {
  token: string;
  taskTypes: any[];
  schoolCatalog: any[];
  users: any[];
  onAssigned: () => void;
}

export const AssignTaskWithMLView: React.FC<Props> = ({
  token,
  taskTypes,
  schoolCatalog,
  users,
  onAssigned,
}) => {
  const lecturers = users.filter((u) => u.role === "lecturer" && u.is_active !== false);
  const defaultDeadline = new Date(Date.now() + 10 * 86400000).toISOString().slice(0, 10);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [taskTypeId, setTaskTypeId] = useState<number>(taskTypes[0]?.id || 1);
  const [scale, setScale] = useState<string>("quy mô chuẩn");
  const [schoolCatalogId, setSchoolCatalogId] = useState<number | "">("");
  const [priority, setPriority] = useState<string>("Cao");
  const [complexity, setComplexity] = useState<string>("Trung bình");
  const [deadline, setDeadline] = useState<string>(defaultDeadline);
  const [requireExternal, setRequireExternal] = useState<boolean>(false);
  const [reviewerId, setReviewerId] = useState<number | "">("");

  const [selectedLecturerIds, setSelectedLecturerIds] = useState<number[]>([]);
  const [leadLecturerId, setLeadLecturerId] = useState<number | null>(null);
  const [memberNotes, setMemberNotes] = useState<Record<number, string>>({});

  const [previewData, setPreviewData] = useState<any | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [createdResult, setCreatedResult] = useState<any | null>(null);
  const [expandedLecturerId, setExpandedLecturerId] = useState<number | null>(null);
  const [showLeadConditions, setShowLeadConditions] = useState<boolean>(false);

  useEffect(() => {
    if (taskTypes.length > 0 && !taskTypes.some((t) => t.id === taskTypeId)) {
      setTaskTypeId(taskTypes[0].id);
    }
  }, [taskTypes]);

  useEffect(() => {
    if (selectedLecturerIds.length === 0) {
      setLeadLecturerId(null);
    } else if (leadLecturerId === null || !selectedLecturerIds.includes(leadLecturerId)) {
      setLeadLecturerId(selectedLecturerIds[0]);
    }
  }, [selectedLecturerIds, leadLecturerId]);

  const currentTaskType = taskTypes.find((t) => t.id === taskTypeId);
  const currentScaleObj = currentTaskType?.scales?.find((s: any) => s.scale === scale);

  const toggleLecturer = (id: number) => {
    setSelectedLecturerIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handlePreviewML = async (overrideTaskTypeId?: number) => {
    setErrorMsg("");
    setPreviewLoading(true);
    try {
      const targetTypeId = overrideTaskTypeId ?? taskTypeId;
      const res = await fetch(`${API_BASE}/tasks/preview-risk`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          title: title || "Dự kiến phân công công việc",
          task_type_id: targetTypeId,
          scale,
          priority,
          complexity,
          original_deadline: deadline,
          require_external_input: requireExternal,
          lecturer_ids: null,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setErrorMsg(data.detail || "Không thể phân tích mức độ phù hợp");
      } else {
        setPreviewData(data);
      }
    } catch {
      setErrorMsg("Lỗi kết nối tới máy chủ khi gọi gợi ý phân công");
    } finally {
      setPreviewLoading(false);
    }
  };

  // Tự động chạy gợi ý lần đầu hoặc khi đổi Danh mục Nhóm công việc
  useEffect(() => {
    if (taskTypeId) {
      handlePreviewML(taskTypeId);
    }
  }, [taskTypeId]);

  const applyRecommendedLeadAndTeam = (count: number) => {
    if (!previewData?.candidates?.length) return;
    const topIds = previewData.candidates.slice(0, count).map((c: any) => c.lecturer_id);
    const recLeadId =
      previewData.recommended_lead?.lecturer_id || previewData.candidates[0]?.lecturer_id;
    if (recLeadId && !topIds.includes(recLeadId)) {
      topIds[0] = recLeadId;
    }
    setSelectedLecturerIds(topIds);
    setLeadLecturerId(recLeadId);
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    setCreatedResult(null);
    if (title.trim().length < 5) {
      setErrorMsg("Tên công việc phải có ít nhất 5 ký tự.");
      return;
    }
    if (selectedLecturerIds.length === 0) {
      setErrorMsg("Vui lòng chọn ít nhất 1 giảng viên nhận việc.");
      return;
    }
    if (
      selectedLecturerIds.length >= 2 &&
      (!leadLecturerId || !selectedLecturerIds.includes(leadLecturerId))
    ) {
      setErrorMsg(
        "Phân công nhóm (≥ 2 người) bắt buộc phải chọn 1 Người phụ trách chính (Trưởng nhóm)."
      );
      return;
    }

    setSubmitting(true);
    try {
      const cleanNotes: Record<string, string> = {};
      for (const lid of selectedLecturerIds) {
        if (memberNotes[lid]?.trim()) {
          cleanNotes[String(lid)] = memberNotes[lid].trim();
        }
      }

      const res = await fetch(`${API_BASE}/tasks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
          task_type_id: taskTypeId,
          scale,
          school_catalog_id: schoolCatalogId === "" ? null : Number(schoolCatalogId),
          priority,
          complexity,
          original_deadline: deadline,
          require_external_input: requireExternal,
          lecturer_ids: selectedLecturerIds,
          lead_lecturer_id: leadLecturerId || selectedLecturerIds[0],
          reviewer_id: reviewerId === "" ? null : Number(reviewerId),
          member_notes: cleanNotes,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setErrorMsg(data.detail || "Lỗi khi tạo công việc");
      } else {
        setCreatedResult(data);
        setTitle("");
        setDescription("");
        setSelectedLecturerIds([]);
        setMemberNotes({});
        onAssigned();
      }
    } catch {
      setErrorMsg("Lỗi kết nối tới máy chủ");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
      {/* CỘT TRÁI: BIỂU MẪU GIAO VIỆC CÓ VALIDATION RÕ RÀNG */}
      <div className="xl:col-span-5 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div className="border-b border-slate-200 pb-3">
          <h3 className="text-base font-bold text-slate-900">
            Giao Công việc Mới & Chỉ định Phụ trách chính
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Khi chọn nhóm công việc, AI bên phải sẽ tự động lọc các giảng viên thuộc đúng nhóm công việc đó có độ trễ thấp nhất.
          </p>
        </div>

        {errorMsg && (
          <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold">
            {errorMsg}
          </div>
        )}

        {createdResult && (
          <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs space-y-1">
            <div className="font-bold flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              Đã giao việc thành công! Mã công việc: {createdResult.code}
            </div>
            <div>
              Người kiểm tra tiến độ: <b>{createdResult.reviewer_name}</b>
            </div>
          </div>
        )}

        <form onSubmit={handleCreateTask} className="space-y-4">
          <div>
            <label
              htmlFor="task-title-input"
              className="block text-xs font-semibold text-slate-700 mb-1"
            >
              Tên công việc / Nhiệm vụ *
            </label>
            <input
              id="task-title-input"
              type="text"
              minLength={5}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="VD: Rà soát ngân hàng câu hỏi thi kết thúc học phần..."
              aria-describedby="task-title-hint"
              className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
            <p id="task-title-hint" className="text-[11px] text-slate-400 mt-0.5">
              Tối thiểu 5 ký tự, nêu rõ học phần hoặc nội dung công tác.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Nhóm & Danh mục công việc *
              </label>
              <select
                value={taskTypeId}
                onChange={(e) => {
                  const id = Number(e.target.value);
                  setTaskTypeId(id);
                  const found = taskTypes.find((x) => x.id === id);
                  if (found) setComplexity(found.default_complexity || "Trung bình");
                }}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs bg-white font-semibold"
              >
                {taskTypes.map((tt) => (
                  <option key={tt.id} value={tt.id}>
                    [{tt.task_group}] {tt.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Quy mô & Giờ chuẩn quy đổi
              </label>
              <select
                value={scale}
                onChange={(e) => setScale(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs bg-white font-semibold"
              >
                <option value="quy mô nhỏ">Quy mô nhỏ</option>
                <option value="quy mô chuẩn">Quy mô chuẩn</option>
                <option value="quy mô lớn">Quy mô lớn</option>
              </select>
              {currentScaleObj && (
                <p className="text-[11px] text-indigo-700 font-semibold mt-1">
                  Định mức: {currentScaleObj.expected_duration_days} ngày •{" "}
                  <b>{currentScaleObj.conversion_hours ?? 0} giờ chuẩn</b>
                </p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Mức độ ưu tiên
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs bg-white"
              >
                <option value="Thấp">Thấp</option>
                <option value="Trung bình">Trung bình</option>
                <option value="Cao">Cao</option>
                <option value="Khẩn cấp">Khẩn cấp</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Độ phức tạp
              </label>
              <select
                value={complexity}
                onChange={(e) => setComplexity(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs bg-white"
              >
                <option value="Thấp">Thấp</option>
                <option value="Trung bình">Trung bình</option>
                <option value="Cao">Cao</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Hạn hoàn thành *
              </label>
              <input
                type="date"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Người kiểm tra tiến độ
              </label>
              <select
                value={reviewerId}
                onChange={(e) =>
                  setReviewerId(e.target.value === "" ? "" : Number(e.target.value))
                }
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs bg-white"
              >
                <option value="">Mặc định: Người giao việc kiểm tra</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name} ({u.department_name || "Khoa CNTT"})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Ánh xạ danh mục cấp Trường
              </label>
              <select
                value={schoolCatalogId}
                onChange={(e) =>
                  setSchoolCatalogId(
                    e.target.value === "" ? "" : Number(e.target.value)
                  )
                }
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs bg-white"
              >
                <option value="">-- Tính theo định mức của Khoa --</option>
                {schoolCatalog.map((sc) => (
                  <option key={sc.id} value={sc.id}>
                    [{sc.code}] {sc.name} ({sc.conversion_hours}h)
                  </option>
                ))}
              </select>
            </div>
          </div>

          <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
            <input
              type="checkbox"
              checked={requireExternal}
              onChange={(e) => setRequireExternal(e.target.checked)}
              className="rounded text-blue-600"
            />
            <span>Công việc cần phối hợp hoặc chờ dữ liệu từ đơn vị ngoài Khoa</span>
          </label>

          {/* ĐỘI NGŨ GIẢNG VIÊN ĐÃ CHỌN (TINH GỌN, KHÔNG LẶP LẠI DANH SÁCH 20 NGƯỜI BÊN PHẢI) */}
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/90 space-y-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <label className="text-xs font-bold text-slate-800">
                Đội ngũ nhận việc ({selectedLecturerIds.length >= 2 ? "Làm theo Nhóm" : "Cá nhân"})
              </label>
              <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 text-[11px] font-bold">
                Đã chọn: {selectedLecturerIds.length} giảng viên
              </span>
            </div>

            {selectedLecturerIds.length === 0 ? (
              <div className="p-3 rounded-xl border border-dashed border-slate-300 bg-white text-center text-xs text-slate-500">
                Chưa chọn giảng viên — Hãy bấm <b>"Chọn giao"</b> hoặc{" "}
                <b>"⚡ Chọn nhanh Nhóm 3 GV"</b> ở bảng Gợi ý AI bên phải, hoặc chọn nhanh ở ô bên dưới.
              </div>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {selectedLecturerIds.map((lid) => {
                  const lec =
                    previewData?.candidates?.find((c: any) => c.lecturer_id === lid) ||
                    lecturers.find((x) => x.id === lid);
                  const isLead = leadLecturerId === lid;
                  return (
                    <span
                      key={lid}
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-semibold border ${
                        isLead
                          ? "bg-amber-100 text-amber-900 border-amber-300"
                          : "bg-blue-50 text-blue-800 border-blue-200"
                      }`}
                    >
                      {isLead && <Crown className="w-3.5 h-3.5 text-amber-600 shrink-0" />}
                      <span>
                        {lec?.full_name || `GV #${lid}`} ({lec?.lecturer_code || lid})
                      </span>
                      <button
                        type="button"
                        onClick={() => toggleLecturer(lid)}
                        className="ml-0.5 text-slate-400 hover:text-rose-600 font-bold cursor-pointer"
                        title="Bỏ chọn giảng viên này"
                      >
                        ✕
                      </button>
                    </span>
                  );
                })}
              </div>
            )}

            {/* Dropdown phụ nếu Quản lý muốn thêm thủ công giảng viên ngoài danh sách gợi ý */}
            <div className="flex items-center gap-2 pt-0.5">
              <select
                value=""
                onChange={(e) => {
                  const id = Number(e.target.value);
                  if (id && !selectedLecturerIds.includes(id)) {
                    toggleLecturer(id);
                  }
                }}
                className="w-full px-3 py-1.5 border border-slate-300 rounded-xl text-xs bg-white text-slate-700"
              >
                <option value="">+ Thêm thủ công giảng viên từ danh sách Khoa...</option>
                {lecturers
                  .filter((l) => !selectedLecturerIds.includes(l.id))
                  .map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.full_name} ({l.lecturer_code}) — {l.department_name || "Khoa CNTT"}
                    </option>
                  ))}
              </select>
            </div>
          </div>

          {/* KHI PHÂN CÔNG TỪ 2 NGƯỜI TRỞ LÊN: CHỌN TRƯỞNG NHÓM & PHÂN VIỆC */}
          {selectedLecturerIds.length >= 2 && (
            <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200 space-y-2.5">
              <div className="text-xs font-bold text-amber-900">
                Phân công Nhóm ({selectedLecturerIds.length} người) — Chỉ định 1 Trưởng nhóm (Phụ trách chính):
              </div>
              <div className="space-y-2">
                {selectedLecturerIds.map((lid) => {
                  const lec =
                    lecturers.find((x) => x.id === lid) ||
                    previewData?.candidates?.find((c: any) => c.lecturer_id === lid);
                  const isLead = leadLecturerId === lid;
                  return (
                    <div
                      key={lid}
                      className={`p-2.5 rounded-lg bg-white border ${
                        isLead ? "border-amber-400" : "border-slate-200"
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs">
                        <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-800">
                          <input
                            type="radio"
                            name="leadLecturer"
                            checked={isLead}
                            onChange={() => setLeadLecturerId(lid)}
                            className="accent-amber-600"
                          />
                          <span>{lec?.full_name || `GV #${lid}`}</span>
                        </label>
                        {isLead && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-300 font-bold">
                            Trưởng nhóm (Phụ trách chính)
                          </span>
                        )}
                      </div>
                      <input
                        type="text"
                        value={memberNotes[lid] || ""}
                        onChange={(e) =>
                          setMemberNotes((prev) => ({
                            ...prev,
                            [lid]: e.target.value,
                          }))
                        }
                        placeholder={
                          isLead
                            ? "Nhiệm vụ của Trưởng nhóm (nộp minh chứng chính thức, điều phối)..."
                            : "Nhiệm vụ cụ thể giao cho thành viên này (nộp minh chứng lên Trưởng nhóm)..."
                        }
                        className="mt-1.5 w-full px-2.5 py-1 border border-slate-200 rounded text-[11px] bg-slate-50 focus:bg-white outline-none"
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Ghi chú / Yêu cầu sản phẩm minh chứng
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Ghi chú nội dung bàn giao, yêu cầu file minh chứng..."
              className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-xs outline-none"
            />
          </div>

          <div className="flex flex-col sm:flex-row gap-3 pt-1">
            <button
              type="button"
              onClick={() => handlePreviewML()}
              disabled={previewLoading}
              className="flex-1 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white py-2.5 px-4 rounded-xl text-xs font-bold shadow-xs transition cursor-pointer disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              {previewLoading
                ? "Đang lọc giảng viên độ trễ thấp nhất..."
                : "Phân tích lại Gợi ý AI"}
            </button>

            <button
              type="submit"
              disabled={submitting}
              className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2.5 px-4 rounded-xl text-xs font-bold shadow-xs transition cursor-pointer disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              {submitting ? "Đang lưu..." : "Xác nhận Giao việc"}
            </button>
          </div>
        </form>
      </div>

      {/* CỘT PHẢI: GỢI Ý GIẢNG VIÊN TRONG NHÓM VIỆC ĐỘ TRỄ THẤP NHẤT & ĐIỀU KIỆN CHỌN PHỤ TRÁCH CHÍNH */}
      <div className="xl:col-span-7 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-600" />
              Gợi ý AI: Giảng viên Độ trễ Thấp nhất & Phụ trách chính
            </h3>
            <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-indigo-600" />
              Chỉ lọc giảng viên thuộc nhóm công việc:{" "}
              <span className="px-2 py-0.5 rounded bg-indigo-50 text-indigo-800 border border-indigo-200 font-bold">
                {previewData?.selected_task_group ||
                  currentTaskType?.task_group ||
                  "Giảng dạy"}
              </span>{" "}
              có xác suất trễ hạn dự báo thấp nhất.
            </p>
          </div>

          {previewData?.candidates?.length >= 2 && (
            <button
              type="button"
              onClick={() => applyRecommendedLeadAndTeam(3)}
              className="px-3 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold shadow-2xs cursor-pointer transition"
            >
              ⚡ Chọn nhanh Nhóm Gợi ý
            </button>
          )}
        </div>

        {/* KHỐI NỔI BẬT: GỢI Ý NGƯỜI PHỤ TRÁCH CHÍNH & 4 ĐIỀU KIỆN ĐÁNH GIÁ */}
        {previewData?.recommended_lead && (
          <div className="p-4 rounded-2xl bg-gradient-to-br from-amber-50 via-orange-50/40 to-white border-2 border-amber-300 space-y-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-500 text-white flex items-center justify-center shrink-0 shadow-xs">
                  <Crown className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-extrabold uppercase tracking-wide text-amber-800">
                      Đề xuất Người Phụ trách chính (Trưởng nhóm)
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-200/80 text-amber-950">
                      Điểm tiêu chí: {previewData.recommended_lead.lead_score}/100
                    </span>
                  </div>
                  <div className="text-sm font-extrabold text-slate-900 mt-0.5">
                    {previewData.recommended_lead.full_name} (
                    {previewData.recommended_lead.lecturer_code}) —{" "}
                    <span className="text-emerald-700">
                      Nguy cơ trễ thấp nhất:{" "}
                      {(previewData.recommended_lead.probability * 100).toFixed(1)}%
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mt-0.5">
                    {previewData.recommended_lead.reason_summary}
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => {
                  const lid = previewData.recommended_lead.lecturer_id;
                  if (!selectedLecturerIds.includes(lid)) {
                    setSelectedLecturerIds((prev) => [lid, ...prev]);
                  }
                  setLeadLecturerId(lid);
                }}
                className="px-3 py-1.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold cursor-pointer shrink-0"
              >
                Chọn làm Phụ trách chính
              </button>
            </div>

            {/* 4 ĐIỀU KIỆN ĐỂ AI GỢI Ý PHỤ TRÁCH CHÍNH (THU GỌN MẶC ĐỊNH ĐỂ KHÔNG ĐẨY DANH SÁCH XUỐNG DƯỚI) */}
            <div className="bg-white/90 rounded-xl px-3 py-2 border border-amber-200/80">
              <div
                onClick={() => setShowLeadConditions(!showLeadConditions)}
                className="flex items-center justify-between cursor-pointer select-none"
              >
                <div className="text-[11px] font-bold text-slate-700 uppercase flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Tiêu chí xét duyệt Người Phụ trách chính</span>
                </div>
                <span className="text-[11px] font-bold text-amber-800 flex items-center gap-1">
                  {showLeadConditions ? (
                    <>
                      Thu gọn <ChevronUp className="w-3.5 h-3.5" />
                    </>
                  ) : (
                    <>
                      Xem chi tiết <ChevronDown className="w-3.5 h-3.5" />
                    </>
                  )}
                </span>
              </div>
              {showLeadConditions && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2 pt-2 border-t border-amber-100">
                  {previewData.recommended_lead.conditions?.map(
                    (cond: any, idx: number) => (
                      <div
                        key={idx}
                        className="p-2 rounded-lg bg-slate-50 border border-slate-200/80 text-xs flex items-start gap-2"
                      >
                        <span
                          className={`mt-0.5 w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${
                            cond.passed
                              ? "bg-emerald-100 text-emerald-700"
                              : "bg-amber-100 text-amber-800"
                          }`}
                        >
                          {cond.passed ? "✓" : "!"}
                        </span>
                        <div>
                          <div className="font-bold text-slate-800 text-[11px]">
                            {cond.criterion}
                          </div>
                          <div className="text-[11px] text-slate-600">{cond.detail}</div>
                        </div>
                      </div>
                    )
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* DANH SÁCH GIẢNG VIÊN TRONG NHÓM VIỆC CÓ ĐỘ TRỄ THẤP NHẤT */}
        {!previewData ? (
          <div className="py-12 text-center text-xs text-slate-500">
            Đang tải danh sách giảng viên có độ trễ thấp nhất...
          </div>
        ) : (
          <div className="space-y-2.5 max-h-[460px] overflow-y-auto pr-1">
            {previewData.candidates?.map((c: any) => {
              const isSelected = selectedLecturerIds.includes(c.lecturer_id);
              const isLead = isSelected && leadLecturerId === c.lecturer_id;
              const isExpanded = expandedLecturerId === c.lecturer_id;

              return (
                <div
                  key={c.lecturer_id}
                  className={`p-3.5 rounded-2xl border transition ${
                    isSelected
                      ? "border-blue-500 bg-blue-50/40 ring-1 ring-blue-400"
                      : "border-slate-200 bg-slate-50/50 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div
                        className={`w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs ${
                          c.rank === 1
                            ? "bg-emerald-600 text-white"
                            : "bg-blue-600 text-white"
                        }`}
                      >
                        #{c.rank}
                      </div>
                      <div>
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="font-bold text-slate-900 text-sm">
                            {c.full_name}
                          </span>
                          <span className="text-xs font-mono text-slate-500">
                            ({c.lecturer_code})
                          </span>
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                            Nhóm {c.task_group_match || previewData.selected_task_group}:{" "}
                            {c.group_done_count ?? c.hist_completed_count} việc
                          </span>
                          {c.is_recommended_lead && (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                              ★ Gợi ý Phụ trách chính
                            </span>
                          )}
                          {selectedLecturerIds.length >= 2 && isLead && (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500 text-white">
                              Đang chọn làm Trưởng nhóm
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-600 mt-1">
                          {c.degree} • {c.department_name} • Đang mở:{" "}
                          <b>{c.current_open_tasks} việc</b> • Đúng hạn nhóm này:{" "}
                          <b className="text-emerald-700">
                            {c.group_on_time_rate ?? (100 - (c.hist_late_rate || 0)).toFixed(1)}%
                          </b>
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      {(() => {
                        const p =
                          c.probability !== null && c.probability !== undefined
                            ? Number(c.probability)
                            : 0.12;
                        const isHigh = p >= 0.52 || c.level === "Cao";
                        const isMed =
                          !isHigh && (p >= 0.23 || c.level === "Trung bình");
                        const badgeCls = isHigh
                          ? "bg-rose-100 text-rose-800 border-rose-300"
                          : isMed
                          ? "bg-amber-100 text-amber-800 border-amber-300"
                          : "bg-emerald-100 text-emerald-800 border-emerald-300";
                        const lvlLabel = isHigh
                          ? "Cao"
                          : isMed
                          ? "Trung bình"
                          : "Thấp";
                        const isLowConf =
                          Boolean(c.low_confidence) ||
                          (c.hist_completed_count !== undefined &&
                            Number(c.hist_completed_count) < 5);

                        return (
                          <>
                            <span
                              className={`inline-block px-2.5 py-1 rounded-xl text-xs font-bold border ${badgeCls}`}
                            >
                              Rủi ro {lvlLabel}: {(p * 100).toFixed(1)}%
                            </span>
                            {isLowConf && (
                              <span
                                className="px-2 py-0.5 rounded-lg bg-amber-50 text-amber-800 border border-amber-200 text-[10px] font-bold"
                                title="Giảng viên mới (<5 việc lịch sử) hoặc thiếu trường đặc trưng — Tiên lượng dựa trên tỷ lệ Bộ môn"
                              >
                                ⚠️ Ít lịch sử
                              </span>
                            )}
                          </>
                        );
                      })()}

                      {isSelected && selectedLecturerIds.length >= 2 && !isLead && (
                        <button
                          type="button"
                          onClick={() => setLeadLecturerId(c.lecturer_id)}
                          className="px-2.5 py-1.5 rounded-xl text-xs font-semibold bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 cursor-pointer"
                        >
                          Đặt Trưởng nhóm
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => toggleLecturer(c.lecturer_id)}
                        className={`h-8 px-3 rounded-xl text-xs font-semibold border cursor-pointer transition ${
                          isSelected
                            ? "bg-blue-600 border-blue-600 text-white"
                            : "bg-white border-slate-300 text-slate-700 hover:bg-slate-100"
                        }`}
                      >
                        {isSelected ? "Đã chọn" : "Chọn giao"}
                      </button>
                    </div>
                  </div>

                  <div className="mt-2 pt-2 border-t border-slate-200/70 flex flex-wrap items-center justify-between gap-2 text-xs">
                    <span className="text-slate-600">{c.recommendation}</span>
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedLecturerId(isExpanded ? null : c.lecturer_id)
                      }
                      className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800 font-semibold cursor-pointer shrink-0"
                    >
                      {isExpanded ? (
                        <>
                          Ẩn điều kiện <ChevronUp className="w-3.5 h-3.5" />
                        </>
                      ) : (
                        <>
                          Xem điều kiện & yếu tố AI <ChevronDown className="w-3.5 h-3.5" />
                        </>
                      )}
                    </button>
                  </div>

                  {isExpanded && (
                    <div className="mt-2 p-3 rounded-xl bg-white border border-slate-200 text-xs space-y-2">
                      {c.lead_conditions && (
                        <div className="space-y-1">
                          <div className="font-bold text-slate-700">
                            Đánh giá điều kiện Phụ trách chính (Điểm: {c.lead_score}/100):
                          </div>
                          {c.lead_conditions.map((lc: any, i: number) => (
                            <div key={i} className="text-slate-600 flex items-center gap-1.5">
                              <span className="text-emerald-600 font-bold">✓</span>
                              <span>
                                <b>{lc.criterion}:</b> {lc.detail}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                      {c.top_factors && c.top_factors.length > 0 && (
                        <div className="pt-1 border-t border-slate-100 flex flex-wrap gap-1.5">
                          {c.top_factors.map((f: any, i: number) => (
                            <span
                              key={i}
                              className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[11px]"
                            >
                              {formatFeatureName(
                                typeof f === "string" ? f : f.feature
                              )}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default AssignTaskWithMLView;
