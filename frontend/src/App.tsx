import React, { useState, useEffect } from "react";
import {
  LayoutDashboard,
  CheckSquare,
  FileSpreadsheet,
  Bell,
  LogOut,
  UserCheck,
  Users,
  KeyRound,
  RefreshCw,
  FileDown, Bot,
  Sparkles,
} from "lucide-react";

import { API_BASE } from "./types";
import { LecturerEvaluationView } from "./components/LecturerEvaluationView";
import { AssignTaskWithMLView } from "./components/AssignTaskWithMLView";
import { TasksAndExtensionsView } from "./components/TasksAndExtensionsView";
import { PlansAndCatalogView } from "./components/PlansAndCatalogView";
import { AIAssistantView } from "./components/AIAssistantView";

export default function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));
  const [user, setUser] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<string>("tasks");
  const [reportMode, setReportMode] = useState<"faculty" | "lecturer">("faculty");

  // Login states
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("Admin@123");
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

  // Online ML Retraining state
  const [retraining, setRetraining] = useState(false);
  const [retrainMsg, setRetrainMsg] = useState("");

  // Notifications & Password modals
  const [showNotifPanel, setShowNotifPanel] = useState(false);
  const [showPwdModal, setShowPwdModal] = useState(false);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [pwdMsg, setPwdMsg] = useState("");

  // Create User state
  const [newUsername, setNewUsername] = useState("");
  const [newFullName, setNewFullName] = useState("");
  const [newRole, setNewRole] = useState("lecturer");
  const [newDeptId, setNewDeptId] = useState<number | "">("");
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
    const res = await fetch(`${API_BASE}/reports/statistics?${qs.toString()}`, {
      headers: h,
    });
    if (res.ok) setStats(await res.json());
  };

  const fetchInitialData = async () => {
    if (!token) return;
    const h = { Authorization: `Bearer ${token}` };
    try {
      const [stRes, tkRes, nfRes, mlRes, ttRes, usRes, scRes, dpRes] =
        await Promise.all([
          fetch(`${API_BASE}/reports/statistics?academic_year=${dashYear}`, {
            headers: h,
          }),
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
      if (dpRes.ok) {
        const dList = await dpRes.json();
        setDepartments(dList);
        if (dList.length > 0 && newDeptId === "") setNewDeptId(dList[0].id);
      }
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
      window.URL.revokeObjectURL(url);
    }
  };

  const handleExportLateExcel = async () => {
    const qs = new URLSearchParams({ academic_year: dashYear });
    if (dashSemester) qs.set("semester", dashSemester);
    const res = await fetch(
      `${API_BASE}/reports/export-late-excel?${qs.toString()}`,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    if (res.ok) {
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `DanhSach_GiangVien_TreHan_${dashYear}_${
        dashSemester || "CaNam"
      }.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
    }
  };

  const handleRetrainML = async () => {
    setRetraining(true);
    setRetrainMsg("");
    try {
      const res = await fetch(`${API_BASE}/reports/ml-retrain`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok) {
        const tr = data.train_result || {};
        setRetrainMsg(
          `${data.message} (Phiên bản: ${tr.version || "Online"} • Độ chính xác trên tập thực tế: ${
            tr.acc_before ?? ""
          }% → ${tr.acc_after ?? ""}%)`
        );
        fetchInitialData();
      } else {
        setRetrainMsg(data.detail || "Không thể huấn luyện lại mô hình");
      }
    } catch {
      setRetrainMsg("Không thể kết nối tới dịch vụ Học máy (port 8001)");
    } finally {
      setRetraining(false);
    }
  };

  const handleScanDeadlines = async () => {
    const res = await fetch(`${API_BASE}/common/notifications/scan`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      fetchInitialData();
      setShowNotifPanel(true);
    }
  };

  const handleMarkAllRead = async () => {
    const res = await fetch(`${API_BASE}/common/notifications/read-all`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      fetchInitialData();
    }
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
      body: JSON.stringify({
        old_password: oldPassword,
        new_password: newPassword,
      }),
    });
    const data = await res.json();
    if (res.ok) {
      setPwdMsg("Đã cập nhật mật khẩu thành công!");
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
        department_id:
          newDeptId !== "" ? Number(newDeptId) : departments[0]?.id || null,
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
        <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8 space-y-5">
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
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Tên đăng nhập
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Nhập tên đăng nhập..."
                className="w-full px-4 py-2.5 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Mật khẩu
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Nhập mật khẩu..."
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
            <p className="text-xs font-bold text-slate-600">
              Đăng nhập nhanh (Chỉ dành cho Quản trị viên Hệ thống):
            </p>
            <button
              type="button"
              onClick={() => loginWithCredentials("admin", "Admin@123")}
              className="w-full text-left px-3.5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-300 text-xs transition cursor-pointer flex items-center justify-between"
            >
              <span className="font-bold text-slate-900">
                Quản trị viên Hệ thống (Admin)
              </span>
              <span className="font-mono text-slate-600">admin</span>
            </button>
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
                {user?.full_name} ({user?.username}) • Vai trò:{" "}
                <span className="text-blue-300 font-semibold uppercase">
                  {user?.role}
                </span>{" "}
                • {user?.department_name}
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
                      Đánh dấu đã đọc hết
                    </button>
                  </div>
                  <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
                    {notifications.map((n) => (
                      <div
                        key={n.id}
                        className={`p-3 text-xs ${
                          !n.is_read ? "bg-blue-50/50" : "bg-white"
                        }`}
                      >
                        <div className="font-semibold text-slate-800">{n.title}</div>
                        <p className="text-slate-600 mt-0.5">{n.content || n.message}</p>
                        <span className="text-[10px] text-slate-400 mt-1 block">
                          {String(n.created_at).slice(0, 16).replace("T", " ")}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <button
              onClick={() => setShowPwdModal(true)}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 cursor-pointer"
              title="Đổi mật khẩu"
            >
              <KeyRound className="w-4 h-4" />
            </button>

            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-xs font-semibold cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" /> Đăng xuất
            </button>
          </div>
        </div>

        {/* NAVIGATION TABS */}
        <div className="bg-slate-800 border-t border-slate-700">
          <div className="max-w-7xl mx-auto px-4 flex items-center gap-1 overflow-x-auto py-1.5">
            <button
              onClick={() => setActiveTab("tasks")}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer transition whitespace-nowrap ${
                activeTab === "tasks"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-300 hover:bg-slate-700 hover:text-white"
              }`}
            >
              <CheckSquare className="w-4 h-4" />
              Công việc & Tiến độ
            </button>

            {user?.role !== "lecturer" && (
              <button
                onClick={() => setActiveTab("assign")}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer transition whitespace-nowrap ${
                  activeTab === "assign"
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-300 hover:bg-slate-700 hover:text-white"
                }`}
              >
                <Sparkles className="w-4 h-4" />
                Giao việc Mới
              </button>
            )}

            <button
              onClick={() => setActiveTab("dashboard")}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer transition whitespace-nowrap ${
                activeTab === "dashboard"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-300 hover:bg-slate-700 hover:text-white"
              }`}
            >
              <LayoutDashboard className="w-4 h-4" />
              Thống kê & Đánh giá
            </button>

            <button
              onClick={() => setActiveTab("ai_assistant")}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer transition whitespace-nowrap ${
                activeTab === "ai_assistant"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-300 hover:bg-slate-700 hover:text-white"
              }`}
            >
              <Bot className="w-4 h-4" />
              Trợ lý AI HUIT
            </button>
            <button
              onClick={() => setActiveTab("plans_catalog")}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer transition whitespace-nowrap ${
                activeTab === "plans_catalog"
                  ? "bg-blue-600 text-white shadow-sm"
                  : "text-slate-300 hover:bg-slate-700 hover:text-white"
              }`}
            >
              <FileSpreadsheet className="w-4 h-4" />
              Kế hoạch Năm & Định mức
            </button>

            {user?.role !== "lecturer" && (
              <button
                onClick={() => setActiveTab("users")}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer transition whitespace-nowrap ${
                  activeTab === "users"
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-300 hover:bg-slate-700 hover:text-white"
                }`}
              >
                <Users className="w-4 h-4" />
                Tài khoản Giảng viên ({users.length})
              </button>
            )}
          </div>
        </div>
      </header>

      {/* MAIN CONTENT */}
      <main className="max-w-7xl w-full mx-auto px-4 py-6 flex-1">
        {/* TAB: THỐNG KÊ, XUẤT BÁO CÁO & HỒ SƠ ĐÁNH GIÁ 1 NĂM */}
        {activeTab === "dashboard" && (
          <div className="space-y-6">
            {/* Thanh chọn chế độ báo cáo: Tổng quan Khoa vs Hồ sơ 1 năm Giảng viên */}
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setReportMode("faculty")}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer transition ${
                    reportMode === "faculty"
                      ? "bg-blue-600 text-white"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  <LayoutDashboard className="w-4 h-4" />
                  Báo cáo Tổng hợp Khoa & Huấn luyện Mô hình
                </button>
                <button
                  onClick={() => setReportMode("lecturer")}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer transition ${
                    reportMode === "lecturer"
                      ? "bg-blue-600 text-white"
                      : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                  }`}
                >
                  <UserCheck className="w-4 h-4" />
                  Hồ sơ Công tác 1 Năm của Giảng viên
                </button>
              </div>

              {reportMode === "faculty" && (
                <div className="flex flex-wrap items-center gap-2">
                  <select
                    value={dashYear}
                    onChange={(e) => setDashYear(e.target.value)}
                    className="px-3 py-1.5 border border-slate-300 rounded-xl text-xs bg-white font-medium"
                  >
                    <option value="2026-2027">Năm học 2026–2027</option>
                    <option value="2025-2026">Năm học 2025–2026</option>
                  </select>
                  <select
                    value={dashSemester}
                    onChange={(e) => setDashSemester(e.target.value)}
                    className="px-3 py-1.5 border border-slate-300 rounded-xl text-xs bg-white font-medium"
                  >
                    <option value="">Cả năm học</option>
                    <option value="HK1">Học kỳ 1</option>
                    <option value="HK2">Học kỳ 2</option>
                    <option value="HE">Học kỳ Hè</option>
                  </select>

                  <button
                    onClick={handleExportLateExcel}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold cursor-pointer shadow-xs"
                  >
                    <FileDown className="w-4 h-4" />
                    Xuất Excel DS Người Trễ hạn
                  </button>

                  <button
                    onClick={handleExportExcel}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold cursor-pointer shadow-xs"
                  >
                    <FileDown className="w-4 h-4" />
                    Xuất Excel Tổng hợp
                  </button>
                </div>
              )}
            </div>

            {reportMode === "faculty" ? (
              <div className="space-y-6">
                {/* 4 THẺ KPI TỔNG QUAN */}
                {stats && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
                      <div className="text-xs font-semibold text-slate-500">
                        Tổng số Phân công Công việc
                      </div>
                      <div className="text-2xl font-extrabold text-slate-900 mt-1">
                        {stats.total_tasks}
                      </div>
                      <div className="text-xs text-slate-500 mt-1">
                        Tỷ lệ hoàn thành: <b className="text-blue-600">{stats.completion_rate}%</b> ({stats.total_converted_hours} giờ chuẩn)
                      </div>
                    </div>

                    <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
                      <div className="text-xs font-semibold text-slate-500">
                        Hoàn thành Đúng hạn
                      </div>
                      <div className="text-2xl font-extrabold text-emerald-600 mt-1">
                        {stats.completed_on_time}
                      </div>
                      <div className="text-xs text-slate-500 mt-1">
                        Tỷ lệ đúng hạn: <b className="text-emerald-700">{stats.on_time_rate}%</b>
                      </div>
                    </div>

                    <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs">
                      <div className="text-xs font-semibold text-slate-500">
                        Đang thực hiện / Mới giao
                      </div>
                      <div className="text-2xl font-extrabold text-blue-600 mt-1">
                        {(stats.in_progress || 0) + (stats.new || 0)}
                      </div>
                      <div className="text-xs text-amber-700 font-medium mt-1">
                        Sắp đến hạn (≤ 3 ngày): <b>{stats.due_soon_open || 0} việc</b>
                      </div>
                    </div>

                    <div className="bg-white p-5 rounded-2xl border border-rose-200 bg-rose-50/30 shadow-xs">
                      <div className="text-xs font-semibold text-rose-700">
                        Hoàn thành Trễ / Đang Quá hạn
                      </div>
                      <div className="text-2xl font-extrabold text-rose-600 mt-1">
                        {(stats.late_completed || 0) + (stats.overdue_open || 0)}
                      </div>
                      <div className="text-xs text-rose-700 mt-1">
                        Trễ hạn: <b>{stats.late_completed || 0}</b> • Đang quá hạn:{" "}
                        <b>{stats.overdue_open || 0}</b>
                      </div>
                    </div>
                  </div>
                )}

                {/* BẢNG PHÂN RÃ THEO NHÓM CÔNG VIỆC & KHỐI LƯỢNG GIỜ CHUẨN */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                  <div className="lg:col-span-7 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
                    <h3 className="text-base font-bold text-slate-900 mb-1">
                      Thống kê theo Nhóm Công việc & Quy đổi Giờ chuẩn
                    </h3>
                    <p className="text-xs text-slate-500 mb-4">
                      Tổng hợp số lượng đầu việc hoàn thành, trễ hạn và tổng giờ chuẩn quy đổi theo từng lĩnh vực công tác.
                    </p>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 uppercase">
                            <th className="p-3">Nhóm công việc</th>
                            <th className="p-3 text-center">Tổng số</th>
                            <th className="p-3 text-center">Hoàn thành</th>
                            <th className="p-3 text-center">Trễ hạn</th>
                            <th className="p-3 text-right">Giờ chuẩn</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {stats?.by_group?.map((g: any) => (
                            <tr key={g.group} className="hover:bg-slate-50">
                              <td className="p-3 font-semibold text-slate-800">
                                {g.group}
                              </td>
                              <td className="p-3 text-center font-bold">{g.total}</td>
                              <td className="p-3 text-center text-emerald-700 font-semibold">
                                {g.done}
                              </td>
                              <td className="p-3 text-center text-rose-600 font-semibold">
                                {g.late}
                              </td>
                              <td className="p-3 text-right font-bold text-blue-700">
                                {g.hours} giờ
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* HUẤN LUYỆN TRỰC TIẾP MÔ HÌNH TỪ DỮ LIỆU VẬN HÀNH */}
                  <div className="lg:col-span-5 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between space-y-4">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-200">
                          Huấn luyện trực tiếp (Online Learning)
                        </span>
                        {mlAcc?.ml_service?.retrain_count !== undefined && (
                          <span className="text-xs text-slate-500">
                            Đã cập nhật: <b>{mlAcc.ml_service.retrain_count} lần</b>
                          </span>
                        )}
                      </div>

                      <h3 className="text-base font-bold text-slate-900">
                        Huấn luyện & Cập nhật Mô hình theo Dữ liệu Thực tế
                      </h3>
                      <p className="text-xs text-slate-600 leading-relaxed">
                        Trong quá trình sử dụng, khi có thêm các công việc mới hoàn thành (đúng hạn hoặc trễ hạn), người quản lý có thể huấn luyện bổ sung trực tiếp trên dữ liệu vận hành để mô hình ngày càng chính xác hơn.
                      </p>

                      {mlAcc && (
                        <div className="grid grid-cols-2 gap-2.5 pt-1 text-xs">
                          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                            <div className="text-slate-500">Dữ liệu thực tế đã xong</div>
                            <div className="text-base font-bold text-slate-900 mt-0.5">
                              {mlAcc.live_done_count ?? mlAcc.total_evaluated ?? 0} mẫu
                            </div>
                          </div>
                          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                            <div className="text-slate-500">Độ chính xác nhóm Thấp</div>
                            <div className="text-base font-bold text-emerald-600 mt-0.5">
                              {mlAcc.low_risk?.accuracy ?? 90}%
                            </div>
                          </div>
                        </div>
                      )}

                      {retrainMsg && (
                        <div className="p-3 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-900 text-xs font-medium">
                          {retrainMsg}
                        </div>
                      )}
                    </div>

                    <div className="space-y-2 pt-2">
                      {user?.role !== "lecturer" && (
                        <button
                          onClick={handleRetrainML}
                          disabled={retraining}
                          className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-400 text-white font-semibold text-xs rounded-xl shadow-xs transition cursor-pointer flex items-center justify-center gap-2"
                        >
                          <RefreshCw
                            className={`w-4 h-4 ${retraining ? "animate-spin" : ""}`}
                          />
                          {retraining
                            ? "Đang huấn luyện từ dữ liệu thực tế..."
                            : "Huấn luyện cập nhật mô hình từ dữ liệu hiện tại"}
                        </button>
                      )}

                      <button
                        onClick={() => setReportMode("lecturer")}
                        className="w-full py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold text-xs rounded-xl transition cursor-pointer"
                      >
                        Xem Hồ sơ Công tác 1 Năm của Giảng viên →
                      </button>
                    </div>
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
            users={users}
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
        {activeTab === "ai_assistant" && (
          <AIAssistantView token={token || ""} currentUser={user} tasks={tasks} />
        )}

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

        {/* TAB: QUẢN TRỊ NGƯỜI DÙNG & TÀI KHOẢN GIẢNG VIÊN */}
        {activeTab === "users" && user?.role !== "lecturer" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs space-y-4">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Cấp Tài khoản Giảng viên Mới
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Mỗi giảng viên có tài khoản riêng để đăng nhập xem công việc được giao và nộp file minh chứng.
                </p>
              </div>
              {userMsg && (
                <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold">
                  {userMsg}
                </div>
              )}
              <form onSubmit={handleCreateUser} className="space-y-3 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Tên đăng nhập *
                  </label>
                  <input
                    type="text"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    placeholder="VD: gv_k01_4"
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl"
                    required
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Họ và tên Giảng viên *
                  </label>
                  <input
                    type="text"
                    value={newFullName}
                    onChange={(e) => setNewFullName(e.target.value)}
                    placeholder="VD: ThS. Lê Hoàng Nam"
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl"
                    required
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Bộ môn
                  </label>
                  <select
                    value={newDeptId}
                    onChange={(e) =>
                      setNewDeptId(e.target.value === "" ? "" : Number(e.target.value))
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-xl bg-white"
                  >
                    {departments.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">
                    Vai trò
                  </label>
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
                  <label className="block font-semibold text-slate-700 mb-1">
                    Mật khẩu khởi tạo
                  </label>
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
                  Thêm Tài khoản Giảng viên
                </button>
              </form>
            </div>

            <div className="lg:col-span-8 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Danh sách Tài khoản trong Hệ thống ({users.length})
                  </h3>
                  <p className="text-xs text-slate-500">
                    {user?.role === "admin"
                      ? "Quản trị viên Hệ thống (Admin) có quyền chuyển nhanh sang tài khoản khác để kiểm tra."
                      : "Danh sách toàn bộ tài khoản giảng viên và cán bộ quản lý trong Khoa."}
                  </p>
                </div>
              </div>
              <div className="overflow-x-auto max-h-[540px]">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-slate-100 text-slate-600 uppercase sticky top-0">
                    <tr>
                      <th className="p-3">Mã / Username</th>
                      <th className="p-3">Họ và tên</th>
                      <th className="p-3">Vai trò</th>
                      <th className="p-3">Bộ môn</th>
                      <th className="p-3 text-right">
                        {user?.role === "admin" ? "Đăng nhập nhanh (Admin)" : "Trạng thái"}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {users.map((u) => {
                      const defPwd =
                        u.role === "admin"
                          ? "Admin@123"
                          : u.role === "manager"
                          ? "Manager@123"
                          : "Lecturer@123";
                      return (
                        <tr key={u.id} className="hover:bg-slate-50">
                          <td className="p-3 font-mono font-semibold text-blue-700">
                            {u.username}{" "}
                            {u.lecturer_code ? `(${u.lecturer_code})` : ""}
                          </td>
                          <td className="p-3 font-semibold text-slate-900">
                            {u.full_name}
                          </td>
                          <td className="p-3 uppercase font-bold text-slate-600">
                            {u.role}
                          </td>
                          <td className="p-3 text-slate-500">
                            {u.department_name || "Toàn Khoa"}
                          </td>
                          <td className="p-3 text-right">
                            {user?.role === "admin" ? (
                              <button
                                type="button"
                                onClick={() => {
                                  loginWithCredentials(u.username, defPwd);
                                  setActiveTab("tasks");
                                }}
                                className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-blue-50 hover:text-blue-700 text-slate-700 font-semibold cursor-pointer"
                              >
                                Chuyển sang TK này
                              </button>
                            ) : (
                              <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-semibold">
                                Đang hoạt động
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* MODAL ĐỔI MẬT KHẨU */}
      {showPwdModal && (
        <div
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowPwdModal(false);
          }}
          className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4"
        >
          <form
            role="dialog"
            aria-modal="true"
            onSubmit={handleChangePassword}
            className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-xl space-y-4 text-xs"
          >
            <h3 className="text-base font-bold text-slate-900">
              Đổi mật khẩu tài khoản
            </h3>
            {pwdMsg && (
              <div className="p-2.5 rounded-lg bg-blue-50 text-blue-800 font-semibold">
                {pwdMsg}
              </div>
            )}
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Mật khẩu hiện tại
              </label>
              <input
                type="password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-xl"
                required
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Mật khẩu mới (≥8 ký tự)
              </label>
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
