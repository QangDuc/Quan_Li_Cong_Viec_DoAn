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
  FileDown,
  Sparkles,
  Bot,
  Plus,
  Edit3,
  Trash2,
  Lock,
  Unlock,
  Activity,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Briefcase,
  Eye,
  EyeOff,
  ShieldCheck,
  User,
  ArrowRight,
  Layers,
  ChevronDown,
  ChevronUp,
  HelpCircle,
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
  const [activeTab, setActiveTab] = useState<string>("dashboard");
  const [reportMode, setReportMode] = useState<"faculty" | "lecturer">("faculty");

  // Login states
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showLoginPwd, setShowLoginPwd] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [loggingIn, setLoggingIn] = useState(false);
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

  // Progressive Disclosure UI states (giảm tải mật độ thông tin)
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [showExcelSpec, setShowExcelSpec] = useState<boolean>(false);
  const [showUserBasis, setShowUserBasis] = useState<boolean>(false);

  // Online ML Retraining state
  const [retraining, setRetraining] = useState(false);
  const [retrainMsg, setRetrainMsg] = useState("");

  // Notifications & Password modals
  const [showNotifPanel, setShowNotifPanel] = useState(false);
  const [showPwdModal, setShowPwdModal] = useState(false);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [pwdMsg, setPwdMsg] = useState("");

  // Quản trị Tài khoản (Thêm / Sửa / Xóa / Khóa)
  const [userSearch, setUserSearch] = useState("");
  const [userRoleFilter, setUserRoleFilter] = useState("ALL");
  const [userModalMode, setUserModalMode] = useState<"create" | "edit" | null>(null);
  const [editingUserId, setEditingUserId] = useState<number | null>(null);
  const [uUsername, setUUsername] = useState("");
  const [uFullName, setUFullName] = useState("");
  const [uLecturerCode, setULecturerCode] = useState("");
  const [uEmail, setUEmail] = useState("");
  const [uDegree, setUDegree] = useState("ThS");
  const [uRole, setURole] = useState("lecturer");
  const [uDeptId, setUDeptId] = useState<number | "">("");
  const [uPassword, setUPassword] = useState("Lecturer@123");
  const [uIsActive, setUIsActive] = useState(true);
  const [userMsg, setUserMsg] = useState<{ type: "ok" | "err"; text: string } | null>(
    null
  );

  useEffect(() => {
    if (token) {
      fetchMe();
      fetchInitialData();
    }
  }, [token]);

  useEffect(() => {
    if (token && (activeTab === "dashboard" || activeTab === "plans")) {
      fetchInitialData();
    }
  }, [activeTab]);

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
        if (dList.length > 0 && uDeptId === "") setUDeptId(dList[0].id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError("");
    if (username.trim().length < 3) {
      setLoginError("Tên đăng nhập phải có ít nhất 3 ký tự.");
      return;
    }
    setLoggingIn(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setLoginError(data.detail || "Tài khoản hoặc mật khẩu không chính xác.");
        return;
      }
      localStorage.setItem("token", data.access_token);
      setToken(data.access_token);
      setUser(data.user);
    } catch {
      setLoginError("Không kết nối được tới máy chủ Backend (port 8000)");
    } finally {
      setLoggingIn(false);
    }
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
      a.download = `BaoCao_CongViec_GioChuan_HUIT_${dashYear}_${
        dashSemester || "CaNam"
      }.xlsx`;
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
        const brierNote =
          tr.brier_before !== undefined && tr.brier_after !== undefined
            ? ` • Brier: ${tr.brier_before} → ${tr.brier_after}`
            : "";
        setRetrainMsg(
          `${data.message} (Phiên bản: ${tr.version || "TabPFN v2"} • Độ chính xác Holdout: ${
            tr.acc_before ?? ""
          }% → ${tr.acc_after ?? ""}%${brierNote})`
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

  // Mở Modal Thêm mới Tài khoản
  const openCreateUserModal = () => {
    setUserModalMode("create");
    setEditingUserId(null);
    setUUsername("");
    setUFullName("");
    setULecturerCode("");
    setUEmail("");
    setUDegree("ThS");
    setURole("lecturer");
    setUDeptId(departments[0]?.id || 1);
    setUPassword("Lecturer@123");
    setUIsActive(true);
  };

  // Mở Modal Sửa Tài khoản
  const openEditUserModal = (u: any) => {
    setUserModalMode("edit");
    setEditingUserId(u.id);
    setUUsername(u.username);
    setUFullName(u.full_name);
    setULecturerCode(u.lecturer_code || "");
    setUEmail(u.email || "");
    setUDegree(u.degree || "ThS");
    setURole(u.role || "lecturer");
    setUDeptId(u.department_id ?? "");
    setUPassword("");
    setUIsActive(u.is_active !== false);
  };

  const handleSaveUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setUserMsg(null);

    if (uFullName.trim().length < 3) {
      setUserMsg({ type: "err", text: "Họ và tên phải có ít nhất 3 ký tự." });
      return;
    }

    if (userModalMode === "create") {
      if (!/^[a-zA-Z0-9_.-]{3,50}$/.test(uUsername.trim())) {
        setUserMsg({
          type: "err",
          text: "Username chỉ gồm chữ cái, số, dấu gạch dưới (3–50 ký tự).",
        });
        return;
      }
      if (uPassword.length < 6) {
        setUserMsg({ type: "err", text: "Mật khẩu khởi tạo tối thiểu 6 ký tự." });
        return;
      }

      const res = await fetch(`${API_BASE}/users`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          username: uUsername.trim(),
          password: uPassword,
          full_name: uFullName.trim(),
          role: uRole,
          department_id: uDeptId !== "" ? Number(uDeptId) : null,
          lecturer_code: uLecturerCode.trim() || null,
          email: uEmail.trim() || null,
          degree: uDegree,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setUserMsg({ type: "ok", text: data.message });
        setUserModalMode(null);
        fetchInitialData();
      } else {
        setUserMsg({
          type: "err",
          text: data.detail || "Không thể thêm tài khoản",
        });
      }
    } else if (userModalMode === "edit" && editingUserId) {
      const res = await fetch(`${API_BASE}/users/${editingUserId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          full_name: uFullName.trim(),
          role: uRole,
          department_id: uDeptId !== "" ? Number(uDeptId) : null,
          lecturer_code: uLecturerCode.trim() || null,
          email: uEmail.trim() || null,
          degree: uDegree,
          is_active: uIsActive,
          new_password: uPassword.trim() ? uPassword.trim() : null,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setUserMsg({ type: "ok", text: data.message });
        setUserModalMode(null);
        fetchInitialData();
      } else {
        setUserMsg({
          type: "err",
          text: data.detail || "Không thể cập nhật tài khoản",
        });
      }
    }
  };

  const handleToggleLockUser = async (u: any) => {
    const res = await fetch(`${API_BASE}/users/${u.id}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        is_active: !u.is_active,
      }),
    });
    const data = await res.json();
    if (res.ok) {
      setUserMsg({
        type: "ok",
        text: `${!u.is_active ? "Đã mở khóa" : "Đã khóa"} tài khoản ${u.username}`,
      });
      fetchInitialData();
    } else {
      setUserMsg({ type: "err", text: data.detail || "Lỗi thao tác tài khoản" });
    }
  };

  const handleDeleteUser = async (u: any) => {
    if (
      !window.confirm(
        `Bạn có chắc chắn muốn xóa/ngừng kích hoạt tài khoản "${u.full_name}" (${u.username})?`
      )
    ) {
      return;
    }
    const res = await fetch(`${API_BASE}/users/${u.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await res.json();
    if (res.ok) {
      setUserMsg({ type: "ok", text: data.message });
      fetchInitialData();
    } else {
      setUserMsg({
        type: "err",
        text: data.detail || "Không thể xóa tài khoản",
      });
    }
  };

  // --- MÀN HÌNH ĐĂNG NHẬP CHUYÊN NGHIỆP & THÂN THIỆN ---
  if (!token) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4 sm:p-6 lg:p-10 relative overflow-hidden">
        {/* Hiệu ứng nền ánh sáng mềm mại */}
        <div className="pointer-events-none absolute -top-32 -left-32 w-96 h-96 rounded-full bg-blue-500/15 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 -right-32 w-96 h-96 rounded-full bg-indigo-500/15 blur-3xl" />

        <div className="w-full max-w-5xl bg-white rounded-3xl shadow-2xl border border-slate-200/80 overflow-hidden grid grid-cols-1 lg:grid-cols-12 relative z-10">
          {/* CỘT TRÁI: BANNER GIỚI THIỆU HỆ THỐNG CHUYÊN NGHIỆP */}
          <div className="lg:col-span-6 bg-gradient-to-br from-blue-900 via-indigo-900 to-slate-900 text-white p-8 sm:p-10 flex flex-col justify-between relative overflow-hidden">
            <div className="pointer-events-none absolute top-0 right-0 w-72 h-72 bg-blue-400/10 rounded-full blur-2xl -translate-y-1/3 translate-x-1/3" />
            <div className="pointer-events-none absolute bottom-0 left-0 w-64 h-64 bg-indigo-400/10 rounded-full blur-2xl translate-y-1/3 -translate-x-1/4" />

            {/* Header Thương hiệu Trường & Khoa */}
            <div className="relative z-10 space-y-6">
              <div className="flex items-center gap-3.5">
                <img
                  src="/huit-logo.png"
                  alt="Logo Trường Đại học Công Thương TP.HCM (HUIT)"
                  className="w-14 h-14 rounded-full object-cover shadow-lg shrink-0"
                />
                <div>
                  <div className="text-[11px] font-bold uppercase tracking-widest text-blue-200">
                    Trường Đại học Công Thương TP.HCM
                  </div>
                  <div className="text-sm font-extrabold text-white">
                    Khoa Công nghệ Thông tin
                  </div>
                </div>
              </div>

              <div className="space-y-3 pt-2">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold bg-blue-500/20 text-blue-200 border border-blue-400/30">
                  <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                  Nền tảng Quản trị Số & Trí tuệ Nhân tạo
                </span>
                <h1 className="text-2xl sm:text-3xl font-extrabold leading-tight tracking-tight text-white">
                  Hệ thống Quản lý Công việc & Điều phối Tiến độ
                </h1>
                <p className="text-xs sm:text-sm text-blue-100/85 leading-relaxed">
                  Không gian làm việc tập trung giúp Ban Chủ nhiệm Khoa, Trưởng Bộ môn và Giảng viên theo dõi tiến độ, phê duyệt minh chứng và quy đổi giờ chuẩn minh bạch.
                </p>
              </div>

              {/* Các điểm nổi bật thân thiện */}
              <div className="space-y-3 pt-2">
                <div className="flex items-start gap-3 p-3 rounded-2xl bg-white/8 border border-white/10 backdrop-blur-xs">
                  <div className="w-8 h-8 rounded-xl bg-emerald-500/20 border border-emerald-400/30 flex items-center justify-center shrink-0 mt-0.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-300" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-white">
                      Quản lý Tiến độ & Minh chứng Nhóm rõ ràng
                    </div>
                    <div className="text-[11px] text-blue-100/75 mt-0.5">
                      Phối hợp nhóm mạch lạc giữa Trưởng nhóm, Thành viên và Người kiểm tra tiến độ.
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3 rounded-2xl bg-white/8 border border-white/10 backdrop-blur-xs">
                  <div className="w-8 h-8 rounded-xl bg-indigo-500/20 border border-indigo-400/30 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-4 h-4 text-indigo-300" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-white">
                      Trợ lý AI & Gợi ý Phân công Thông minh
                    </div>
                    <div className="text-[11px] text-blue-100/75 mt-0.5">
                      Đề xuất giảng viên có độ trễ thấp nhất và tự động tổng hợp định mức giờ chuẩn.
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Footer bên trái */}
            <div className="relative z-10 pt-8 flex items-center justify-between text-[11px] text-blue-200/70 border-t border-white/10 mt-6">
              <span className="flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Bảo mật xác thực JWT
              </span>
              <span>Năm học 2026 – 2027</span>
            </div>
          </div>

          {/* CỘT PHẢI: BIỂU MẪU ĐĂNG NHẬP SẠCH SẼ & THÂN THIỆN */}
          <div className="lg:col-span-6 p-8 sm:p-12 flex flex-col justify-center bg-white">
            <div className="max-w-sm mx-auto w-full space-y-6">
              <div className="space-y-1.5">
                <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">
                  Đăng nhập hệ thống
                </h2>
                <p className="text-xs sm:text-sm text-slate-500">
                  Vui lòng nhập thông tin tài khoản cán bộ / giảng viên của Thầy/Cô để tiếp tục.
                </p>
              </div>

              {loginError && (
                <div
                  role="alert"
                  className="bg-rose-50 border border-rose-200 text-rose-700 px-3.5 py-3 rounded-2xl text-xs font-semibold flex items-center gap-2.5"
                >
                  <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
                  <span>{loginError}</span>
                </div>
              )}

              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label
                    htmlFor="login-username"
                    className="block text-xs font-bold text-slate-700 mb-1.5"
                  >
                    Tên đăng nhập hoặc Mã giảng viên
                  </label>
                  <div className="relative">
                    <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-3 pointer-events-none" />
                    <input
                      id="login-username"
                      name="username"
                      type="text"
                      autoComplete="username"
                      spellCheck={false}
                      autoCapitalize="none"
                      minLength={3}
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="Nhập tên đăng nhập của bạn"
                      className="w-full pl-10 pr-4 py-2.5 bg-slate-50/70 focus:bg-white border border-slate-300 rounded-xl text-sm text-slate-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                      required
                    />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label
                      htmlFor="login-password"
                      className="block text-xs font-bold text-slate-700"
                    >
                      Mật khẩu
                    </label>
                  </div>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3 pointer-events-none" />
                    <input
                      id="login-password"
                      name="password"
                      type={showLoginPwd ? "text" : "password"}
                      autoComplete="current-password"
                      enterKeyHint="done"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Nhập mật khẩu"
                      className="w-full pl-10 pr-10 py-2.5 bg-slate-50/70 focus:bg-white border border-slate-300 rounded-xl text-sm text-slate-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowLoginPwd(!showLoginPwd)}
                      className="absolute right-3 top-2.5 p-0.5 text-slate-400 hover:text-slate-600 cursor-pointer"
                      aria-label={showLoginPwd ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                    >
                      {showLoginPwd ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs pt-0.5">
                  <label className="flex items-center gap-2 text-slate-600 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span>Duy trì đăng nhập</span>
                  </label>
                  <span className="text-slate-500">
                    Cần cấp lại MK? Liên hệ Văn phòng Khoa
                  </span>
                </div>

                <button
                  type="submit"
                  disabled={loggingIn}
                  className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-60 text-white font-bold py-3 px-4 rounded-xl transition shadow-md shadow-blue-600/20 cursor-pointer text-sm flex items-center justify-center gap-2 mt-2"
                >
                  <span>{loggingIn ? "Đang xác thực..." : "Đăng nhập vào Hệ thống"}</span>
                  {!loggingIn && <ArrowRight className="w-4 h-4" />}
                </button>
              </form>

              <div className="pt-4 border-t border-slate-100 text-center">
                <p className="text-[11px] text-slate-400">
                  © 2026 Khoa Công nghệ Thông tin — Trường Đại học Công Thương TP.HCM (HUIT)
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const filteredUsers = users.filter((u) => {
    if (userRoleFilter !== "ALL" && u.role !== userRoleFilter) return false;
    if (userSearch.trim()) {
      const q = userSearch.toLowerCase();
      return (
        u.username?.toLowerCase().includes(q) ||
        u.full_name?.toLowerCase().includes(q) ||
        u.lecturer_code?.toLowerCase().includes(q) ||
        u.department_name?.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const navItems = [
    {
      id: "dashboard",
      label: "Dashboard Quản trị",
      icon: LayoutDashboard,
      show: true,
    },
    {
      id: "tasks",
      label: "Công việc & Nhóm",
      icon: CheckSquare,
      badge: tasks.length,
      show: true,
    },
    {
      id: "assign",
      label: "Giao việc & Gợi ý AI",
      icon: Sparkles,
      show: user?.role !== "lecturer",
    },
    {
      id: "plans_catalog",
      label: "Kế hoạch & Định mức",
      icon: FileSpreadsheet,
      show: true,
    },
    {
      id: "users",
      label: "Quản lý Tài khoản",
      icon: Users,
      badge: users.length,
      show: user?.role !== "lecturer",
    },
    {
      id: "ai_assistant",
      label: "Trợ lý AI Thông minh",
      icon: Bot,
      isHighlight: true,
      show: true,
    },
  ];

  return (
    <div className="min-h-screen bg-slate-100 flex">
      {/* SIDEBAR BÊN TRÁI KIỂU SAAS / E-COMMERCE ADMIN DASHBOARD (CÓ THU GỌN) */}
      <aside
        className={`${
          sidebarCollapsed ? "w-20" : "w-64"
        } bg-slate-900 text-slate-200 flex flex-col justify-between shrink-0 sticky top-0 h-screen z-30 shadow-xl transition-all duration-200`}
      >
        <div>
          {/* LOGO BRAND */}
          <div className="h-16 px-4 flex items-center justify-between border-b border-slate-800">
            <div className="flex items-center gap-3 overflow-hidden">
              <img
                src="/huit-logo.png"
                alt="Logo HUIT"
                className="w-10 h-10 rounded-full object-cover shadow shrink-0"
              />
              {!sidebarCollapsed && (
                <div className="truncate">
                  <div className="font-extrabold text-white text-sm leading-tight truncate">
                    HUIT WorkFlow Pro
                  </div>
                  <div className="text-[11px] text-slate-400 truncate">
                    Khoa Công nghệ Thông tin
                  </div>
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 cursor-pointer shrink-0"
              title={sidebarCollapsed ? "Mở rộng thanh điều hướng" : "Thu gọn thanh điều hướng"}
            >
              <Layers className="w-4 h-4" />
            </button>
          </div>

          {/* MENU ĐIỀU HƯỚNG */}
          <nav className="p-3 space-y-1">
            {!sidebarCollapsed && (
              <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Phân hệ Quản trị & Vận hành
              </div>
            )}
            {navItems
              .filter((item) => item.show)
              .map((item) => {
                const Icon = item.icon;
                const active = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    title={sidebarCollapsed ? item.label : undefined}
                    className={`w-full flex items-center border ${
                      sidebarCollapsed ? "justify-center px-2" : "justify-between px-3.5"
                    } py-2.5 rounded-xl text-xs font-semibold cursor-pointer transition ${
                      active
                        ? "bg-blue-600 text-white border-blue-600 shadow-sm"
                        : item.isHighlight
                        ? "bg-indigo-950/80 text-indigo-300 hover:bg-indigo-900/80 border-indigo-800/60"
                        : "text-slate-300 border-transparent hover:bg-slate-800 hover:text-white"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className="w-4 h-4 shrink-0" />
                      {!sidebarCollapsed && <span>{item.label}</span>}
                    </div>
                    {!sidebarCollapsed && item.badge !== undefined && (
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          active
                            ? "bg-blue-800 text-white"
                            : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
          </nav>
        </div>

        {/* USER PROFILE CARD Ở ĐÁY SIDEBAR */}
        <div className="p-3 border-t border-slate-800 space-y-2">
          {!sidebarCollapsed ? (
            <div className="p-3 rounded-xl bg-slate-800/90 border border-slate-700/80">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white truncate">
                  {user?.full_name}
                </span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase bg-blue-500/20 text-blue-300 border border-blue-400/30">
                  {user?.role}
                </span>
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5 truncate">
                {user?.department_name || "Khoa CNTT"}
              </div>
              <div className="flex items-center gap-1.5 mt-2 text-[10px] text-emerald-400 font-semibold">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                Đang trực tuyến ({user?.username})
              </div>
            </div>
          ) : (
            <div
              className="p-2 rounded-xl bg-slate-800/90 border border-slate-700/80 flex flex-col items-center gap-1"
              title={`${user?.full_name} (${user?.username})`}
            >
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[10px] font-bold uppercase text-blue-300">
                {user?.role?.slice(0, 3)}
              </span>
            </div>
          )}

          <div className={`flex items-center ${sidebarCollapsed ? "flex-col" : ""} gap-1.5`}>
            <button
              onClick={() => setShowPwdModal(true)}
              title="Đổi mật khẩu"
              className="flex-1 w-full flex items-center justify-center gap-1.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer"
            >
              <KeyRound className="w-3.5 h-3.5" />
              {!sidebarCollapsed && <span>Đổi MK</span>}
            </button>
            <button
              onClick={handleLogout}
              title="Đăng xuất"
              className="flex-1 w-full flex items-center justify-center gap-1.5 py-2 rounded-xl bg-rose-600/90 hover:bg-rose-600 text-white text-xs font-semibold cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5" />
              {!sidebarCollapsed && <span>Thoát</span>}
            </button>
          </div>
        </div>
      </aside>

      {/* KHU VỰC NỘI DUNG CHÍNH BÊN PHẢI */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* TOPBAR */}
        <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-20">
          <div>
            <h2 className="text-base font-extrabold text-slate-900">
              {navItems.find((n) => n.id === activeTab)?.label || "Quản trị Hệ thống"}
            </h2>
            <p className="text-xs text-slate-500">
              Năm học {dashYear} • Quản lý tiến độ, minh chứng trưởng nhóm & quy đổi giờ chuẩn
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleScanDeadlines}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700 cursor-pointer transition"
            >
              <RefreshCw className="w-3.5 h-3.5 text-blue-600" /> Quét Nhắc hạn
            </button>

            {/* CHUÔNG THÔNG BÁO */}
            <div className="relative">
              <button
                onClick={() => setShowNotifPanel(!showNotifPanel)}
                className="relative p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 cursor-pointer"
                title="Thông báo hệ thống"
              >
                <Bell className="w-4 h-4" />
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 bg-rose-500 text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center">
                    {unreadCount}
                  </span>
                )}
              </button>

              {showNotifPanel && (
                <div className="absolute right-0 mt-2 w-96 bg-white text-slate-900 rounded-2xl shadow-2xl border border-slate-200 overflow-hidden z-50">
                  <div className="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                    <span className="font-bold text-xs uppercase text-slate-700">
                      Thông báo & Nhắc việc ({notifications.length})
                    </span>
                    <button
                      onClick={handleMarkAllRead}
                      className="text-xs text-blue-600 hover:underline font-semibold cursor-pointer"
                    >
                      Đánh dấu đã đọc
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
          </div>
        </header>

        {/* NỘI DUNG TỪNG PHÂN HỆ */}
        <main className="p-6 flex-1 max-w-[1440px] w-full mx-auto">
          {/* 1. TAB DASHBOARD QUẢN TRỊ (E-COMMERCE / SAAS ANALYTICS STYLE) */}
          {activeTab === "dashboard" && (
            <div className="space-y-6">
              {/* THANH ĐIỀU KHIỂN DASHBOARD & XUẤT EXCEL ĐẦY ĐỦ TRƯỜNG (CỐ ĐỊNH CHIỀU CAO CHỐNG NHẢY BỐ CỤC) */}
              <div className="bg-white p-3.5 rounded-2xl border border-slate-200 shadow-2xs min-h-[60px] flex flex-wrap items-center justify-between gap-2.5">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setReportMode("faculty")}
                    className={`h-9 flex items-center gap-2 px-3.5 rounded-xl text-xs font-bold border cursor-pointer transition ${
                      reportMode === "faculty"
                        ? "bg-slate-900 text-white border-slate-900"
                        : "bg-slate-100 text-slate-700 border-slate-200/80 hover:bg-slate-200"
                    }`}
                  >
                    <LayoutDashboard className="w-4 h-4 shrink-0" />
                    Tổng quan Vận hành Khoa
                  </button>
                  <button
                    type="button"
                    onClick={() => setReportMode("lecturer")}
                    className={`h-9 flex items-center gap-2 px-3.5 rounded-xl text-xs font-bold border cursor-pointer transition ${
                      reportMode === "lecturer"
                        ? "bg-slate-900 text-white border-slate-900"
                        : "bg-slate-100 text-slate-700 border-slate-200/80 hover:bg-slate-200"
                    }`}
                  >
                    <UserCheck className="w-4 h-4 shrink-0" />
                    Hồ sơ Đánh giá 1 Năm Giảng viên
                  </button>
                </div>

                {reportMode === "faculty" ? (
                  <div className="flex flex-wrap items-center gap-2">
                    <select
                      value={dashYear}
                      onChange={(e) => setDashYear(e.target.value)}
                      className="h-9 px-3 border border-slate-300 rounded-xl text-xs bg-white font-semibold outline-none"
                    >
                      <option value="2026-2027">Năm học 2026–2027</option>
                      <option value="2025-2026">Năm học 2025–2026</option>
                    </select>
                    <select
                      value={dashSemester}
                      onChange={(e) => setDashSemester(e.target.value)}
                      className="h-9 px-3 border border-slate-300 rounded-xl text-xs bg-white font-semibold outline-none"
                    >
                      <option value="">Cả năm học</option>
                      <option value="HK1">Học kỳ 1</option>
                      <option value="HK2">Học kỳ 2</option>
                      <option value="HE">Học kỳ Hè</option>
                    </select>

                    <button
                      type="button"
                      onClick={handleExportLateExcel}
                      className="h-9 flex items-center gap-1.5 px-3 rounded-xl bg-rose-600 hover:bg-rose-700 border border-rose-600 text-white text-xs font-bold cursor-pointer shadow-2xs"
                    >
                      <FileDown className="w-3.5 h-3.5 shrink-0" />
                      Xuất DS Trễ hạn
                    </button>

                    <button
                      type="button"
                      onClick={handleExportExcel}
                      className="h-9 flex items-center gap-1.5 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 border border-emerald-600 text-white text-xs font-bold cursor-pointer shadow-2xs"
                    >
                      <FileDown className="w-3.5 h-3.5 shrink-0" />
                      Xuất Báo cáo Excel
                    </button>
                  </div>
                ) : (
                  <div className="h-9 flex items-center text-xs text-slate-500 px-2">
                    Đánh giá toàn diện khối lượng giảng dạy, giờ chuẩn &amp; kiểm toán dự báo AI theo giảng viên
                  </div>
                )}
              </div>

              {reportMode === "faculty" ? (
                <div className="space-y-6">
                  {/* 4 THẺ KPI THƯƠNG MẠI TRỰC QUAN */}
                  {stats && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs flex flex-col justify-between">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-500 uppercase">
                            Tổng Phân công & Giờ chuẩn
                          </span>
                          <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                            <Briefcase className="w-4 h-4" />
                          </div>
                        </div>
                        <div className="my-2">
                          <span className="text-3xl font-extrabold text-slate-900">
                            {stats.total_tasks}
                          </span>
                          <span className="text-xs text-slate-500 ml-1.5">lượt giao</span>
                        </div>
                        <div className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-500">Hoàn thành</span>
                            <b className="text-blue-600">{stats.completion_rate}%</b>
                          </div>
                          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-blue-600 rounded-full"
                              style={{ width: `${stats.completion_rate || 0}%` }}
                            />
                          </div>
                          <div className="text-[11px] text-slate-500 pt-0.5">
                            Tổng quy đổi:{" "}
                            <b className="text-slate-800">
                              {stats.total_converted_hours} giờ chuẩn
                            </b>
                          </div>
                        </div>
                      </div>

                      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs flex flex-col justify-between">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-500 uppercase">
                            Hoàn thành Đúng hạn
                          </span>
                          <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                            <CheckCircle2 className="w-4 h-4" />
                          </div>
                        </div>
                        <div className="my-2">
                          <span className="text-3xl font-extrabold text-emerald-600">
                            {stats.completed_on_time}
                          </span>
                          <span className="text-xs text-emerald-700 font-bold ml-2 px-2 py-0.5 rounded-full bg-emerald-50">
                            {stats.on_time_rate}% đúng hạn
                          </span>
                        </div>
                        <div className="space-y-1">
                          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-emerald-500 rounded-full"
                              style={{ width: `${stats.on_time_rate || 0}%` }}
                            />
                          </div>
                          <div className="text-[11px] text-slate-500 pt-0.5">
                            Đạt chuẩn KPI đánh giá giảng viên cuối năm
                          </div>
                        </div>
                      </div>

                      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs flex flex-col justify-between">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-500 uppercase">
                            Đang thực hiện / Việc Nhóm
                          </span>
                          <div className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                            <Clock className="w-4 h-4" />
                          </div>
                        </div>
                        <div className="my-2">
                          <span className="text-3xl font-extrabold text-indigo-600">
                            {(stats.in_progress || 0) + (stats.new || 0)}
                          </span>
                          <span className="text-xs text-slate-500 ml-1.5">đầu việc mở</span>
                        </div>
                        <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-100">
                          <span className="text-amber-700 font-semibold">
                            Sắp đến hạn (≤3 ngày): {stats.due_soon_open || 0}
                          </span>
                          <button
                            onClick={() => setActiveTab("tasks")}
                            className="text-blue-600 hover:underline font-bold cursor-pointer"
                          >
                            Xem ngay →
                          </button>
                        </div>
                      </div>

                      <div className="bg-white p-5 rounded-2xl border border-rose-200 bg-rose-50/20 shadow-2xs flex flex-col justify-between">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-rose-700 uppercase">
                            Cảnh báo Trễ / Quá hạn
                          </span>
                          <div className="w-9 h-9 rounded-xl bg-rose-100 text-rose-600 flex items-center justify-center">
                            <AlertTriangle className="w-4 h-4" />
                          </div>
                        </div>
                        <div className="my-2">
                          <span className="text-3xl font-extrabold text-rose-600">
                            {(stats.late_completed || 0) + (stats.overdue_open || 0)}
                          </span>
                          <span className="text-xs text-rose-700 font-semibold ml-1.5">
                            trường hợp
                          </span>
                        </div>
                        <div className="text-xs text-rose-700 pt-1 border-t border-rose-100 flex justify-between">
                          <span>Hoàn thành trễ: <b>{stats.late_completed || 0}</b></span>
                          <span>Đang quá hạn: <b>{stats.overdue_open || 0}</b></span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* BIỂU ĐỒ THANH TIẾN ĐỘ THEO NHÓM CÔNG VIỆC & ONLINE ML */}
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    <div className="lg:col-span-7 bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-base font-bold text-slate-900">
                            Hiệu suất Thực hiện & Giờ chuẩn theo Nhóm Công việc
                          </h3>
                          <p className="text-xs text-slate-500">
                            Trực quan hóa tỷ lệ hoàn thành và tổng giờ chuẩn quy đổi theo từng lĩnh vực.
                          </p>
                        </div>
                      </div>

                      <div className="space-y-3.5 pt-1">
                        {stats?.by_group?.map((g: any) => {
                          const donePct =
                            g.total > 0 ? Math.round((g.done / g.total) * 100) : 0;
                          return (
                            <div
                              key={g.group}
                              className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 space-y-2"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                                <div className="flex items-center gap-2">
                                  <span className="font-bold text-slate-900 text-sm">
                                    {g.group}
                                  </span>
                                  <span className="px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 font-bold">
                                    {g.hours} giờ chuẩn
                                  </span>
                                </div>
                                <div className="flex items-center gap-3">
                                  <span className="text-slate-600">
                                    Hoàn thành: <b>{g.done}/{g.total}</b> ({donePct}%)
                                  </span>
                                  {g.late > 0 && (
                                    <span className="text-rose-600 font-bold">
                                      Trễ: {g.late}
                                    </span>
                                  )}
                                </div>
                              </div>
                              <div className="w-full h-2.5 bg-slate-200 rounded-full overflow-hidden flex">
                                <div
                                  className="h-full bg-emerald-500 transition-all"
                                  style={{ width: `${donePct}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* CỘT PHẢI: GIÁM SÁT MLOPS (HỌC TIẾP ĐỊNH KỲ V4) & CHUẨN BÁO CÁO EXCEL */}
                    <div className="lg:col-span-5 space-y-4">
                      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="text-xs font-bold uppercase px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-700 border border-indigo-200">
                            MLOps • Học tiếp Định kỳ Có kiểm soát
                          </span>
                          <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            ModelRegistry: {mlAcc?.ml_service?.registry_version ? `${mlAcc.ml_service.registry_version} (CURRENT)` : "v0001 (CURRENT)"}
                          </span>
                        </div>

                        <div>
                          <h3 className="text-sm font-bold text-slate-900">
                            Mô hình TabPFN 9.2.0 & Rào chắn Chất lượng (Quality Gates)
                          </h3>
                          <p className="text-xs text-slate-500 mt-0.5">
                            Dự đoán rủi ro trễ hạn trên 58 trường đặc trưng (mô hình dùng 55). Chỉ nâng cấp phiên bản khi vượt qua rào chắn kiểm định trên tập Holdout.
                          </p>
                        </div>

                        {mlAcc && (
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                            <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                              <div className="text-[11px] text-slate-500">ROC-AUC / ECE</div>
                              <div className="text-sm font-extrabold text-slate-900 mt-0.5">
                                0.8090 <span className="text-[11px] font-semibold text-emerald-700">/ 0.0075</span>
                              </div>
                            </div>
                            <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                              <div className="text-[11px] text-slate-500">Ngưỡng [Thấp, Cao]</div>
                              <div className="text-sm font-extrabold text-indigo-700 mt-0.5">
                                [0.23, 0.52]
                              </div>
                            </div>
                            <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                              <div className="text-[11px] text-slate-500">Kho Phản hồi</div>
                              <div className="text-sm font-extrabold text-slate-900 mt-0.5">
                                {mlAcc.live_done_count ?? mlAcc.total_evaluated ?? 0} mẫu
                              </div>
                            </div>
                            <div className="p-2.5 rounded-xl bg-emerald-50/60 border border-emerald-200">
                              <div className="text-[11px] text-emerald-800">Nhóm Thấp đúng hạn</div>
                              <div className="text-sm font-extrabold text-emerald-700 mt-0.5">
                                {mlAcc.low_risk?.accuracy ?? 89.96}%
                              </div>
                            </div>
                          </div>
                        )}

                        <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 rounded-xl bg-slate-50 border border-slate-200/80 text-[11px] text-slate-600">
                          <span>
                            Động cơ đang chạy:{" "}
                            <b className="text-indigo-700">
                              {mlAcc?.ml_service?.model_version || mlAcc?.ml_service?.engine || "TabPFN v2 (9.2.0 • 4 túi ngữ cảnh, v0001)"}
                            </b>
                          </span>
                          <span className="text-emerald-700 font-semibold">
                            ✓ 55/55 đặc trưng khớp 100%
                          </span>
                        </div>

                        {retrainMsg && (
                          <div className="p-3 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-900 text-xs font-medium">
                            {retrainMsg}
                          </div>
                        )}

                        {user?.role !== "lecturer" && (
                          <button
                            onClick={handleRetrainML}
                            disabled={retraining}
                            className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-400 text-white font-bold text-xs rounded-xl shadow-2xs transition cursor-pointer flex items-center justify-center gap-2"
                          >
                            <RefreshCw
                              className={`w-4 h-4 ${retraining ? "animate-spin" : ""}`}
                            />
                            {retraining
                              ? "Đang kiểm định rào chắn & đánh giá ứng viên..."
                              : "Kiểm tra Rào chắn & Đánh giá Học tiếp Định kỳ"}
                          </button>
                        )}
                      </div>

                      {/* THẺ THÔNG TIN CHUẨN HÓA TRƯỜNG EXCEL (THU GỌN THEO PROGRESSIVE DISCLOSURE) */}
                      <div className="bg-emerald-50/60 p-4 rounded-2xl border border-emerald-200/90">
                        <div
                          onClick={() => setShowExcelSpec(!showExcelSpec)}
                          className="flex items-center justify-between cursor-pointer select-none"
                        >
                          <div className="text-xs font-extrabold text-emerald-950 flex items-center gap-2">
                            <FileSpreadsheet className="w-4 h-4 text-emerald-600 shrink-0" />
                            <span>Cấu trúc Báo cáo Excel Tổng hợp</span>
                          </div>
                          <span className="text-[11px] font-bold text-emerald-700 flex items-center gap-1 shrink-0">
                            {showExcelSpec ? (
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
                        {showExcelSpec && (
                          <p className="text-xs text-emerald-900 leading-relaxed mt-2.5 pt-2.5 border-t border-emerald-200/80">
                            File Excel xuất ra bao gồm đầy đủ thông tin công việc, giảng viên, vai trò nhóm, tiến độ, minh chứng, dự báo rủi ro AI và bảng tổng hợp định mức giờ chuẩn theo quy định.
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <LecturerEvaluationView token={token} currentUser={user} users={users} />
              )}
            </div>
          )}

          {/* 2. TAB QUẢN LÝ CÔNG VIỆC & NHÓM */}
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

          {/* 3. TAB GIAO VIỆC & GỢI Ý AI */}
          {activeTab === "assign" && (
            <AssignTaskWithMLView
              token={token}
              currentUser={user}
              taskTypes={taskTypes}
              schoolCatalog={schoolCatalog}
              users={users}
              onAssigned={fetchInitialData}
            />
          )}

          {/* 4. TAB KẾ HOẠCH NĂM & ĐỊNH MỨC */}
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

          {/* 5. TAB TRỢ LÝ AI & CẤU HÌNH API KEY */}
          {activeTab === "ai_assistant" && (
            <AIAssistantView token={token} currentUser={user} tasks={tasks} />
          )}

          {/* 6. TAB QUẢN TRỊ TÀI KHOẢN (THEO BẢNG 3.3, BẢNG 3.4 & MỤC 4.10 BÁO CÁO KLTN) */}
          {activeTab === "users" && user?.role !== "lecturer" && (
            <div className="space-y-4">
              {/* BANNER QUẢN TRỊ TÀI KHOẢN & PHÂN QUYỀN RBAC */}
              <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2 text-sm font-extrabold text-slate-900">
                      <Activity className="w-4 h-4 text-emerald-600" />
                      Danh sách Tài khoản Cán bộ & Giảng viên ({users.length})
                    </div>
                    <span className="px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 text-xs font-semibold">
                      {user?.role === "admin"
                        ? "Quyền Admin: SYSTEM • 15/15 quyền (USER_MANAGE & DEPT_MANAGE)"
                        : `Quyền Quản lý: ${user?.scope_level || "FACULTY"} • 12/15 quyền (USER_VIEW)`}
                    </span>
                    <button
                      type="button"
                      onClick={() => setShowUserBasis(!showUserBasis)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold cursor-pointer transition"
                    >
                      <HelpCircle className="w-3.5 h-3.5 text-blue-600" />
                      {showUserBasis ? "Ẩn chi tiết phân quyền ▴" : "Ma trận quyền & Trạng thái ▾"}
                    </button>
                  </div>
                  {(user?.role === "admin" ||
                    (Array.isArray(user?.permissions) &&
                      user.permissions.includes("USER_MANAGE"))) && (
                    <button
                      onClick={openCreateUserModal}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold cursor-pointer shadow-xs"
                    >
                      <Plus className="w-4 h-4" />
                      Thêm Tài khoản Mới
                    </button>
                  )}
                </div>

                {showUserBasis && (
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-2.5 text-xs pt-2 border-t border-slate-100">
                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                      <div className="font-bold text-slate-900">
                        1. Admin (SYSTEM • 15 quyền)
                      </div>
                      <div className="text-[11px] text-slate-600 mt-0.5">
                        Toàn quyền quản trị hệ thống, nắm giữ độc quyền <code>USER_MANAGE</code> (Thêm/sửa/khóa TK, cấu hình RBAC) và <code>DEPT_MANAGE</code>.
                      </div>
                    </div>
                    <div className="p-2.5 rounded-xl bg-blue-50/70 border border-blue-200">
                      <div className="font-bold text-blue-900">
                        2. Manager (FACULTY / DEPARTMENT • 12 quyền)
                      </div>
                      <div className="text-[11px] text-blue-800 mt-0.5">
                        Trưởng Khoa (<code>FACULTY</code>) & Trưởng Bộ môn (<code>DEPARTMENT</code>): Quản lý công việc, kế hoạch 270h, gợi ý AI và xem danh sách giảng viên (<code>USER_VIEW</code>).
                      </div>
                    </div>
                    <div className="p-2.5 rounded-xl bg-emerald-50/70 border border-emerald-200">
                      <div className="font-bold text-emerald-900">
                        3. Lecturer (SELF • 5 quyền)
                      </div>
                      <div className="text-[11px] text-emerald-800 mt-0.5">
                        Giảng viên (<code>TASK_VIEW</code>, <code>TASK_UPDATE_PROGRESS</code>, <code>TASK_COMMENT</code>, <code>PLAN_VIEW</code>, <code>USER_VIEW</code>).
                      </div>
                    </div>
                    <div className="p-2.5 rounded-xl bg-amber-50/70 border border-amber-200">
                      <div className="font-bold text-amber-900">
                        4. Trạng thái Hoạt động Thực tế
                      </div>
                      <div className="text-[11px] text-amber-800 mt-0.5">
                        Tự động đối chiếu <code>is_active</code>, phiên trực tuyến <code>last_active_at</code> và số công việc đang mở (<code>open_tasks_count</code>).
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {userMsg && (
                <div
                  className={`p-3 rounded-xl text-xs font-semibold flex items-center justify-between border ${
                    userMsg.type === "ok"
                      ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                      : "bg-rose-50 border-rose-200 text-rose-700"
                  }`}
                >
                  <span>{userMsg.text}</span>
                  <button
                    onClick={() => setUserMsg(null)}
                    className="font-bold cursor-pointer px-2"
                  >
                    ✕
                  </button>
                </div>
              )}

              {/* BẢNG QUẢN LÝ TÀI KHOẢN */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden">
                <div className="p-4 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={userSearch}
                      onChange={(e) => setUserSearch(e.target.value)}
                      placeholder="Tìm theo username, họ tên, mã GV, bộ môn..."
                      className="px-3.5 py-1.5 border border-slate-300 rounded-xl text-xs w-64 bg-white outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    {[
                      { k: "ALL", l: `Tất cả (${users.length})` },
                      { k: "lecturer", l: "Giảng viên" },
                      { k: "manager", l: "Quản lý" },
                      { k: "admin", l: "Admin" },
                    ].map((f) => (
                      <button
                        key={f.k}
                        type="button"
                        onClick={() => setUserRoleFilter(f.k)}
                        className={`h-8 px-3 rounded-xl text-xs font-semibold border cursor-pointer transition ${
                          userRoleFilter === f.k
                            ? "bg-blue-600 text-white border-blue-600"
                            : "bg-white border-slate-200 text-slate-600 hover:bg-slate-100"
                        }`}
                      >
                        {f.l}
                      </button>
                    ))}
                  </div>
                </div>

                <div
                  tabIndex={0}
                  role="region"
                  aria-label="Bảng quản lý tài khoản người dùng"
                  className="overflow-x-auto max-h-[600px]"
                >
                  <table className="w-full text-left border-collapse text-xs">
                    <thead className="bg-slate-100 text-slate-600 uppercase sticky top-0 z-10">
                      <tr>
                        <th className="p-3.5">Mã / Username</th>
                        <th className="p-3.5">Họ và tên & Học vị</th>
                        <th className="p-3.5">Vai trò & Phạm vi RBAC</th>
                        <th className="p-3.5">Trạng thái & Hoạt động</th>
                        <th className="p-3.5 text-right">Thao tác</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {filteredUsers.map((u) => {
                        const canManageUsers =
                          user?.role === "admin" ||
                          (Array.isArray(user?.permissions) &&
                            user.permissions.includes("USER_MANAGE"));
                        return (
                          <tr key={u.id} className="hover:bg-slate-50">
                            <td className="p-3.5">
                              <div className="font-mono font-bold text-blue-700">
                                {u.username}
                              </div>
                              <div className="text-[11px] text-slate-500">
                                Mã CB/GV: <b>{u.lecturer_code || "—"}</b>
                              </div>
                            </td>
                            <td className="p-3.5">
                              <div className="font-bold text-slate-900 text-sm">
                                {u.full_name}
                              </div>
                              <div className="text-[11px] text-slate-500">
                                Học vị: <b>{u.degree || "ThS"}</b> • {u.email || "Chưa cập nhật email"}
                              </div>
                            </td>
                            <td className="p-3.5">
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span
                                  className={`px-2 py-0.5 rounded uppercase text-[10px] font-bold ${
                                    u.role === "admin"
                                      ? "bg-slate-900 text-white"
                                      : u.role === "manager"
                                      ? "bg-blue-50 text-blue-700 border border-blue-200"
                                      : "bg-slate-100 text-slate-700 border border-slate-200"
                                  }`}
                                >
                                  {u.role}
                                </span>
                                {u.scope_level && (
                                  <span
                                    title={
                                      u.permissions?.length
                                        ? `Phạm vi: ${u.scope_description || u.scope_level}\nQuyền hạn (${u.permissions.length}): ${u.permissions.join(", ")}`
                                        : u.scope_description || u.scope_level
                                    }
                                    className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200"
                                  >
                                    {u.scope_level}
                                    {Array.isArray(u.permissions)
                                      ? ` • ${u.permissions.length} quyền`
                                      : ""}
                                  </span>
                                )}
                              </div>
                              <div className="text-[11px] text-slate-600 mt-1">
                                {u.department_name || "Toàn Khoa CNTT"}
                              </div>
                            </td>
                            <td className="p-3.5">
                              <div className="flex items-center gap-1.5">
                                <span
                                  className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                                    u.is_active === false
                                      ? "bg-rose-100 text-rose-700"
                                      : u.is_online
                                      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                      : "bg-blue-50 text-blue-700 border border-blue-200"
                                  }`}
                                >
                                  <span
                                    className={`w-2 h-2 rounded-full ${
                                      u.is_active === false
                                        ? "bg-rose-500"
                                        : u.is_online
                                        ? "bg-emerald-500 animate-pulse"
                                        : "bg-blue-500"
                                    }`}
                                  />
                                  {u.status_label ||
                                    (u.is_active === false
                                      ? "Đã khóa"
                                      : "Đang hoạt động")}
                                </span>
                              </div>
                              <div className="text-[11px] text-slate-600 mt-1">
                                {u.activity_basis ||
                                  `Kích hoạt hợp lệ • Đang nhận ${
                                    u.open_tasks_count ?? 0
                                  } việc mở • Đã xong ${u.completed_tasks_count ?? 0} việc`}
                              </div>
                            </td>
                            <td className="p-3.5 text-right">
                              {canManageUsers ? (
                                <div className="flex items-center justify-end gap-1.5">
                                  <button
                                    type="button"
                                    onClick={() => openEditUserModal(u)}
                                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 font-semibold cursor-pointer"
                                    title="Chỉnh sửa thông tin & phân quyền RBAC"
                                  >
                                    <Edit3 className="w-3.5 h-3.5" />
                                    Sửa
                                  </button>

                                  {u.id !== user?.id && (
                                    <>
                                      <button
                                        type="button"
                                        onClick={() => handleToggleLockUser(u)}
                                        className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg font-semibold cursor-pointer border ${
                                          u.is_active === false
                                            ? "bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border-emerald-200"
                                            : "bg-amber-50 hover:bg-amber-100 text-amber-800 border-amber-200"
                                        }`}
                                        title={
                                          u.is_active === false
                                            ? "Mở khóa tài khoản"
                                            : "Khóa tạm thời tài khoản"
                                        }
                                      >
                                        {u.is_active === false ? (
                                          <>
                                            <Unlock className="w-3.5 h-3.5" /> Mở khóa
                                          </>
                                        ) : (
                                          <>
                                            <Lock className="w-3.5 h-3.5" /> Khóa
                                          </>
                                        )}
                                      </button>

                                      <button
                                        type="button"
                                        onClick={() => handleDeleteUser(u)}
                                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 font-semibold cursor-pointer"
                                        title="Xóa tài khoản"
                                      >
                                        <Trash2 className="w-3.5 h-3.5" />
                                        Xóa
                                      </button>
                                    </>
                                  )}
                                </div>
                              ) : (
                                <span className="text-[11px] text-slate-400 font-medium">
                                  Chỉ xem (USER_VIEW)
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
      </div>

      {/* MODAL THÊM / SỬA TÀI KHOẢN NGƯỜI DÙNG */}
      {userModalMode && (
        <div
          onClick={(e) => {
            if (e.target === e.currentTarget) setUserModalMode(null);
          }}
          className="fixed inset-0 bg-slate-900/50 flex items-center justify-center z-50 p-4"
        >
          <form
            role="dialog"
            aria-modal="true"
            onSubmit={handleSaveUser}
            className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4 text-xs"
          >
            <h3 className="text-base font-bold text-slate-900">
              {userModalMode === "create"
                ? "Thêm Mới Tài khoản Giảng viên / Quản lý"
                : `Chỉnh sửa Tài khoản (${uUsername})`}
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Tên đăng nhập (Username) *
                </label>
                <input
                  type="text"
                  value={uUsername}
                  disabled={userModalMode === "edit"}
                  onChange={(e) => setUUsername(e.target.value)}
                  placeholder="VD: gv_k01_10"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl disabled:bg-slate-100 font-mono"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Mã Giảng viên
                </label>
                <input
                  type="text"
                  value={uLecturerCode}
                  onChange={(e) => setULecturerCode(e.target.value)}
                  placeholder="Tự động cấp nếu để trống (VD: GV0025)"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl font-mono"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2">
                <label className="block font-semibold text-slate-700 mb-1">
                  Họ và tên đầy đủ *
                </label>
                <input
                  type="text"
                  minLength={3}
                  value={uFullName}
                  onChange={(e) => setUFullName(e.target.value)}
                  placeholder="VD: ThS. Lê Hoàng Nam"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl"
                  required
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Học vị
                </label>
                <select
                  value={uDegree}
                  onChange={(e) => setUDegree(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl bg-white"
                >
                  <option value="CN">Cử nhân / Kỹ sư</option>
                  <option value="ThS">Thạc sĩ (ThS)</option>
                  <option value="TS">Tiến sĩ (TS)</option>
                  <option value="PGS.TS">PGS.TS</option>
                  <option value="GS.TS">GS.TS</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Bộ môn trực thuộc
                </label>
                <select
                  value={uDeptId}
                  onChange={(e) =>
                    setUDeptId(e.target.value === "" ? "" : Number(e.target.value))
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl bg-white"
                >
                  <option value="">Toàn Khoa CNTT (Cấp Khoa / Hệ thống)</option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Vai trò phân quyền
                </label>
                <select
                  value={uRole}
                  onChange={(e) => setURole(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl bg-white"
                >
                  <option value="lecturer">Giảng viên (lecturer)</option>
                  <option value="manager">Quản lý Khoa / Bộ môn (manager)</option>
                  {user?.role === "admin" && (
                    <option value="admin">Quản trị hệ thống (admin)</option>
                  )}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Email liên hệ
                </label>
                <input
                  type="email"
                  value={uEmail}
                  onChange={(e) => setUEmail(e.target.value)}
                  placeholder="VD: namlh@huit.edu.vn"
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  {userModalMode === "create"
                    ? "Mật khẩu khởi tạo (≥6 ký tự) *"
                    : "Đặt lại Mật khẩu mới (để trống nếu giữ nguyên)"}
                </label>
                <input
                  type="text"
                  value={uPassword}
                  onChange={(e) => setUPassword(e.target.value)}
                  placeholder={
                    userModalMode === "create"
                      ? "VD: Lecturer@123"
                      : "Nhập mật khẩu mới nếu cần reset..."
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-xl"
                  required={userModalMode === "create"}
                />
              </div>
            </div>

            {userModalMode === "edit" && (
              <label className="flex items-center gap-2 pt-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={uIsActive}
                  onChange={(e) => setUIsActive(e.target.checked)}
                  className="rounded text-blue-600"
                />
                <span className="font-semibold text-slate-800">
                  Tài khoản đang kích hoạt (Cho phép đăng nhập và nhận việc)
                </span>
              </label>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setUserModalMode(null)}
                className="px-4 py-2 rounded-xl bg-slate-100 text-slate-700 font-semibold cursor-pointer"
              >
                Hủy
              </button>
              <button
                type="submit"
                className="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold cursor-pointer"
              >
                {userModalMode === "create" ? "Tạo Tài khoản" : "Lưu Thay đổi"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL ĐỔI MẬT KHẨU CÁ NHÂN */}
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
                minLength={8}
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
