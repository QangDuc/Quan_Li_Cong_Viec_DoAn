import React, { useState, useEffect } from "react";
import {
  LayoutDashboard, CheckSquare, FileSpreadsheet, ShieldAlert,
  Bell, LogOut, UserCheck, Users, KeyRound, RefreshCw, FileDown, Sparkles
} from "lucide-react";

import { API_BASE } from "./types";
import { LecturerEvaluationView } from "./components/LecturerEvaluationView";
import { AssignTaskWithMLView } from "./components/AssignTaskWithMLView";
import { TasksAndExtensionsView } from "./components/TasksAndExtensionsView";
import { PlansAndCatalogView } from "./components/PlansAndCatalogView";

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));
  const [user, setUser] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<string>("tasks");
  const [reportMode, setReportMode] = useState<"faculty" | "lecturer">("faculty");

  // Login states
  const [username, setUsername] = useState("truongkhoa");
  const [password, setPassword] = useState("Manager@123");
  const [loginError, setLoginError] = useState("");

  // Data states
  const [stats, setStats] = useState<any>(null);
  const [tasks, setTasks] = useState<any[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [mlAcc, setMlAcc] = useState<any>(null);
  const [taskTypes, setTaskTypes] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [schoolCatalog, setSchoolCatalog] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);

  // Filter states on Dashboard
  const [dashYear, setDashYear] = useState<string>("2026-2027");
  const [dashSemester, setDashSemester] = useState<string>("");

  // Notifications & Password modals
  const [showNotifPanel, setShowNotifPanel] = useState(false);
  const [showPwdModal, setShowPwdModal] = useState(false);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [pwdMsg, setPwdMsg] = useState("");

  // Admin Create User state
  const [newUsername, setNewUsername] = useState("");
  const [newFullName, setNewFullName] = useState("");
  const [newRole, setNewRole] = useState("lecturer");
  const [newUserPass, setNewUserPass] = useState("Lecturer@123");
  const [userMsg, setUserMsg] = useState("");

  useEffect(() => {
    if (token) {
      fetchMe();
      fetchInitialData();
    }
  }, [token]);

  useEffect(() => {
    if (token) {
      fetchDashboardStats();
    }
  }, [dashYear, dashSemester, token]);

  const fetchMe = async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setUser(await res.json());
      } else {
        handleLogout();
      }
    } catch {
      handleLogout();
    }
  };

  const fetchDashboardStats = async () => {
    if (!token) return;
    const h = { Authorization: `Bearer ${token}` };
    const qs = new URLSearchParams();
    if (dashYear) qs.set("academic_year", dashYear);
    if (dashSemester) qs.set("semester", dashSemester);
    const res = await fetch(`${API_BASE}/reports/statistics?${qs.toString()}`, { headers: h });
    if (res.ok) setStats(await res.json());
  };

  const fetchInitialData = async () => {
    if (!token) return;
    const h = { Authorization: `Bearer ${token}` };
    try {
      const [stRes, tkRes, nfRes, mlRes, ttRes, usRes, scRes, dpRes] = await Promise.all([
        fetch(`${API_BASE}/reports/statistics?academic_year=${dashYear}`, { headers: h }),
        fetch(`${API_BASE}/tasks`, { headers: h }),
        fetch(`${API_BASE}/common/notifications`, { headers: h }),
        fetch(`${API_BASE}/reports/ml-accuracy`, { headers: h }),
        fetch(`${API_BASE}/common/task-types`, { headers: h }),
        fetch(`${API_BASE}/users`, { headers: h }),
        fetch(`${API_BASE}/reports/school-catalog`, { headers: h }),
        fetch(`${API_BASE}/common/departments`, { headers: h }),
      ]);
      if (stRes.ok) setStats(await stRes.json());
      if (tkRes.ok) setTasks(await tkRes.json());
      if (nfRes.ok) setNotifications(await nfRes.json());
      if (mlRes.ok) setMlAcc(await mlRes.json());
      if (ttRes.ok) setTaskTypes(await ttRes.json());
      if (usRes.ok) setUsers(await usRes.json());
      if (scRes.ok) setSchoolCatalog(await scRes.json());
      if (dpRes.ok) setDepartments(await dpRes.json());
    } catch (e) {
      console.error(e);
    }
  };

  const loginWithCredentials = async (u: string, p: string) => {
    setLoginError("");
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: u, password: p }),
      });
      const data = await res.json();
      if (!res.ok) {
        setLoginError(data.detail || "Đăng nhập thất bại");
        return;
      }
      localStorage.setItem("token", data.access_token);
      setToken(data.access_token);
      setUser(data.user);
    } catch {
      setLoginError("Không kết nối được tới máy chủ Backend (port 8000)");
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    await loginWithCredentials(username, password);
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  };

  const handleExportExcel = async () => {
    const qs = new URLSearchParams({ academic_year: dashYear });
    if (dashSemester) qs.set("semester", dashSemester);
    const res = await fetch(`${API_BASE}/reports/export-excel?${qs.toString()}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `BaoCao_CongViec_${dashYear}_${dashSemester || "CaNam"}.xlsx`;
      a.click();
    }
  };

  const handleScanDeadlines = async () => {
    const res = await fetch(`${API_BASE}/common/notifications/scan-deadlines`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      fetchInitialData();
      setShowNotifPanel(true);
    }
  };

  const handleMarkAllRead = async () => {
    await fetch(`${API_BASE}/common/notifications/read-all`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
    });
    fetchInitialData();
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwdMsg("");
    const res = await fetch(`${API_BASE}/auth/change-password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
    const data = await res.json();
    if (res.ok) {
      setPwdMsg("Đổi mật khẩu thành công!");
      setOldPassword("");
      setNewPassword("");
    } else {
      setPwdMsg(data.detail || "Lỗi đổi mật khẩu");
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setUserMsg("");
    const res = await fetch(`${API_BASE}/users`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        username: newUsername,
        password: newUserPass,
        full_name: newFullName,
        role: newRole,
        department_id: departments[0]?.id || null,
      }),
    });
    const data = await res.json();
    if (res.ok) {
      setUserMsg(data.message);
      setNewUsername("");
      setNewFullName("");
      fetchInitialData();
    } else {
      setUserMsg(data.detail || "Không thể tạo người dùng");
    }
  };

  // --- MÀN HÌNH ĐĂNG NHẬP ---
  if (!token) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8 space-y-6">
          <div className="text-center space-y-2">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-blue-600 text-white font-bold text-xl shadow-lg">
              HUIT
            </div>
            <h1 className="text-xl font-bold text-slate-900">
              Hệ thống Quản lý Công việc & Tối ưu Phân công bằng Học máy
            </h1>
            <p className="text-xs text-slate-500">
              Khoa Công nghệ Thông tin — Khóa luận CNTT-KLCN184 (2026–2027)
            </p>
          </div>

          {loginError && (
            <div className="bg-rose-50 border border-rose-200 text-rose-700 p-3 rounded-xl text-xs font-medium">
              {loginError}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Tên đăng nhập</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-4 py-2.5 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Mật khẩu</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2.5 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                required
              />
            </div>
            <button
              type="submit"
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-xl transition shadow-md cursor-pointer"
            >
              Đăng nhập Hệ thống
            </button>
          </form>

          <div className="border-t border-slate-200 pt-4 space-y-2">
            <p className="text-xs font-bold text-slate-600">Đăng nhập nhanh theo Vai trò Kiểm thử:</p>
            <div className="grid grid-cols-1 gap-2">
              <button
                type="button"
                onClick={() => loginWithCredentials("truongkhoa", "Manager@123")}
                className="text-left px-3 py-2 rounded-xl bg-blue-50 hover:bg-blue-100 border border-blue-200 text-xs transition cursor-pointer"
              >
                <b className="text-blue-900">1. Trưởng Khoa CNTT (TS. Nguyễn Văn Lễ):</b>{" "}
                <span className="text-blue-700">truongkhoa / Manager@123</span>
              </button>
              <button
                type="button"
                onClick={() => loginWithCredentials("gv_k01_1", "Lecturer@123")}
                className="text-left px-3 py-2 rounded-xl bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-xs transition cursor-pointer"
              >
                <b className="text-emerald-900">2. Hồ sơ Giảng viên 1 Năm (ThS. Nguyễn Minh Khoa):</b>{" "}
                <span className="text-emerald-700">gv_k01_1 / Lecturer@123</span>
              </button>
              <button
                type="button"
                onClick={() => loginWithCredentials("tbm_k01", "Manager@123")}
                className="text-left px-3 py-2 rounded-xl bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-xs transition cursor-pointer"
              >
                <b className="text-indigo-900">3. Trưởng Bộ môn CNPM (PGS.TS. Hoàng Văn Minh):</b>{" "}
                <span className="text-indigo-700">tbm_k01 / Manager@123</span>
              </button>
              <button
                type="button"
                onClick={() => loginWithCredentials("admin", "Admin@123")}
                className="text-left px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-300 text-xs transition cursor-pointer"
              >
                <b className="text-slate-900">4. Quản trị viên Hệ thống (Admin):</b>{" "}
                <span className="text-slate-700">admin / Admin@123</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* HEADER */}
      <header className="bg-slate-900 text-white shadow-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center font-bold text-sm shadow">
              HUIT
            </div>
            <div>
              <h1 className="font-bold text-base leading-tight">
                Quản lý Công việc & Dự báo Rủi ro Học máy — Khoa CNTT
              </h1>
              <p className="text-xs text-slate-400">
                {user?.full_name} • Vai trò:{" "}
                <span className="text-blue-300 font-semibold uppercase">{user?.role}</span> •{" "}
                {user?.department_name}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleScanDeadlines}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 cursor-pointer"
              title="Quét tự động công việc sắp đến hạn và quá hạn"
            >
              <RefreshCw className="w-3.5 h-3.5 text-blue-400" /> Quét Nhắc hạn
            </button>

            <div className="relative">
              <button
                onClick={() => setShowNotifPanel(!showNotifPanel)}
                className="relative p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 cursor-pointer"
                title="Thông báo hệ thống"
              >
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 bg-rose-500 text-white text-[10px] font-bold w-5 h-5 rounded-full flex items-center justify-center">
                    {unreadCount}
                  </span>
                )}
              </button>

              {showNotifPanel && (
                <div className="absolute right-0 mt-2 w-96 bg-white text-slate-900 rounded-2xl shadow-2xl border border-slate-200 overflow-hidden z-50">
                  <div className="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                    <span className="font-bold text-xs uppercase text-slate-700">
                      Trung tâm Thông báo ({notifications.length})
                    </span>
                    <button
                      onClick={handleMarkAllRead}
                      className="text-xs text-blue-600 hover:underline font-semibold cursor-pointer"
                    >
                      Đánh dấu đã đọc tất cả
                    </button>
                  </div>
                  <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
                    {notifications.map((n) => (
                      <div
                        key={n.id}
                        className={`p-3 text-xs ${n.is_read ? "bg-white" : "bg-blue-50/50"}`}
                      >
                        <div className="font-bold text-slate-900">{n.title}</div>
                        <p className="text-slate-600 mt-0.5">{n.content}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <button
              onClick={() => setShowPwdModal(true)}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 cursor-pointer"
              title="Đổi mật khẩu"
            >
              <KeyRound className="w-4 h-4" />
            </button>

            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 bg-rose-600 hover:bg-rose-700 px-3 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" /> Thoát
            </button>
          </div>
        </div>
      </header>

      {/* NAVIGATION TABS — 4 TAB NGHIỆP VỤ THỰC TẾ HẰNG NGÀY */}
      <div className="bg-white border-b border-slate-200 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 flex gap-1 overflow-x-auto">
          {[
            { id: "tasks", label: "Công việc & Duyệt gia hạn", icon: CheckSquare },
            ...(user?.role !== "lecturer"
              ? [{ id: "assign", label: "Giao việc mới", icon: Sparkles }]
              : []),
            { id: "reports", label: "Báo cáo & Hồ sơ Giảng viên", icon: LayoutDashboard },
            { id: "plans_catalog", label: "Kế hoạch năm & Định mức giờ chuẩn", icon: FileSpreadsheet },
            ...(user?.role === "admin"
              ? [{ id: "users", label: "Quản trị Tài khoản", icon: Users }]
              : []),
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3.5 border-b-2 font-semibold text-xs sm:text-sm whitespace-nowrap transition cursor-pointer ${
                  active
                    ? "border-blue-600 text-blue-600 bg-blue-50/40"
                    : "border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* MAIN CONTENT */}
      <main className="max-w-7xl mx-auto px-4 py-6 flex-1 w-full">
        {/* TAB: BÁO CÁO & HỒ SƠ GIẢNG VIÊN */}
        {activeTab === "reports" && (
          <div className="space-y-6">
            {/* Thanh chuyển đổi: Tổng hợp toàn Khoa <-> Hồ sơ Công tác 1 Năm Giảng viên */}
            <div className="bg-white p-3.5 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setReportMode("faculty")}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold cursor-pointer transition ${
                    reportMode === "faculty"
                      ? "bg-blue-600 text-white shadow-sm"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  <LayoutDashboard className="w-4 h-4" />
                  1. Thống kê Tổng hợp toàn Khoa
                </button>
                <button
                  onClick={() => setReportMode("lecturer")}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold cursor-pointer transition ${
                    reportMode === "lecturer"
                      ? "bg-blue-600 text-white shadow-sm"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  <UserCheck className="w-4 h-4" />
                  2. Hồ sơ Công tác 1 Năm của Giảng viên
                </button>
              </div>
              <span className="text-xs text-slate-500">
                Định mức quy chiếu: Thông tư 20/2020/TT-BGDĐT (270 giờ chuẩn giảng dạy / năm học)
              </span>
            </div>

            {reportMode === "faculty" ? (
              <div className="space-y-6">
                {/* Bộ lọc Năm học / Học kỳ & Xuất báo cáo Excel */}
                <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h2 className="text-base font-bold text-slate-900">
                      Báo cáo Tổng hợp Tình hình Thực hiện Công việc & Khối lượng Quy đổi
                    </h2>
                    <p className="text-xs text-slate-500">
                      Trích xuất số liệu theo Năm học / Học kỳ, tổng hợp giờ chuẩn quy đổi và theo dõi chất lượng dự báo tiến độ.
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2.5">
                    <select
                      value={dashYear}
                      onChange={(e) => setDashYear(e.target.value)}
                      className="px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-xs font-semibold"
                    >
                      <option value="2026-2027">Năm học 2026-2027</option>
                      <option value="2025-2026">Năm học 2025-2026</option>
                    </select>
                    <select
                      value={dashSemester}
                      onChange={(e) => setDashSemester(e.target.value)}
                      className="px-3 py-2 bg-slate-50 border border-slate-300 rounded-xl text-xs font-semibold"
                    >
                      <option value="">Cả năm học</option>
                      <option value="HK1">Học kỳ 1 (HK1)</option>
                      <option value="HK2">Học kỳ 2 (HK2)</option>
                      <option value="Summer">Học kỳ Hè</option>
                    </select>
                    <button
                      onClick={handleExportExcel}
                      className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-xl text-xs font-semibold shadow-sm cursor-pointer"
                    >
                      <FileDown className="w-4 h-4" /> Xuất Báo cáo Excel (.xlsx)
                    </button>
                  </div>
                </div>

                {stats && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                      <p className="text-xs font-semibold text-slate-500 uppercase">Tổng lượt phân công</p>
                      <p className="text-3xl font-bold text-slate-900 mt-2">{stats.total_tasks}</p>
                      <p className="text-xs text-slate-500 mt-1">
                        Đang thực hiện: <b>{stats.in_progress}</b> • Mới giao: <b>{stats.new}</b>
                      </p>
                    </div>
                    <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                      <p className="text-xs font-semibold text-slate-500 uppercase">Đã hoàn thành</p>
                      <p className="text-3xl font-bold text-emerald-600 mt-2">
                        {stats.completed}{" "}
                        <span className="text-sm font-normal text-slate-500">({stats.completion_rate}%)</span>
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        Đúng hạn: <b className="text-emerald-600">{stats.completed_on_time}</b> ({stats.on_time_rate}%)
                      </p>
                    </div>
                    <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                      <p className="text-xs font-semibold text-slate-500 uppercase">Trễ hạn & Quá hạn mở</p>
                      <p className="text-3xl font-bold text-rose-600 mt-2">
                        {stats.late_completed + stats.overdue_open}
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        Hoàn thành trễ: <b>{stats.late_completed}</b> • Quá hạn chưa xong: <b>{stats.overdue_open}</b>
                      </p>
                    </div>
                    <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200">
                      <p className="text-xs font-semibold text-slate-500 uppercase">Tổng Giờ chuẩn Quy đổi</p>
                      <p className="text-3xl font-bold text-indigo-700 mt-2">
                        {stats.total_converted_hours} <span className="text-sm font-normal">giờ chuẩn</span>
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        Cộng tự động theo Định mức Khoa & Danh mục Trường
                      </p>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                  <div className="lg:col-span-7 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                        <ShieldAlert className="w-5 h-5 text-blue-600" />
                        Theo dõi Độ chính xác Cảnh báo Sớm Trễ hạn
                      </h3>
                      <span className="text-xs px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 font-semibold">
                        Đối chiếu sau nghiệm thu
                      </span>
                    </div>
                    {mlAcc && mlAcc.total_evaluated > 0 ? (
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
                          <p className="text-slate-500">Số lượt công việc đã nghiệm thu</p>
                          <p className="text-2xl font-bold text-slate-900 mt-1">{mlAcc.total_evaluated} lượt</p>
                        </div>
                        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200">
                          <p className="text-rose-700 font-semibold">Nhóm Cảnh báo Nguy cơ Cao</p>
                          <p className="text-xl font-bold text-rose-800 mt-1">
                            Trễ thực tế {mlAcc.high_risk.actual_late}/{mlAcc.high_risk.total_predicted} ({mlAcc.high_risk.precision}%)
                          </p>
                        </div>
                        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200">
                          <p className="text-emerald-700 font-semibold">Nhóm Nguy cơ Thấp</p>
                          <p className="text-xl font-bold text-emerald-800 mt-1">
                            Đúng hạn {mlAcc.low_risk.actual_on_time}/{mlAcc.low_risk.total_predicted} ({mlAcc.low_risk.accuracy}%)
                          </p>
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500">Chưa có dữ liệu đối chiếu.</p>
                    )}
                    <p className="text-[11px] text-slate-400 italic">
                      * Kết quả dự báo chỉ đóng vai trò gợi ý hỗ trợ; quyền quyết định phân công và đánh giá cuối cùng thuộc về Lãnh đạo Khoa / Bộ môn.
                    </p>
                  </div>

                  <div className="lg:col-span-5 bg-gradient-to-br from-blue-600 to-indigo-700 text-white p-6 rounded-2xl shadow-md flex flex-col justify-between space-y-4">
                    <div className="space-y-2">
                      <span className="px-2.5 py-1 rounded-full bg-white/20 text-xs font-bold uppercase">
                        Tra cứu theo từng giảng viên
                      </span>
                      <h3 className="text-lg font-bold">
                        Hồ sơ Công tác & Giờ chuẩn Quy đổi 1 Năm (2026–2027)
                      </h3>
                      <p className="text-xs text-blue-100 leading-relaxed">
                        Xem chi tiết khối lượng công tác cả năm học của từng giảng viên (HK1, HK2, Học kỳ Hè), tổng giờ chuẩn giảng dạy và giờ chuẩn công tác quy đổi theo khung Thông tư 20/2020/TT-BGDĐT.
                      </p>
                    </div>
                    <button
                      onClick={() => setReportMode("lecturer")}
                      className="w-full py-2.5 px-4 bg-white text-blue-700 hover:bg-blue-50 font-bold text-xs sm:text-sm rounded-xl shadow transition cursor-pointer"
                    >
                      Xem Hồ sơ Công tác 1 Năm của Giảng viên →
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <LecturerEvaluationView token={token} currentUser={user} users={users} />
            )}
          </div>
        )}

        {/* TAB: QUẢN LÝ CÔNG VIỆC, TIẾN ĐỘ & GIA HẠN */}
        {activeTab === "tasks" && (
          <TasksAndExtensionsView
            token={token}
            currentUser={user}
            tasks={tasks}
            schoolCatalog={schoolCatalog}
            onRefresh={fetchInitialData}
          />
        )}

        {/* TAB: GIAO VIỆC MỚI */}
        {activeTab === "assign" && (
          <AssignTaskWithMLView
            token={token}
            taskTypes={taskTypes}
            schoolCatalog={schoolCatalog}
            users={users}
            onAssigned={() => {
              fetchInitialData();
            }}
          />
        )}

        {/* TAB: KẾ HOẠCH NĂM & ĐỊNH MỨC GIỜ CHUẨN */}
        {activeTab === "plans_catalog" && (
          <PlansAndCatalogView
            token={token}
            currentUser={user}
            users={users}
            taskTypes={taskTypes}
            schoolCatalog={schoolCatalog}
            onRefresh={fetchInitialData}
          />
        )}

        {/* TAB 6: QUẢN TRỊ NGƯỜI DÙNG (ADMIN) */}
        {activeTab === "users" && user?.role === "admin" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <h3 className="text-base font-bold text-slate-900">Tạo Tài khoản Người dùng mới</h3>
              {userMsg && (
                <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold">
                  {userMsg}
                </div>
              )}
              <form onSubmit={handleCreateUser} className="space-y-3 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Tên đăng nhập *</label>
                  <input
                    type="text"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl"
                    required
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Họ và tên *</label>
                  <input
                    type="text"
                    value={newFullName}
                    onChange={(e) => setNewFullName(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl"
                    required
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Vai trò</label>
                  <select
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl bg-white"
                  >
                    <option value="lecturer">Giảng viên (lecturer)</option>
                    <option value="manager">Quản lý Khoa / Bộ môn (manager)</option>
                    <option value="admin">Quản trị hệ thống (admin)</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Mật khẩu khởi tạo</label>
                  <input
                    type="text"
                    value={newUserPass}
                    onChange={(e) => setNewUserPass(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl"
                    required
                  />
                </div>
                <button
                  type="submit"
                  className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl cursor-pointer"
                >
                  Thêm Người dùng
                </button>
              </form>
            </div>

            <div className="lg:col-span-8 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <h3 className="text-base font-bold text-slate-900 mb-4">
                Danh sách Tài khoản trong Hệ thống ({users.length})
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-slate-100 text-slate-600 uppercase">
                    <tr>
                      <th className="p-3">Mã / Username</th>
                      <th className="p-3">Họ và tên</th>
                      <th className="p-3">Vai trò</th>
                      <th className="p-3">Bộ môn</th>
                      <th className="p-3">Trạng thái</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {users.map((u) => (
                      <tr key={u.id} className="hover:bg-slate-50">
                        <td className="p-3 font-mono font-semibold text-blue-700">
                          {u.username} {u.lecturer_code ? `(${u.lecturer_code})` : ""}
                        </td>
                        <td className="p-3 font-semibold text-slate-900">{u.full_name}</td>
                        <td className="p-3 uppercase font-bold text-slate-600">{u.role}</td>
                        <td className="p-3 text-slate-500">{u.department_name || "Toàn Khoa"}</td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-semibold">
                            Hoạt động
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* MODAL ĐỔI MẬT KHẨU */}
      {showPwdModal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4">
          <form
            onSubmit={handleChangePassword}
            className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-xl space-y-4 text-xs"
          >
            <h3 className="text-base font-bold text-slate-900">Đổi mật khẩu tài khoản</h3>
            {pwdMsg && (
              <div className="p-2.5 rounded-lg bg-blue-50 text-blue-800 font-semibold">{pwdMsg}</div>
            )}
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Mật khẩu hiện tại</label>
              <input
                type="password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl"
                required
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Mật khẩu mới (≥8 ký tự)</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl"
                required
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowPwdModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 font-semibold cursor-pointer"
              >
                Đóng
              </button>
              <button
                type="submit"
                className="px-4 py-2 rounded-xl bg-blue-600 text-white font-semibold cursor-pointer"
              >
                Cập nhật
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
