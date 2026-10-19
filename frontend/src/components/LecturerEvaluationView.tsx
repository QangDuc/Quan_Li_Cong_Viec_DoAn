import React, { useEffect, useState } from "react";
import {
  Award, CheckCircle2, AlertTriangle, FileDown,
  BarChart3, ShieldAlert, Layers, Calendar, BookOpen, Check, XCircle
} from "lucide-react";

import { API_BASE, formatFeatureName } from "../types";

interface Props {
  token: string;
  currentUser: any;
  users: any[];
}

export const LecturerEvaluationView: React.FC<Props> = ({ token, currentUser, users }) => {
  const lecturers = users.filter((u) => u.role === "lecturer");
  const defaultLecturerId =
    currentUser?.role === "lecturer"
      ? currentUser.id
      : lecturers.find((u) => u.username === "gv_k01_1")?.id || lecturers[0]?.id || currentUser?.id;

  const [selectedLecturerId, setSelectedLecturerId] = useState<number>(defaultLecturerId);
  const [academicYear, setAcademicYear] = useState<string>("2026-2027");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [subTab, setSubTab] = useState<"overview" | "tasks" | "matrix" | "ml_audit">("overview");
  const [semFilter, setSemFilter] = useState<string>("ALL");

  useEffect(() => {
    if (defaultLecturerId && !selectedLecturerId) {
      setSelectedLecturerId(defaultLecturerId);
    }
  }, [defaultLecturerId]);

  useEffect(() => {
    if (!selectedLecturerId) return;
    fetchEvaluation(selectedLecturerId, academicYear);
  }, [selectedLecturerId, academicYear]);

  const fetchEvaluation = async (lecId: number, year: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/reports/lecturer-evaluation/${lecId}?academic_year=${year}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setData(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleExportLecturerExcel = async () => {
    const url = `${API_BASE}/reports/export-excel?academic_year=${academicYear}&lecturer_id=${selectedLecturerId}`;
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    if (res.ok) {
      const blob = await res.blob();
      const dlUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = dlUrl;
      a.download = `HoSo_1Nam_${data?.lecturer?.lecturer_code || selectedLecturerId}_${academicYear}.xlsx`;
      a.click();
    }
  };

  if (loading || !data) {
    return (
      <div className="bg-white rounded-2xl p-8 border border-slate-200 shadow-sm text-center text-slate-500">
        Đang tải Hồ sơ Đánh giá Công việc 1 năm của Giảng viên...
      </div>
    );
  }

  const { lecturer, summary, semesters, by_group, task_personnel_matrix, ml_audit, tasks } = data;
  const filteredTasks = semFilter === "ALL" ? tasks : tasks.filter((t: any) => t.semester === semFilter);

  return (
    <div className="space-y-6">
      {/* Thanh chọn giảng viên & năm học */}
      <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-blue-600 text-white flex items-center justify-center font-bold text-lg shadow-sm">
            {lecturer.lecturer_code?.slice(-2) || "GV"}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-900">{lecturer.full_name}</h2>
              <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                Mã GV: {lecturer.lecturer_code}
              </span>
              <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                Hồ sơ Giả lập 1 Năm ({academicYear})
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-0.5">
              {lecturer.degree} • {lecturer.academic_rank} • {lecturer.department_name} • Email: {lecturer.email}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {currentUser?.role !== "lecturer" && (
            <select
              value={selectedLecturerId}
              onChange={(e) => setSelectedLecturerId(Number(e.target.value))}
              className="px-3.5 py-2 bg-slate-50 border border-slate-300 rounded-xl text-sm font-medium text-slate-800 focus:ring-2 focus:ring-blue-500 outline-none"
            >
              {lecturers.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name} ({u.lecturer_code || u.username})
                </option>
              ))}
            </select>
          )}
          <select
            value={academicYear}
            onChange={(e) => setAcademicYear(e.target.value)}
            className="px-3.5 py-2 bg-slate-50 border border-slate-300 rounded-xl text-sm font-medium text-slate-800"
          >
            <option value="2026-2027">Năm học 2026-2027</option>
            <option value="2025-2026">Năm học 2025-2026</option>
          </select>
          <button
            onClick={handleExportLecturerExcel}
            className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-sm font-semibold shadow-sm transition cursor-pointer"
          >
            <FileDown className="w-4 h-4" /> Xuất Hồ sơ 1 Năm (.xlsx)
          </button>
        </div>
      </div>

      {/* 5 Thẻ KPI Tổng hợp 1 năm */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase">
            <span>Tổng đầu việc 1 năm</span>
            <Layers className="w-4 h-4 text-blue-600" />
          </div>
          <p className="text-3xl font-bold text-slate-900 mt-2">{summary.total_tasks}</p>
          <p className="text-xs text-slate-500 mt-1">
            Hoàn thành: <b className="text-emerald-600">{summary.completed_total}</b> ({summary.completion_rate}%) • Đang mở:{" "}
            <b className="text-blue-600">{summary.in_progress + summary.new_tasks}</b>
          </p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase">
            <span>Đúng hạn & Sớm hạn</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <p className="text-3xl font-bold text-emerald-600 mt-2">{summary.completed_on_time}</p>
          <p className="text-xs text-slate-500 mt-1">
            Tỷ lệ đúng hạn: <b>{summary.on_time_rate}%</b> (Sớm hạn: {summary.completed_early} việc)
          </p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase">
            <span>Hoàn thành trễ & Quá hạn</span>
            <AlertTriangle className="w-4 h-4 text-rose-600" />
          </div>
          <p className="text-3xl font-bold text-rose-600 mt-2">
            {summary.completed_late} <span className="text-sm font-normal text-slate-500">/ {summary.overdue_open} quá hạn mở</span>
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Sắp đến hạn (≤5 ngày): <b className="text-amber-600">{summary.due_soon_open} việc</b>
          </p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase">
            <span>Giờ chuẩn quy đổi</span>
            <Award className="w-4 h-4 text-indigo-600" />
          </div>
          <p className="text-3xl font-bold text-indigo-700 mt-2">
            {summary.total_task_converted_hours} <span className="text-sm font-normal">giờ</span>
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Cấp Khoa: <b>{summary.faculty_converted_hours}h</b> • Cấp Trường: <b>{summary.school_mapped_hours}h</b>
          </p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase">
            <span>Tỷ lệ Dự báo Khớp thực tế</span>
            <ShieldAlert className="w-4 h-4 text-purple-600" />
          </div>
          <p className="text-3xl font-bold text-purple-700 mt-2">{ml_audit.overall_accuracy}%</p>
          <p className="text-xs text-slate-500 mt-1">
            Cảnh báo đúng {ml_audit.high_risk_actual_late}/{ml_audit.high_risk_total} việc Nguy cơ Cao
          </p>
        </div>
      </div>

      {/* Thanh Sub-tabs trong Hồ sơ 1 năm */}
      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
        {[
          { id: "overview", label: "1. Tổng hợp Học kỳ & Định mức Giờ chuẩn", icon: Calendar },
          { id: "tasks", label: `2. Danh sách Công việc Cả năm (${tasks.length})`, icon: BookOpen },
          { id: "matrix", label: `3. Thống kê Năng lực theo Loại việc (${task_personnel_matrix.length})`, icon: BarChart3 },
          { id: "ml_audit", label: `4. Đối chiếu Dự báo & Thực tế (${ml_audit.records.length})`, icon: ShieldAlert },
        ].map((t) => {
          const Icon = t.icon;
          const active = subTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setSubTab(t.id as any)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition cursor-pointer ${
                active
                  ? "bg-blue-600 text-white shadow-sm"
                  : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
              }`}
            >
              <Icon className="w-4 h-4" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* SUB-TAB 1: TỔNG QUAN HỌC KỲ & KHỐI LƯỢNG QUY ĐỔI */}
      {subTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-600" />
              Thống kê theo Học kỳ trong Năm học {academicYear}
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b">
                  <tr>
                    <th className="p-3">Học kỳ</th>
                    <th className="p-3 text-center">Tổng việc</th>
                    <th className="p-3 text-center text-emerald-700">Đúng hạn</th>
                    <th className="p-3 text-center text-rose-600">Trễ hạn</th>
                    <th className="p-3 text-center text-blue-600">Đang mở</th>
                    <th className="p-3 text-right">Giờ quy đổi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {semesters.map((s: any, i: number) => (
                    <tr key={i} className="hover:bg-slate-50">
                      <td className="p-3 font-medium text-slate-800">{s.semester}</td>
                      <td className="p-3 text-center font-bold">{s.total}</td>
                      <td className="p-3 text-center text-emerald-600 font-semibold">{s.on_time}</td>
                      <td className="p-3 text-center text-rose-600 font-semibold">{s.late}</td>
                      <td className="p-3 text-center text-blue-600 font-semibold">{s.open}</td>
                      <td className="p-3 text-right font-bold text-indigo-700">{s.hours} giờ</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-100 space-y-2 text-xs text-slate-700">
              <div className="font-bold text-blue-900">
                Tổng hợp Khối lượng Giảng dạy & Công tác Năm học (Theo khung Thông tư 20/2020/TT-BGDĐT):
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>• Định mức giảng dạy (270 giờ chuẩn/năm): <b>{lecturer.teaching_hours_year} giờ chuẩn</b></div>
                <div>• Số học phần / Sinh viên: <b>{lecturer.course_count} học phần ({lecturer.student_count} SV)</b></div>
                <div>• Giờ công tác cấp Khoa/Bộ môn: <b>{summary.faculty_converted_hours} giờ chuẩn</b></div>
                <div>• Giờ công tác ánh xạ cấp Trường: <b>{summary.school_mapped_hours} giờ chuẩn</b></div>
              </div>
              <div className="pt-1 border-t border-blue-200 flex items-center justify-between font-semibold text-blue-900">
                <span>Tỷ lệ hoàn thành định mức công tác kiêm nhiệm & chuyên môn năm ({summary.target_task_hours}h):</span>
                <span>{summary.total_task_converted_hours} / {summary.target_task_hours} giờ ({summary.workload_fulfillment_pct}%)</span>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
              <Layers className="w-5 h-5 text-indigo-600" />
              Phân bố theo Nhóm Công việc Chuyên môn & Quy đổi Giờ chuẩn
            </h3>
            <div className="space-y-3">
              {by_group.map((g: any, idx: number) => {
                const pct = summary.total_task_converted_hours > 0
                  ? Math.round((g.hours / summary.total_task_converted_hours) * 100)
                  : 0;
                return (
                  <div key={idx} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-1.5">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-semibold text-slate-800">{g.group}</span>
                      <span className="font-bold text-indigo-700">{g.hours} giờ chuẩn ({pct}%)</span>
                    </div>
                    <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                      <div className="h-full bg-indigo-600 rounded-full" style={{ width: `${Math.max(pct, 6)}%` }} />
                    </div>
                    <div className="flex items-center justify-between text-xs text-slate-500">
                      <span>Tổng: {g.total} đầu việc • Đã xong: {g.done}</span>
                      <span className={g.late > 0 ? "text-rose-600 font-semibold" : "text-emerald-600"}>
                        Trễ hạn: {g.late} việc
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 2: DANH SÁCH 18 CÔNG VIỆC TRONG 1 NĂM */}
      {subTab === "tasks" && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
            <div className="font-bold text-slate-800 text-sm">
              Danh sách Toàn bộ Công việc trong Năm học {academicYear} của {lecturer.full_name}
            </div>
            <div className="flex items-center gap-2">
              {["ALL", "HK1", "HK2", "HE"].map((sem) => (
                <button
                  key={sem}
                  onClick={() => setSemFilter(sem)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer ${
                    semFilter === sem
                      ? "bg-blue-600 text-white"
                      : "bg-white border border-slate-300 text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  {sem === "ALL" ? `Cả năm (${tasks.length})` : sem === "HE" ? "Học kỳ Hè" : sem}
                </button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-100/80 border-b border-slate-200 text-slate-600 text-xs uppercase">
                  <th className="p-3.5">Mã & Tên công việc</th>
                  <th className="p-3.5">Học kỳ / Nhóm</th>
                  <th className="p-3.5">Hạn gốc / Hiện tại</th>
                  <th className="p-3.5 text-center">Giờ chuẩn</th>
                  <th className="p-3.5 text-center">Tiến độ & Trạng thái</th>
                  <th className="p-3.5">Dự báo Nguy cơ Trễ hạn</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredTasks.map((t: any) => (
                  <tr key={t.task_id} className="hover:bg-slate-50/80">
                    <td className="p-3.5 max-w-md">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                          {t.code}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600">{t.priority}</span>
                        {t.school_catalog_code && (
                          <span className="text-xs px-2 py-0.5 rounded bg-purple-100 text-purple-800 font-semibold">
                            Cấp Trường: {t.school_catalog_code}
                          </span>
                        )}
                      </div>
                      <p className="font-semibold text-slate-900 mt-1">{t.title}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{t.task_type_name} ({t.scale})</p>
                    </td>
                    <td className="p-3.5 text-xs">
                      <span className="font-bold text-slate-800">{t.semester}</span>
                      <div className="text-slate-500 mt-0.5">{t.task_group}</div>
                    </td>
                    <td className="p-3.5 text-xs text-slate-600">
                      <div>Giao: {t.assigned_at}</div>
                      <div>Hạn gốc: <b>{t.original_deadline}</b></div>
                      {t.current_deadline !== t.original_deadline && (
                        <div className="text-amber-700 font-semibold">Gia hạn: {t.current_deadline}</div>
                      )}
                      {t.completed_at && <div className="text-emerald-700">Xong: {t.completed_at}</div>}
                    </td>
                    <td className="p-3.5 text-center font-bold text-indigo-700">
                      {t.conversion_hours}h
                    </td>
                    <td className="p-3.5 text-center">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                          t.status === "Hoàn thành"
                            ? t.is_late
                              ? "bg-rose-100 text-rose-700"
                              : "bg-emerald-100 text-emerald-700"
                            : t.status === "Đang thực hiện"
                            ? "bg-blue-100 text-blue-700"
                            : "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {t.status} ({t.progress_pct}%)
                      </span>
                      {t.status === "Hoàn thành" && (
                        <div className={`text-xs mt-1 font-medium ${t.is_late ? "text-rose-600" : "text-emerald-600"}`}>
                          {t.is_late
                            ? `Trễ +${t.delay_days} ngày`
                            : t.delay_days < 0
                            ? `Sớm ${Math.abs(t.delay_days)} ngày`
                            : "Đúng hạn"}
                        </div>
                      )}
                    </td>
                    <td className="p-3.5 text-xs">
                      {t.ml_prediction ? (
                        <div className="space-y-1">
                          <span
                            className={`inline-block px-2 py-0.5 rounded font-bold ${
                              t.ml_prediction.level === "Cao"
                                ? "bg-rose-100 text-rose-700 border border-rose-200"
                                : t.ml_prediction.level === "Trung bình"
                                ? "bg-amber-100 text-amber-800 border border-amber-200"
                                : "bg-emerald-100 text-emerald-700 border border-emerald-200"
                            }`}
                          >
                            Nguy cơ {t.ml_prediction.level}: {(t.ml_prediction.probability * 100).toFixed(1)}%
                          </span>
                          <p className="text-slate-500 line-clamp-2">{t.ml_prediction.recommendation}</p>
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">Chưa có dự báo</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SUB-TAB 3: MA TRẬN TÁC VỤ - NHÂN SỰ */}
      {subTab === "matrix" && (
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-5 bg-slate-50 border-b border-slate-200">
            <h3 className="font-bold text-slate-800 text-base">
              Thống kê Năng lực Thực hiện theo từng Loại Công việc của {lecturer.full_name}
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Đối sánh lịch sử hoàn thành đúng hạn / trễ hạn của giảng viên trên từng nhóm công việc so với mặt bằng chung của Bộ môn và toàn Khoa CNTT.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-100 text-slate-600 text-xs uppercase border-b">
                  <th className="p-3.5">Loại công việc</th>
                  <th className="p-3.5">Nhóm việc</th>
                  <th className="p-3.5 text-center">Số lần giao</th>
                  <th className="p-3.5 text-center">Đã xong / Trễ</th>
                  <th className="p-3.5 text-center">Tỷ lệ trễ Cá nhân</th>
                  <th className="p-3.5 text-center">TB Bộ môn</th>
                  <th className="p-3.5 text-center">TB Toàn Khoa</th>
                  <th className="p-3.5 text-center">Độ lệch TB (ngày)</th>
                  <th className="p-3.5 text-right">Giờ chuẩn</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {task_personnel_matrix.map((row: any) => (
                  <tr key={row.task_type_id} className="hover:bg-slate-50">
                    <td className="p-3.5 font-semibold text-slate-900">{row.task_type_name}</td>
                    <td className="p-3.5 text-xs text-slate-600">{row.task_group}</td>
                    <td className="p-3.5 text-center font-bold">{row.total_assigned}</td>
                    <td className="p-3.5 text-center">
                      <span className="text-emerald-700 font-semibold">{row.completed_count}</span> /{" "}
                      <span className="text-rose-600 font-semibold">{row.late_count}</span>
                    </td>
                    <td className="p-3.5 text-center">
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                          row.lecturer_late_rate >= 44
                            ? "bg-rose-100 text-rose-700"
                            : row.lecturer_late_rate >= 22
                            ? "bg-amber-100 text-amber-800"
                            : "bg-emerald-100 text-emerald-700"
                        }`}
                      >
                        {row.lecturer_late_rate}%
                      </span>
                    </td>
                    <td className="p-3.5 text-center text-slate-600 font-medium">{row.dept_late_rate}%</td>
                    <td className="p-3.5 text-center text-slate-600 font-medium">{row.global_late_rate}%</td>
                    <td className="p-3.5 text-center font-mono text-xs">
                      {row.avg_delay_days > 0 ? `+${row.avg_delay_days} ngày` : `${row.avg_delay_days} ngày`}
                    </td>
                    <td className="p-3.5 text-right font-bold text-indigo-700">{row.converted_hours}h</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SUB-TAB 4: ĐỐI CHIẾU DỰ ĐOÁN ML VS KẾT QUẢ THỰC TẾ */}
      {subTab === "ml_audit" && (
        <div className="space-y-4">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="font-bold text-slate-800 text-base">
                Bảng Đối chiếu Lịch sử Dự báo Lúc giao việc & Kết quả Thực tế
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Phân tầng mức nguy cơ trễ hạn: <b>Thấp (&lt; 22%)</b> •{" "}
                <b>Trung bình (22% – 44%)</b> • <b>Cao (≥ 44%)</b>.
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <div className="px-3.5 py-2 rounded-xl bg-rose-50 border border-rose-200 text-rose-800">
                Nguy cơ Cao báo đúng: <b>{ml_audit.high_risk_actual_late}/{ml_audit.high_risk_total}</b> ({ml_audit.high_risk_precision}%)
              </div>
              <div className="px-3.5 py-2 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800">
                Nguy cơ Thấp đúng hạn: <b>{ml_audit.low_risk_actual_on_time}/{ml_audit.low_risk_total}</b> ({ml_audit.low_risk_accuracy}%)
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="bg-slate-100 text-slate-600 text-xs uppercase border-b">
                    <th className="p-3.5">Công việc</th>
                    <th className="p-3.5 text-center">Dự báo lúc giao</th>
                    <th className="p-3.5">Nguyên nhân chính & Khuyến nghị</th>
                    <th className="p-3.5 text-center">Kết quả Thực tế</th>
                    <th className="p-3.5 text-center">Đối chiếu</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {ml_audit.records.map((r: any) => (
                    <tr key={r.task_id} className="hover:bg-slate-50">
                      <td className="p-3.5 max-w-xs">
                        <div className="text-xs font-mono font-bold text-blue-700">{r.task_code} ({r.semester})</div>
                        <div className="font-semibold text-slate-900 mt-0.5">{r.task_title}</div>
                        <div className="text-xs text-slate-500 mt-0.5">Hạn gốc: {r.original_deadline}</div>
                      </td>
                      <td className="p-3.5 text-center">
                        <span
                          className={`inline-block px-2.5 py-1 rounded-lg text-xs font-bold ${
                            r.level === "Cao"
                              ? "bg-rose-100 text-rose-700"
                              : r.level === "Trung bình"
                              ? "bg-amber-100 text-amber-800"
                              : "bg-emerald-100 text-emerald-700"
                          }`}
                        >
                          {r.level} ({(r.probability * 100).toFixed(1)}%)
                        </span>
                      </td>
                      <td className="p-3.5 text-xs space-y-1 max-w-md">
                        {r.top_factors && r.top_factors.length > 0 ? (
                          r.top_factors.map((f: any, idx: number) => (
                            <div key={idx} className="flex items-center gap-1.5">
                              <span
                                className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                  f.direction === "tăng rủi ro"
                                    ? "bg-rose-50 text-rose-700 border border-rose-200"
                                    : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                }`}
                              >
                                {f.direction === "tăng rủi ro" ? "▲ Tăng nguy cơ" : "▼ Giảm nguy cơ"}
                              </span>
                              <span className="text-slate-700 font-medium">{formatFeatureName(f.feature)}</span>
                            </div>
                          ))
                        ) : (
                          <span className="text-slate-400">Không có yếu tố nổi bật</span>
                        )}
                        <div className="text-slate-500 italic pt-0.5">{r.recommendation}</div>
                      </td>
                      <td className="p-3.5 text-center text-xs">
                        {r.actual_is_late === null ? (
                          <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-medium">
                            {r.status} (Chưa kết thúc)
                          </span>
                        ) : r.actual_is_late ? (
                          <span className="px-2.5 py-1 rounded bg-rose-100 text-rose-700 font-bold">
                            Trễ hạn (+{r.delay_days} ngày)
                          </span>
                        ) : (
                          <span className="px-2.5 py-1 rounded bg-emerald-100 text-emerald-700 font-bold">
                            Đúng hạn ({r.delay_days} ngày)
                          </span>
                        )}
                      </td>
                      <td className="p-3.5 text-center">
                        {r.is_correct === null ? (
                          <span className="text-xs text-slate-400">Đang theo dõi</span>
                        ) : r.is_correct ? (
                          <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
                            <Check className="w-3.5 h-3.5" /> Khớp thực tế
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs font-bold text-amber-700 bg-amber-50 px-2.5 py-1 rounded-full border border-amber-200">
                            <XCircle className="w-3.5 h-3.5" /> Lệch nhẹ
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
