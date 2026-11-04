import {
  MOCK_USERS,
  MOCK_DEPARTMENTS,
  MOCK_TASK_TYPES,
  MOCK_SCHOOL_CATALOG,
  MOCK_STATS,
  MOCK_ML_ACCURACY,
  MOCK_NOTIFICATIONS,
  MOCK_TASKS,
  MOCK_EXTENSIONS,
  MOCK_LECTURER_EVALUATION,
  MOCK_PLANS,
} from "./mockData";

export function installMockApi() {
  const originalFetch = window.fetch;

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;

    // Chỉ chặn các yêu cầu gọi tới Backend API khi Backend hoàn toàn không chạy
    if (url.includes("/api/")) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);
        const res = await originalFetch(input, {
          ...init,
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        return res;
      } catch {
        // Nếu Backend chưa bật -> Tự động chuyển sang Mock API
        return handleMockResponse(url, init);
      }
    }

    return originalFetch(input, init);
  };
}

function jsonResponse(data: any, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function handleMockResponse(url: string, init?: RequestInit): Response {
  const method = (init?.method || "GET").toUpperCase();

  // 1. Auth: Đăng nhập
  if (url.includes("/api/auth/login") && method === "POST") {
    let body: any = {};
    try {
      body = JSON.parse(init?.body as string || "{}");
    } catch {
      body = {};
    }
    const username = (body.username || "truongkhoa").toLowerCase();
    const matchedUser = MOCK_USERS.find((u) => u.username.toLowerCase() === username) || {
      id: 99,
      username,
      full_name: username === "truongkhoa" ? "TS. Nguyễn Văn Lễ" : "Người dùng Demo",
      role: username.includes("gv") ? "lecturer" : username.includes("admin") ? "admin" : "manager",
      department_id: 1,
      department_name: "Bộ môn Công nghệ Phần mềm",
      lecturer_code: "GV0099",
    };

    return jsonResponse({
      access_token: `mock-demo-token-${username}`,
      token_type: "bearer",
      user: matchedUser,
    });
  }

  // 1b. Auth: Danh bạ tài khoản
  if (url.includes("/api/auth/accounts-directory")) {
    return jsonResponse(MOCK_USERS);
  }

  // 2. Auth: Thông tin người dùng hiện tại
  if (url.includes("/api/auth/me")) {
    const savedToken = localStorage.getItem("token") || "";
    let matched = MOCK_USERS[0];
    if (savedToken.includes("gv")) matched = MOCK_USERS[1];
    else if (savedToken.includes("tbm")) matched = MOCK_USERS[2];
    else if (savedToken.includes("admin")) matched = MOCK_USERS[4];

    return jsonResponse(matched);
  }

  // 3. Báo cáo thống kê Dashboard
  if (url.includes("/api/reports/statistics")) {
    return jsonResponse(MOCK_STATS);
  }

  // 4. Độ chính xác mô hình Machine Learning
  if (url.includes("/api/reports/ml-accuracy")) {
    return jsonResponse(MOCK_ML_ACCURACY);
  }

  // 5. Danh mục cấp Trường
  if (url.includes("/api/reports/school-catalog")) {
    return jsonResponse(MOCK_SCHOOL_CATALOG);
  }

  // 6. Kế hoạch năm
  if (url.includes("/api/reports/plans")) {
    if (url.includes("/template") || url.includes("/export")) {
      return new Response(new Blob(["Demo Excel File"]), {
        status: 200,
        headers: { "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
      });
    }
    if (url.includes("/preview")) {
      return jsonResponse({ rows: MOCK_PLANS });
    }
    if (url.includes("/import")) {
      return jsonResponse({ message: "Import kế hoạch thành công 2 dòng (Demo Mode)" });
    }
    return jsonResponse(MOCK_PLANS);
  }

  // 7. Hồ sơ đánh giá 1 năm của giảng viên
  if (url.includes("/api/reports/lecturer-evaluation")) {
    return jsonResponse(MOCK_LECTURER_EVALUATION);
  }

  // 8. Xuất báo cáo Excel & Danh sách trễ hạn & Huấn luyện trực tuyến
  if (url.includes("/api/reports/export-excel") || url.includes("/api/reports/export-late-excel")) {
    return new Response(new Blob(["Demo Excel Export"]), {
      status: 200,
      headers: { "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
    });
  }

  if (url.includes("/api/reports/ml-retrain")) {
    return jsonResponse({
      message: "Đã huấn luyện trực tiếp mô hình từ dữ liệu công việc thực tế thành công!",
      train_result: {
        version: "Online-v1 (Demo)",
        live_samples: 31,
        acc_before: 80.6,
        acc_after: 96.8,
        duration_seconds: 1.2,
      },
      refreshed_open_tasks: 18,
    });
  }

  // 9. Bộ môn & Loại công việc & Thông báo
  if (url.includes("/api/common/departments")) return jsonResponse(MOCK_DEPARTMENTS);
  if (url.includes("/api/common/task-types")) return jsonResponse(MOCK_TASK_TYPES);
  if (url.includes("/api/common/notifications")) return jsonResponse(MOCK_NOTIFICATIONS);

  // 10. Danh sách người dùng
  if (url.includes("/api/users")) {
    if (method === "POST") {
      return jsonResponse({ message: "Tạo tài khoản người dùng thành công (Demo Mode)" });
    }
    return jsonResponse(MOCK_USERS);
  }

  // 11. Gợi ý phân công bằng Machine Learning
  if (url.includes("/api/tasks/preview-risk")) {
    return jsonResponse({
      candidates: [
        {
          lecturer_id: 2,
          lecturer_name: "ThS. Nguyễn Minh Khoa",
          department_name: "Bộ môn Công nghệ Phần mềm",
          current_open_tasks: 2,
          teaching_hours: 220,
          risk_level: "Thấp",
          probability: 0.16,
          top_factors: [
            { feature: "hist_late_rate_smooth", direction: "decrease", delta_logit: -0.45 },
            { feature: "lead_vs_expected_ratio", direction: "decrease", delta_logit: -0.38 },
          ],
          recommendation: "Giảng viên có tỷ lệ hoàn thành đúng hạn 94.4%, thời gian biểu còn trống phù hợp nhận thêm việc.",
        },
        {
          lecturer_id: 4,
          lecturer_name: "TS. Trần Thị Mai",
          department_name: "Bộ môn Hệ thống Thông tin",
          current_open_tasks: 3,
          teaching_hours: 240,
          risk_level: "Trung bình",
          probability: 0.29,
          top_factors: [
            { feature: "current_open_tasks", direction: "increase", delta_logit: 0.32 },
          ],
          recommendation: "Có thể phân công nhưng cần lưu ý mốc tiến độ giữa kỳ.",
        },
        {
          lecturer_id: 3,
          lecturer_name: "PGS.TS. Hoàng Văn Minh",
          department_name: "Bộ môn Công nghệ Phần mềm",
          current_open_tasks: 4,
          teaching_hours: 310,
          risk_level: "Cao",
          probability: 0.48,
          top_factors: [
            { feature: "workload_vs_teaching_Load", direction: "increase", delta_logit: 0.54 },
          ],
          recommendation: "Đang có tải giờ giảng dạy cao và chủ nhiệm 2 đề tài. Không khuyến nghị giao thêm việc gấp.",
        },
      ],
    });
  }

  // 12. Danh sách gia hạn
  if (url.includes("/api/tasks/extensions")) {
    return jsonResponse(MOCK_EXTENSIONS);
  }

  // 13. Chi tiết công việc & thao tác công việc
  if (url.includes("/detail")) {
    return jsonResponse({
      task: MOCK_TASKS[0],
      progress_logs: [
        { progress_pct: 30, note: "Khởi tạo khung đề cương", created_at: "2026-10-05 09:00" },
        { progress_pct: 65, note: "Hoàn thiện 5 chương đầu", created_at: "2026-10-20 15:30" },
      ],
    });
  }

  if (url.includes("/api/tasks")) {
    if (method === "POST") {
      return jsonResponse({
        success: true,
        message: "Giao việc và phân công thành công (Demo Mode)",
        task: MOCK_TASKS[0],
      });
    }
    return jsonResponse(MOCK_TASKS);
  }

  return jsonResponse({ success: true, message: "OK (Demo Mode)" });
}

