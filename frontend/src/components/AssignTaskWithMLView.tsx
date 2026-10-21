import React, { useState } from "react";
import { Sparkles, CheckCircle2, Send, ChevronDown, ChevronUp } from "lucide-react";

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
  const [selectedLecturerIds, setSelectedLecturerIds] = useState<number[]>(
    lecturers[0] ? [lecturers[0].id] : []
  );

  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [expandedLecturerId, setExpandedLecturerId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [createdResult, setCreatedResult] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const currentTaskType = taskTypes.find((t) => t.id === taskTypeId);
  const currentScaleObj = currentTaskType?.scales?.find((s: any) => s.scale === scale);

  const toggleLecturer = (id: number) => {
    setSelectedLecturerIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const handlePreviewML = async (evaluateAll: boolean = true) => {
    setErrorMsg("");
    setPreviewLoading(true);
    try {
      const res = await fetch(`${API_BASE}/tasks/preview-risk`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          title: title || "Dự kiến phân công công việc",
          task_type_id: taskTypeId,
          scale,
          priority,
          complexity,
          original_deadline: deadline,
          require_external_input: requireExternal,
          lecturer_ids: evaluateAll ? null : selectedLecturerIds,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setErrorMsg(data.detail || "Không thể phân tích mức độ phù hợp");
      } else {
        setPreviewData(data);
      }
    } catch (e) {
      setErrorMsg("Lỗi kết nối tới máy chủ khi gọi gợi ý phân công");
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    setCreatedResult(null);
    if (!title.trim()) {
      setErrorMsg("Vui lòng nhập tên công việc");
      return;
    }
    if (selectedLecturerIds.length === 0) {
      setErrorMsg("Vui lòng chọn ít nhất 1 giảng viên nhận việc");
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/tasks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          title,
          description,
          task_type_id: taskTypeId,
          scale,
          school_catalog_id: schoolCatalogId === "" ? null : Number(schoolCatalogId),
          priority,
          complexity,
          original_deadline: deadline,
          require_external_input: requireExternal,
          lecturer_ids: selectedLecturerIds,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setErrorMsg(data.detail || "Lỗi khi giao việc");
      } else {
        setCreatedResult(data);
        setTitle("");
        setDescription("");
        onAssigned();
      }
    } catch (e) {
      setErrorMsg("Không thể kết nối máy chủ");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
      {/* Cột trái: Biểu mẫu Giao việc */}
      <div className="xl:col-span-5 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-5">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Send className="w-5 h-5 text-blue-600" />
            Giao việc mới (Cá nhân / Nhóm)
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Điền thông tin đầu việc và bấm <b>Gợi ý người nhận việc phù hợp</b> để hệ thống kiểm tra tải công việc hiện tại của các giảng viên trước khi giao.
          </p>
        </div>

        {errorMsg && (
          <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
            {errorMsg}
          </div>
        )}

        {createdResult && (
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 space-y-2 text-xs">
            <div className="font-bold text-sm flex items-center gap-1.5 text-emerald-800">
              <CheckCircle2 className="w-4 h-4" /> Đã giao việc thành công! Mã công việc: {createdResult.code}
            </div>
            {createdResult.predictions?.map((p: any, idx: number) => (
              <div key={idx} className="p-2.5 bg-white rounded-lg border border-emerald-200">
                <div className="font-semibold">
                  Dự báo tiến độ lúc giao:{" "}
                  <span
                    className={
                      p.level === "Cao"
                        ? "text-rose-600 font-bold"
                        : p.level === "Trung bình"
                        ? "text-amber-700 font-bold"
                        : "text-emerald-700 font-bold"
                    }
                  >
                    Nguy cơ trễ {p.level} {p.probability !== null ? `(${(p.probability * 100).toFixed(1)}%)` : ""}
                  </span>
                </div>
                <div className="text-slate-600 mt-0.5">{p.recommendation || p.notes}</div>
              </div>
            ))}
          </div>
        )}

        <form onSubmit={handleCreateTask} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Tên công việc *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="VD: Biên soạn đề cương chi tiết học phần Lập trình Web..."
              className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Danh mục công việc của Khoa
              </label>
              <select
                value={taskTypeId}
                onChange={(e) => {
                  const id = Number(e.target.value);
                  setTaskTypeId(id);
                  const found = taskTypes.find((x) => x.id === id);
                  if (found) setComplexity(found.default_complexity || "Trung bình");
                }}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm bg-white"
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
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm bg-white"
              >
                <option value="quy mô nhỏ">Quy mô nhỏ</option>
                <option value="quy mô chuẩn">Quy mô chuẩn</option>
                <option value="quy mô lớn">Quy mô lớn</option>
              </select>
              {currentScaleObj && (
                <p className="text-[11px] text-indigo-700 font-medium mt-1">
                  Thời gian chuẩn: {currentScaleObj.expected_duration_days} ngày • Quy đổi:{" "}
                  <b>{currentScaleObj.conversion_hours ?? 0} giờ chuẩn</b>
                </p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Mức độ ưu tiên</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm bg-white"
              >
                <option value="Thấp">Thấp</option>
                <option value="Trung bình">Trung bình</option>
                <option value="Cao">Cao</option>
                <option value="Khẩn cấp">Khẩn cấp</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Độ phức tạp</label>
              <select
                value={complexity}
                onChange={(e) => setComplexity(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm bg-white"
              >
                <option value="Thấp">Thấp</option>
                <option value="Trung bình">Trung bình</option>
                <option value="Cao">Cao</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Hạn hoàn thành *</label>
              <input
                type="date"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Ánh xạ danh mục công việc cấp Trường (nếu là việc do Trường giao)
            </label>
            <select
              value={schoolCatalogId}
              onChange={(e) => setSchoolCatalogId(e.target.value === "" ? "" : Number(e.target.value))}
              className="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm bg-white"
            >
              <option value="">-- Không ánh xạ (Tính theo định mức của Khoa) --</option>
              {schoolCatalog.map((sc) => (
                <option key={sc.id} value={sc.id}>
                  [{sc.code}] {sc.name} ({sc.conversion_hours} giờ chuẩn)
                </option>
              ))}
            </select>
          </div>

          <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
            <input
              type="checkbox"
              checked={requireExternal}
              onChange={(e) => setRequireExternal(e.target.checked)}
              className="rounded text-blue-600"
            />
            <span>Công việc cần phối hợp hoặc chờ dữ liệu từ phòng ban ngoài Khoa</span>
          </label>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-slate-700">
                Chọn Giảng viên thực hiện ({selectedLecturerIds.length > 1 ? "Giao việc Nhóm" : "Giao việc Cá nhân"})
              </label>
              <span className="text-[11px] text-blue-600 font-semibold">
                Đã chọn: {selectedLecturerIds.length} giảng viên
              </span>
            </div>
            <div className="max-h-44 overflow-y-auto border border-slate-200 rounded-xl divide-y divide-slate-100">
              {lecturers.map((lec) => {
                const checked = selectedLecturerIds.includes(lec.id);
                return (
                  <label
                    key={lec.id}
                    className={`flex items-center justify-between p-2.5 text-xs cursor-pointer hover:bg-slate-50 ${
                      checked ? "bg-blue-50/70" : ""
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleLecturer(lec.id)}
                        className="rounded text-blue-600"
                      />
                      <div>
                        <span className="font-semibold text-slate-800">{lec.full_name}</span>
                        <span className="text-slate-500 ml-1.5">({lec.lecturer_code || lec.username})</span>
                      </div>
                    </div>
                    <span className="text-[11px] text-slate-500">{lec.department_name}</span>
                  </label>
                );
              })}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Ghi chú / Yêu cầu sản phẩm</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Ghi chú nội dung bàn giao, mốc kiểm tra tiến độ..."
              className="w-full px-3.5 py-2 border border-slate-300 rounded-xl text-sm outline-none"
            />
          </div>

          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <button
              type="button"
              onClick={() => handlePreviewML(true)}
              disabled={previewLoading}
              className="flex-1 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white py-2.5 px-4 rounded-xl text-sm font-semibold shadow-sm transition cursor-pointer disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              {previewLoading ? "Đang phân tích tải công việc..." : "Gợi ý người nhận việc phù hợp"}
            </button>

            <button
              type="submit"
              disabled={submitting}
              className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2.5 px-4 rounded-xl text-sm font-semibold shadow-sm transition cursor-pointer disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              {submitting ? "Đang lưu..." : "Xác nhận Giao việc"}
            </button>
          </div>
        </form>
      </div>

      {/* Cột phải: Bảng Gợi ý Giảng viên Phù hợp */}
      <div className="xl:col-span-7 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-4">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-600" />
              Danh sách Gợi ý Phân công Giảng viên
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Sắp xếp tự động từ người có nguy cơ trễ hạn thấp nhất dựa trên số việc đang làm, lịch sử hoàn thành và sở trường chuyên môn.
            </p>
          </div>
          <div className="text-xs bg-slate-100 text-slate-700 px-3 py-1.5 rounded-xl font-medium border border-slate-200">
            Mức cảnh báo: Thấp &lt; 22% • Trung bình 22–44% • Cao ≥ 44%
          </div>
        </div>

        {!previewData ? (
          <div className="py-16 text-center space-y-3 text-slate-500">
            <Sparkles className="w-10 h-10 text-indigo-400 mx-auto" />
            <p className="text-sm font-medium text-slate-700">
              Chưa chạy gợi ý phân công cho công việc này
            </p>
            <p className="text-xs max-w-md mx-auto">
              Nhấn nút <b>"Gợi ý người nhận việc phù hợp"</b> ở bên trái để hệ thống kiểm tra tải công việc hiện tại của các giảng viên và đề xuất người nhận việc phù hợp nhất.
            </p>
          </div>
        ) : (
          <div className="space-y-3 max-h-[680px] overflow-y-auto pr-1">
            {previewData.candidates?.map((c: any) => {
              const isSelected = selectedLecturerIds.includes(c.lecturer_id);
              const isExpanded = expandedLecturerId === c.lecturer_id;
              return (
                <div
                  key={c.lecturer_id}
                  className={`p-4 rounded-2xl border transition ${
                    isSelected
                      ? "border-blue-500 bg-blue-50/40 ring-1 ring-blue-400"
                      : "border-slate-200 bg-slate-50/50 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div
                        className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ${
                          c.rank === 1
                            ? "bg-emerald-600 text-white"
                            : c.rank <= 3
                            ? "bg-blue-600 text-white"
                            : "bg-slate-200 text-slate-700"
                        }`}
                      >
                        #{c.rank}
                      </div>
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-bold text-slate-900 text-sm">{c.full_name}</span>
                          <span className="text-xs font-mono text-slate-500">({c.lecturer_code})</span>
                          {c.rank === 1 && (
                            <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                              ★ Gợi ý phù hợp nhất
                            </span>
                          )}
                          {c.low_confidence && (
                            <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-50 text-amber-800 border border-amber-200">
                              Giảng viên mới (dưới 5 việc lịch sử)
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-600 mt-1">
                          {c.degree} • {c.department_name} • Đang làm: <b>{c.current_open_tasks} việc</b>
                          {c.current_overdue_tasks > 0 && (
                            <span className="text-rose-600 font-semibold"> (Quá hạn: {c.current_overdue_tasks})</span>
                          )}{" "}
                          • Đã hoàn thành: <b>{c.hist_completed_count} việc</b>
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2.5">
                      <span
                        className={`inline-block px-3 py-1 rounded-xl text-xs font-bold ${
                          c.level === "Cao"
                            ? "bg-rose-100 text-rose-700 border border-rose-300"
                            : c.level === "Trung bình"
                            ? "bg-amber-100 text-amber-800 border border-amber-300"
                            : "bg-emerald-100 text-emerald-700 border border-emerald-300"
                        }`}
                      >
                        Nguy cơ trễ: {c.level} ({c.probability !== null ? `${(c.probability * 100).toFixed(1)}%` : "N/A"})
                      </span>

                      <button
                        type="button"
                        onClick={() => toggleLecturer(c.lecturer_id)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-semibold cursor-pointer transition ${
                          isSelected
                            ? "bg-blue-600 text-white"
                            : "bg-white border border-slate-300 text-slate-700 hover:bg-slate-100"
                        }`}
                      >
                        {isSelected ? "Đã chọn" : "Chọn giao"}
                      </button>
                    </div>
                  </div>

                  {/* Khuyến nghị ngắn gọn + nút Xem chi tiết phân tích */}
                  <div className="mt-2.5 pt-2.5 border-t border-slate-200/70 flex flex-wrap items-center justify-between gap-2 text-xs">
                    <div className="text-slate-700">
                      <span className="font-semibold text-slate-900">Khuyến nghị: </span>
                      {c.recommendation}
                    </div>
                    <button
                      type="button"
                      onClick={() => setExpandedLecturerId(isExpanded ? null : c.lecturer_id)}
                      className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800 font-semibold cursor-pointer shrink-0"
                    >
                      {isExpanded ? (
                        <>
                          Ẩn chi tiết <ChevronUp className="w-3.5 h-3.5" />
                        </>
                      ) : (
                        <>
                          Xem chi tiết phân tích <ChevronDown className="w-3.5 h-3.5" />
                        </>
                      )}
                    </button>
                  </div>

                  {/* Khung chi tiết phân tích (chỉ mở khi người quản lý bấm Xem chi tiết) */}
                  {isExpanded && (
                    <div className="mt-2.5 p-3 rounded-xl bg-white border border-slate-200 text-xs space-y-2">
                      <div className="flex flex-wrap items-center justify-between gap-2 text-slate-500 border-b border-slate-100 pb-1.5">
                        <span className="font-semibold text-slate-700">Các yếu tố chính ảnh hưởng đến dự báo:</span>
                        <span>
                          Tỷ lệ trễ lịch sử (làm mịn): <b>{c.hist_late_rate}%</b>
                          {c.uncertainty !== null && ` • Độ dao động dự báo: ±${(c.uncertainty * 100).toFixed(1)}%`}
                        </span>
                      </div>
                      <div className="space-y-1.5">
                        {c.top_factors && c.top_factors.length > 0 ? (
                          c.top_factors.map((f: any, i: number) => {
                            if (typeof f === "string") {
                              const isUp = f.toLowerCase().includes("tăng");
                              const isDown = f.toLowerCase().includes("giảm");
                              return (
                                <div key={i} className="flex items-start gap-1.5">
                                  <span
                                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold shrink-0 ${
                                      isUp
                                        ? "bg-rose-50 text-rose-700 border border-rose-200"
                                        : isDown
                                        ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                        : "bg-slate-100 text-slate-700 border border-slate-200"
                                    }`}
                                  >
                                    {isUp ? "▲ Yếu tố tăng nguy cơ trễ" : isDown ? "▼ Yếu tố giảm nguy cơ trễ" : "• Ghi chú"}
                                  </span>
                                  <span className="text-slate-700">
                                    {f.replace(/^(Tăng rủi ro[^:]*:|Giảm rủi ro[^:]*:)\s*/i, "")}
                                  </span>
                                </div>
                              );
                            }
                            const dVal = f.delta_logit ?? f.delta ?? 0;
                            const isUp = (f.direction || "").toLowerCase().includes("tăng") || dVal > 0;
                            return (
                              <div key={i} className="flex items-center gap-1.5">
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                    isUp
                                      ? "bg-rose-50 text-rose-700 border border-rose-200"
                                      : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                  }`}
                                >
                                  {isUp ? "▲ Tăng nguy cơ" : "▼ Giảm nguy cơ"}
                                </span>
                                <span className="text-slate-700">{formatFeatureName(f.feature)}</span>
                              </div>
                            );
                          })
                        ) : (
                          <span className="text-slate-400">Các yếu tố ở mức trung bình của Khoa</span>
                        )}
                      </div>
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
