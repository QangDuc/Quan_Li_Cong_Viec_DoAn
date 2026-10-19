import React, { useEffect, useState } from "react";
import {
  FileSpreadsheet, Upload, Download, Plus, BookOpen, Award, Eye, Pencil, Check, X
} from "lucide-react";

import { API_BASE } from "../types";

interface Props {
  token: string;
  currentUser: any;
  users: any[];
  taskTypes: any[];
  schoolCatalog: any[];
  onRefresh: () => void;
}

export const PlansAndCatalogView: React.FC<Props> = ({
  token,
  currentUser,
  users,
  taskTypes,
  schoolCatalog,
  onRefresh,
}) => {
  const lecturers = users.filter((u) => u.role === "lecturer");
  const [selectedLecturerId, setSelectedLecturerId] = useState<number>(
    lecturers.find((u) => u.username === "gv_k01_1")?.id || lecturers[0]?.id || 0
  );
  const [academicYear, setAcademicYear] = useState("2026-2027");
  const [file, setFile] = useState<File | null>(null);
  const [previewRows, setPreviewRows] = useState<any[] | null>(null);
  const [importMsg, setImportMsg] = useState("");
  const [plans, setPlans] = useState<any[]>([]);

  // Form thêm danh mục cấp Trường
  const [newCode, setNewCode] = useState("");
  const [newName, setNewName] = useState("");
  const [newHours, setNewHours] = useState("15");
  const [newNote, setNewNote] = useState("");
  const [catalogMsg, setCatalogMsg] = useState("");

  // Chỉnh sửa trực tiếp định mức giờ chuẩn (theo Thông tư 20/2020/TT-BGDĐT & Quy chế nội bộ)
  const [editingTaskTypeId, setEditingTaskTypeId] = useState<number | null>(null);
  const [editSmallHrs, setEditSmallHrs] = useState("4");
  const [editSmallDays, setEditSmallDays] = useState("3");
  const [editStdHrs, setEditStdHrs] = useState("6");
  const [editStdDays, setEditStdDays] = useState("5");
  const [editLargeHrs, setEditLargeHrs] = useState("8");
  const [editLargeDays, setEditLargeDays] = useState("7");
  const [scaleSaveMsg, setScaleSaveMsg] = useState("");

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      const res = await fetch(`${API_BASE}/reports/plans`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setPlans(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const handleDownloadTemplate = async () => {
    const res = await fetch(`${API_BASE}/reports/plans/template`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "Mau_KeHoach_CongViec_Nam_2026_2027.xlsx";
      a.click();
    }
  };

  const handlePreviewExcel = async () => {
    if (!file) return;
    setImportMsg("");
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${API_BASE}/reports/plans/preview`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    });
    if (res.ok) {
      const data = await res.json();
      setPreviewRows(data.rows || []);
    } else {
      const err = await res.json();
      setImportMsg(err.detail || "Không thể đọc file Excel");
    }
  };

  const handleConfirmImport = async () => {
    if (!file || !selectedLecturerId) return;
    setImportMsg("");
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(
      `${API_BASE}/reports/plans/import?lecturer_id=${selectedLecturerId}&academic_year=${academicYear}`,
      {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      }
    );
    const data = await res.json();
    if (res.ok) {
      setImportMsg(data.message);
      setPreviewRows(null);
      setFile(null);
      fetchPlans();
      onRefresh();
    } else {
      setImportMsg(data.detail || "Import thất bại");
    }
  };

  const handleAddSchoolCatalog = async (e: React.FormEvent) => {
    e.preventDefault();
    setCatalogMsg("");
    const res = await fetch(`${API_BASE}/reports/school-catalog`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        code: newCode.trim().toUpperCase(),
        name: newName.trim(),
        conversion_hours: Number(newHours),
        note: newNote.trim(),
      }),
    });
    const data = await res.json();
    if (res.ok) {
      setCatalogMsg(data.message);
      setNewCode("");
      setNewName("");
      setNewNote("");
      onRefresh();
    } else {
      setCatalogMsg(data.detail || "Lỗi thêm danh mục Trường");
    }
  };

  const startEditScale = (tt: any) => {
    const sSmall = tt.scales?.find((s: any) => s.scale === "quy mô nhỏ");
    const sStd = tt.scales?.find((s: any) => s.scale === "quy mô chuẩn");
    const sLarge = tt.scales?.find((s: any) => s.scale === "quy mô lớn");
    setEditingTaskTypeId(tt.id);
    setEditSmallHrs(String(sSmall?.conversion_hours ?? 4));
    setEditSmallDays(String(sSmall?.expected_duration_days ?? 3));
    setEditStdHrs(String(sStd?.conversion_hours ?? 6));
    setEditStdDays(String(sStd?.expected_duration_days ?? 5));
    setEditLargeHrs(String(sLarge?.conversion_hours ?? 8));
    setEditLargeDays(String(sLarge?.expected_duration_days ?? 7));
    setScaleSaveMsg("");
  };

  const saveEditScale = async (taskTypeId: number) => {
    setScaleSaveMsg("");
    const res = await fetch(`${API_BASE}/common/task-types/${taskTypeId}/scales`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        scales: [
          {
            scale: "quy mô nhỏ",
            conversion_hours: Number(editSmallHrs),
            expected_duration_days: Number(editSmallDays),
          },
          {
            scale: "quy mô chuẩn",
            conversion_hours: Number(editStdHrs),
            expected_duration_days: Number(editStdDays),
          },
          {
            scale: "quy mô lớn",
            conversion_hours: Number(editLargeHrs),
            expected_duration_days: Number(editLargeDays),
          },
        ],
      }),
    });
    const data = await res.json();
    if (res.ok) {
      setScaleSaveMsg(data.message);
      setEditingTaskTypeId(null);
      onRefresh();
    } else {
      setScaleSaveMsg(data.detail || "Không thể lưu định mức giờ chuẩn");
    }
  };

  const isManagerOrAdmin = currentUser?.role !== "lecturer";

  return (
    <div className="space-y-6">
      {/* PHẦN 1: IMPORT KẾ HOẠCH NĂM */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-5 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5 text-emerald-600" />
              Nhập Kế hoạch Công việc Năm từ Excel
            </h3>
            <button
              type="button"
              onClick={handleDownloadTemplate}
              className="flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:text-blue-800 bg-blue-50 px-3 py-1.5 rounded-lg border border-blue-200 cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" /> Tải file Excel mẫu
            </button>
          </div>
          <p className="text-xs text-slate-500">
            Nhập danh sách đầu việc kế hoạch năm của giảng viên từ file Excel (`.xlsx`), kiểm tra trước khi lưu và tự động thiết lập lịch nhắc hạn.
          </p>

          {importMsg && (
            <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold">
              {importMsg}
            </div>
          )}

          {isManagerOrAdmin ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Giảng viên</label>
                  <select
                    value={selectedLecturerId}
                    onChange={(e) => setSelectedLecturerId(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs bg-white"
                  >
                    {lecturers.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name} ({u.lecturer_code || u.username})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Năm học</label>
                  <select
                    value={academicYear}
                    onChange={(e) => setAcademicYear(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl text-xs bg-white"
                  >
                    <option value="2026-2027">2026-2027</option>
                    <option value="2027-2028">2027-2028</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Chọn file Excel (.xlsx)</label>
                <input
                  type="file"
                  accept=".xlsx"
                  onChange={(e) => {
                    setFile(e.target.files?.[0] || null);
                    setPreviewRows(null);
                  }}
                  className="w-full text-xs text-slate-600 file:mr-3 file:py-2 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200"
                />
              </div>

              <div className="flex gap-2 pt-1">
                <button
                  type="button"
                  disabled={!file}
                  onClick={handlePreviewExcel}
                  className="flex-1 flex items-center justify-center gap-1.5 bg-slate-800 hover:bg-slate-900 text-white py-2 px-3 rounded-xl text-xs font-semibold disabled:opacity-40 cursor-pointer"
                >
                  <Eye className="w-3.5 h-3.5" /> 1. Xem trước & Kiểm tra
                </button>
                <button
                  type="button"
                  disabled={!file}
                  onClick={handleConfirmImport}
                  className="flex-1 flex items-center justify-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white py-2 px-3 rounded-xl text-xs font-semibold disabled:opacity-40 cursor-pointer"
                >
                  <Upload className="w-3.5 h-3.5" /> 2. Xác nhận Import
                </button>
              </div>

              {previewRows && (
                <div className="mt-3 border border-slate-200 rounded-xl overflow-hidden">
                  <div className="bg-slate-100 px-3 py-2 text-xs font-bold text-slate-700">
                    Xem trước {previewRows.length} dòng dữ liệu từ file Excel:
                  </div>
                  <div className="max-h-48 overflow-y-auto divide-y divide-slate-100 text-xs">
                    {previewRows.map((r, i) => (
                      <div key={i} className="p-2.5 flex items-center justify-between">
                        <div>
                          <div className="font-semibold text-slate-800">{r.title}</div>
                          <div className="text-slate-500">
                            Loại: {r.matched_task_type} • Quy mô: {r.scale}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-mono font-bold text-blue-700">{r.deadline}</div>
                          <div className="text-slate-500">{r.priority}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-xs text-slate-500 italic">
              Chức năng tải lên file Excel Kế hoạch năm dành cho Trưởng Khoa / Trưởng Bộ môn. Giảng viên có thể xem danh sách kế hoạch năm của mình ở bảng bên phải.
            </div>
          )}
        </div>

        {/* Danh sách Kế hoạch năm đã Import */}
        <div className="lg:col-span-7 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <h3 className="text-base font-bold text-slate-900">
            Danh sách Kế hoạch Công tác Năm đã Import ({plans.length})
          </h3>
          <div className="space-y-3 max-h-96 overflow-y-auto">
            {plans.map((p) => (
              <div key={p.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <span className="font-bold text-slate-900 text-sm">{p.lecturer_name}</span>
                    <span className="ml-2 px-2 py-0.5 rounded bg-blue-100 text-blue-800 text-xs font-semibold">
                      Năm học {p.academic_year}
                    </span>
                  </div>
                  <span className="text-xs font-semibold text-emerald-700">
                    Hoàn thành: {p.completed_tasks}/{p.total_tasks} đầu việc kế hoạch
                  </span>
                </div>
                <p className="text-xs text-slate-500">
                  File nguồn: <span className="font-mono text-slate-700">{p.file_name}</span> • Người nhập:{" "}
                  {p.imported_by_name}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* PHẦN 2: DANH MỤC CÔNG VIỆC CẤP TRƯỜNG & BẢNG ĐỊNH MỨC GIỜ CHUẨN QUY ĐỔI */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-5 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Award className="w-5 h-5 text-purple-600" />
            Danh mục Công việc Cấp Trường & Ánh xạ
          </h3>
          <p className="text-xs text-slate-500">
            Các nhiệm vụ cấp Trường (coi thi quốc gia, đoàn kiểm định, hội đồng Trường...) được ánh xạ để tính đúng số giờ chuẩn quy đổi theo quyết định của Trường.
          </p>
          <div className="space-y-2.5">
            {schoolCatalog.map((sc) => (
              <div
                key={sc.id}
                className="p-3 rounded-xl border border-slate-200 flex items-center justify-between hover:bg-slate-50"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-purple-100 text-purple-800 font-mono text-xs font-bold">
                      {sc.code}
                    </span>
                    <span className="font-semibold text-slate-800 text-sm">{sc.name}</span>
                  </div>
                  {sc.note && <p className="text-xs text-slate-500 mt-0.5">{sc.note}</p>}
                </div>
                <div className="text-right">
                  <div className="font-bold text-indigo-700 text-sm">{sc.conversion_hours} giờ chuẩn</div>
                  <div className="text-[11px] text-slate-500">Đã ánh xạ: {sc.mapped_task_count || 0} việc</div>
                </div>
              </div>
            ))}
          </div>

          {isManagerOrAdmin && (
            <form onSubmit={handleAddSchoolCatalog} className="pt-3 border-t border-slate-200 space-y-3">
              <div className="text-xs font-bold text-slate-700">Thêm Danh mục Công việc Cấp Trường mới:</div>
              {catalogMsg && <div className="text-xs text-emerald-700 font-semibold">{catalogMsg}</div>}
              <div className="grid grid-cols-3 gap-2">
                <input
                  type="text"
                  placeholder="Mã (VD: TR-06)"
                  value={newCode}
                  onChange={(e) => setNewCode(e.target.value)}
                  className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs"
                  required
                />
                <input
                  type="number"
                  step="0.5"
                  placeholder="Giờ chuẩn"
                  value={newHours}
                  onChange={(e) => setNewHours(e.target.value)}
                  className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs"
                  required
                />
                <button
                  type="submit"
                  className="bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1 cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" /> Thêm mục
                </button>
              </div>
              <input
                type="text"
                placeholder="Tên danh mục công việc cấp Trường..."
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs"
                required
              />
            </form>
          )}
        </div>

        {/* Bảng 35 Loại công việc cấp Khoa & Chỉnh sửa trực tiếp định mức giờ chuẩn */}
        <div className="lg:col-span-7 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-blue-600" />
                Bảng Định mức Giờ chuẩn Quy đổi của Khoa CNTT (35 danh mục)
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Thiết lập theo khung <b>Thông tư 20/2020/TT-BGDĐT</b> của Bộ GD&amp;ĐT (định mức 270 giờ chuẩn giảng dạy / 1.760 giờ hành chính/năm học).{" "}
                {isManagerOrAdmin && "Bấm 'Sửa' ở từng dòng để điều chỉnh giờ chuẩn theo Quy chế nội bộ của Trường."}
              </p>
            </div>
          </div>

          {scaleSaveMsg && (
            <div className="p-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold">
              {scaleSaveMsg}
            </div>
          )}

          <div className="max-h-[460px] overflow-y-auto border border-slate-200 rounded-xl">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-slate-100 text-slate-600 uppercase sticky top-0">
                <tr>
                  <th className="p-3">Loại công việc</th>
                  <th className="p-3">Nhóm</th>
                  <th className="p-3 text-center">Quy mô nhỏ</th>
                  <th className="p-3 text-center">Quy mô chuẩn</th>
                  <th className="p-3 text-center">Quy mô lớn</th>
                  {isManagerOrAdmin && <th className="p-3 text-center">Tùy chỉnh</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {taskTypes.map((tt) => {
                  const sSmall = tt.scales?.find((s: any) => s.scale === "quy mô nhỏ");
                  const sStd = tt.scales?.find((s: any) => s.scale === "quy mô chuẩn");
                  const sLarge = tt.scales?.find((s: any) => s.scale === "quy mô lớn");
                  const isEditing = editingTaskTypeId === tt.id;

                  if (isEditing) {
                    return (
                      <tr key={tt.id} className="bg-blue-50/60">
                        <td className="p-2.5 font-bold text-slate-900">{tt.name}</td>
                        <td className="p-2.5 text-slate-600">{tt.task_group}</td>
                        <td className="p-2 text-center space-y-1">
                          <div className="flex items-center justify-center gap-1">
                            <input
                              type="number"
                              step="0.5"
                              value={editSmallHrs}
                              onChange={(e) => setEditSmallHrs(e.target.value)}
                              className="w-14 px-1.5 py-1 border border-slate-300 rounded text-center bg-white font-bold"
                              title="Giờ chuẩn (Quy mô nhỏ)"
                            />
                            <span>h</span>
                          </div>
                          <div className="flex items-center justify-center gap-1 text-[11px] text-slate-500">
                            <input
                              type="number"
                              step="1"
                              value={editSmallDays}
                              onChange={(e) => setEditSmallDays(e.target.value)}
                              className="w-12 px-1 py-0.5 border border-slate-300 rounded text-center bg-white"
                              title="Số ngày chuẩn (Quy mô nhỏ)"
                            />
                            <span>ngày</span>
                          </div>
                        </td>
                        <td className="p-2 text-center space-y-1">
                          <div className="flex items-center justify-center gap-1">
                            <input
                              type="number"
                              step="0.5"
                              value={editStdHrs}
                              onChange={(e) => setEditStdHrs(e.target.value)}
                              className="w-14 px-1.5 py-1 border border-blue-400 rounded text-center bg-white font-bold text-blue-700"
                              title="Giờ chuẩn (Quy mô chuẩn)"
                            />
                            <span>h</span>
                          </div>
                          <div className="flex items-center justify-center gap-1 text-[11px] text-slate-500">
                            <input
                              type="number"
                              step="1"
                              value={editStdDays}
                              onChange={(e) => setEditStdDays(e.target.value)}
                              className="w-12 px-1 py-0.5 border border-slate-300 rounded text-center bg-white"
                              title="Số ngày chuẩn (Quy mô chuẩn)"
                            />
                            <span>ngày</span>
                          </div>
                        </td>
                        <td className="p-2 text-center space-y-1">
                          <div className="flex items-center justify-center gap-1">
                            <input
                              type="number"
                              step="0.5"
                              value={editLargeHrs}
                              onChange={(e) => setEditLargeHrs(e.target.value)}
                              className="w-14 px-1.5 py-1 border border-indigo-400 rounded text-center bg-white font-bold text-indigo-700"
                              title="Giờ chuẩn (Quy mô lớn)"
                            />
                            <span>h</span>
                          </div>
                          <div className="flex items-center justify-center gap-1 text-[11px] text-slate-500">
                            <input
                              type="number"
                              step="1"
                              value={editLargeDays}
                              onChange={(e) => setEditLargeDays(e.target.value)}
                              className="w-12 px-1 py-0.5 border border-slate-300 rounded text-center bg-white"
                              title="Số ngày chuẩn (Quy mô lớn)"
                            />
                            <span>ngày</span>
                          </div>
                        </td>
                        <td className="p-2 text-center">
                          <div className="flex items-center justify-center gap-1">
                            <button
                              type="button"
                              onClick={() => saveEditScale(tt.id)}
                              className="p-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 cursor-pointer"
                              title="Lưu định mức"
                            >
                              <Check className="w-3.5 h-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={() => setEditingTaskTypeId(null)}
                              className="p-1.5 rounded-lg bg-slate-200 text-slate-700 hover:bg-slate-300 cursor-pointer"
                              title="Hủy"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  }

                  return (
                    <tr key={tt.id} className="hover:bg-slate-50">
                      <td className="p-2.5 font-semibold text-slate-800">{tt.name}</td>
                      <td className="p-2.5 text-slate-500">{tt.task_group}</td>
                      <td className="p-2.5 text-center">
                        <b>{sSmall?.conversion_hours ?? 0} giờ</b>{" "}
                        <span className="text-slate-400">({sSmall?.expected_duration_days} ngày)</span>
                      </td>
                      <td className="p-2.5 text-center text-blue-700">
                        <b>{sStd?.conversion_hours ?? 0} giờ</b>{" "}
                        <span className="text-slate-400">({sStd?.expected_duration_days} ngày)</span>
                      </td>
                      <td className="p-2.5 text-center text-indigo-700">
                        <b>{sLarge?.conversion_hours ?? 0} giờ</b>{" "}
                        <span className="text-slate-400">({sLarge?.expected_duration_days} ngày)</span>
                      </td>
                      {isManagerOrAdmin && (
                        <td className="p-2.5 text-center">
                          <button
                            type="button"
                            onClick={() => startEditScale(tt)}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 font-medium cursor-pointer"
                          >
                            <Pencil className="w-3 h-3" /> Sửa
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
