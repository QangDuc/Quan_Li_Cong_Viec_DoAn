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

    // Chỉ chuyển sang Mock API khi Backend hoàn toàn không chạy
    if (url.includes("/api/")) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 90000);
        const res = await originalFetch(input, {
          ...init,
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        return res;
      } catch {
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
      body = JSON.parse((init?.body as string) || "{}");
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

  // 2. Auth: Thông tin người dùng hiện tại
  if (url.includes("/api/auth/me")) {
    const savedToken = localStorage.getItem("token") || "";
    let matched = MOCK_USERS[0];
    if (savedToken.includes("gv")) matched = MOCK_USERS[1];
    else if (savedToken.includes("tbm")) matched = MOCK_USERS[2];
    else if (savedToken.includes("admin")) matched = MOCK_USERS[4];
    return jsonResponse(matched);
  }

  // 3. AI Assistant: Cấu hình & Chat
  if (url.includes("/api/ai/config")) {
    if (method === "PUT") {
      return jsonResponse({
        message: "Đã lưu cấu hình AI an toàn vào backend/.env.local (Demo Mode)",
        provider: "auto",
      });
    }
    return jsonResponse({
      provider: "auto",
      gemini_configured: false,
      gemini_key_masked: "Chưa cấu hình (Đang dùng AI Nội bộ miễn phí)",
      gemini_model: "gemini-2.5-flash",
      groq_configured: false,
      groq_key_masked: "Chưa cấu hình",
      groq_model: "llama-3.3-70b-versatile",
      env_file_note: "API Key lưu riêng tại backend/.env.local (Đã cấu hình .gitignore)",
      free_key_guides: [
        {
          name: "Google Gemini API (Khuyên dùng - Miễn phí)",
          url: "https://aistudio.google.com/app/apikey",
          steps: "Đăng nhập Gmail -> Nhấn 'Create API Key' -> Copy chuỗi AIzaSy... dán vào ô bên dưới.",
        },
        {
          name: "Groq Cloud Llama 3.3 70B (Miễn phí, tốc độ siêu nhanh)",
          url: "https://console.groq.com/keys",
          steps: "Đăng nhập Groq -> Nhấn 'Create API Key' -> Copy chuỗi gsk_... dán vào ô bên dưới.",
        },
      ],
    });
  }

  if (url.includes("/api/ai/chat")) {
    return jsonResponse({
      reply:
        "⚠️ Không kết nối được Backend (http://localhost:8000) nên đây chỉ là câu trả lời mẫu (Demo). Hãy chạy backend và tải lại trang để dùng Trợ lý AI thật.",
      engine: "Chế độ Demo — Backend offline",
      used_external_api: false,
    });
  }

  // 4. Báo cáo thống kê & Độ chính xác ML
  if (url.includes("/api/reports/statistics")) return jsonResponse(MOCK_STATS);
  if (url.includes("/api/reports/ml-accuracy")) return jsonResponse(MOCK_ML_ACCURACY);
  if (url.includes("/api/reports/school-catalog")) return jsonResponse(MOCK_SCHOOL_CATALOG);
  if (url.includes("/api/reports/lecturer-evaluation")) return jsonResponse(MOCK_LECTURER_EVALUATION);

  // 5. Kế hoạch năm & Xuất Excel
  if (url.includes("/api/reports/plans")) {
    if (url.includes("/template") || url.includes("/export")) {
      return new Response(new Blob(["Demo Excel File"]), {
        status: 200,
        headers: { "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
      });
    }
    if (url.includes("/preview")) return jsonResponse({ rows: MOCK_PLANS });
    if (url.includes("/import")) return jsonResponse({ message: "Import kế hoạch thành công (Demo Mode)" });
    return jsonResponse(MOCK_PLANS);
  }

  if (url.includes("/api/reports/export-excel") || url.includes("/api/reports/export-late-excel")) {
    return new Response(new Blob(["Demo Excel Export"]), {
      status: 200,
      headers: { "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" },
    });
  }

  if (url.includes("/api/reports/ml-retrain")) {
    return jsonResponse({
      message:
        "Đã kiểm định rào chắn chất lượng & cập nhật ngữ cảnh TabPFN v2 trên tập Holdout độc lập!",
      train_result: {
        version: "TabPFN v2 (9.2.0 • 4 túi ngữ cảnh, v0002)",
        live_samples: 32,
        acc_before: 88.2,
        acc_after: 89.9,
        brier_before: 0.1266,
        brier_after: 0.1194,
        duration_seconds: 2.8,
      },
      refreshed_open_tasks: 18,
    });
  }

  // 6. Danh mục dùng chung
  if (url.includes("/api/common/departments")) return jsonResponse(MOCK_DEPARTMENTS);
  if (url.includes("/api/common/task-types")) return jsonResponse(MOCK_TASK_TYPES);
  if (url.includes("/api/common/notifications")) return jsonResponse(MOCK_NOTIFICATIONS);

  // 7. Quản trị người dùng (CRUD)
  if (url.includes("/api/users")) {
    if (method === "POST") return jsonResponse({ message: "Đã thêm tài khoản thành công (Demo Mode)" });
    if (method === "PUT") return jsonResponse({ message: "Đã cập nhật tài khoản thành công (Demo Mode)" });
    if (method === "DELETE") return jsonResponse({ message: "Đã xóa/khóa tài khoản thành công (Demo Mode)" });
    return jsonResponse(MOCK_USERS);
  }

  // 8. Gợi ý phân công bằng Machine Learning (Theo nhóm việc + Độ trễ thấp nhất + Gợi ý Phụ trách chính)
  if (url.includes("/api/tasks/preview-risk")) {
    const candidates = [
      {
        rank: 1,
        lecturer_id: 2,
        lecturer_code: "GV0001",
        full_name: "ThS. Nguyễn Minh Khoa",
        degree: "ThS",
        department_name: "Bộ môn Công nghệ Phần mềm",
        task_group_match: "Giảng dạy",
        group_done_count: 14,
        group_on_time_rate: 94.4,
        current_open_tasks: 2,
        current_overdue_tasks: 0,
        hist_completed_count: 18,
        hist_late_rate: 5.6,
        probability: 0.142,
        level: "Thấp",
        is_lowest_delay_group: true,
        lead_score: 91.5,
        is_recommended_lead: true,
        lead_conditions: [
          {
            criterion: "1. Nguy cơ trễ hạn dự báo thấp nhất (ML Risk)",
            passed: true,
            detail: "Xác suất trễ dự báo 14.2% (Mức Thấp)",
          },
          {
            criterion: "2. Kinh nghiệm thực hiện trong Nhóm công việc được chọn",
            passed: true,
            detail: "Đã hoàn thành 14 việc nhóm này (Đúng hạn 94.4%)",
          },
          {
            criterion: "3. Tải công việc hiện tại không quá tải & Không có việc quá hạn",
            passed: true,
            detail: "Đang mở 2 việc, Quá hạn: 0 việc",
          },
          {
            criterion: "4. Học vị chuyên môn & Kỷ luật hoàn thành lịch sử",
            passed: true,
            detail: "Học vị ThS • Tỷ lệ đúng hạn toàn kỳ 94.4%",
          },
        ],
        top_factors: [
          { feature: "hist_late_rate_smooth", direction: "Giảm nguy cơ", delta_logit: -0.45 },
          { feature: "lead_vs_expected_ratio", direction: "Giảm nguy cơ", delta_logit: -0.38 },
        ],
        recommendation:
          "Độ trễ dự báo thấp nhất (14.2%) trong nhóm công việc • Đề xuất làm Người phụ trách chính.",
      },
      {
        rank: 2,
        lecturer_id: 4,
        lecturer_code: "GV0002",
        full_name: "TS. Trần Thị Mai",
        degree: "TS",
        department_name: "Bộ môn Hệ thống Thông tin",
        task_group_match: "Giảng dạy",
        group_done_count: 11,
        group_on_time_rate: 90.0,
        current_open_tasks: 2,
        current_overdue_tasks: 0,
        hist_completed_count: 15,
        hist_late_rate: 10.0,
        probability: 0.185,
        level: "Thấp",
        is_lowest_delay_group: true,
        lead_score: 88.2,
        is_recommended_lead: false,
        lead_conditions: [
          {
            criterion: "1. Nguy cơ trễ hạn dự báo thấp nhất (ML Risk)",
            passed: true,
            detail: "Xác suất trễ dự báo 18.5% (Mức Thấp)",
          },
          {
            criterion: "2. Kinh nghiệm thực hiện trong Nhóm công việc được chọn",
            passed: true,
            detail: "Đã hoàn thành 11 việc nhóm này (Đúng hạn 90.0%)",
          },
          {
            criterion: "3. Tải công việc hiện tại không quá tải & Không có việc quá hạn",
            passed: true,
            detail: "Đang mở 2 việc, Quá hạn: 0 việc",
          },
          {
            criterion: "4. Học vị chuyên môn & Kỷ luật hoàn thành lịch sử",
            passed: true,
            detail: "Học vị TS • Tỷ lệ đúng hạn toàn kỳ 90.0%",
          },
        ],
        top_factors: [
          { feature: "lecturer_specialty_match", direction: "Giảm nguy cơ", delta_logit: -0.31 },
        ],
        recommendation: "Độ trễ dự báo thấp (18.5%), phù hợp giao việc hoặc phối hợp nhóm.",
      },
    ];
    return jsonResponse({
      selected_task_group: "Giảng dạy",
      total_evaluated_in_group: 2,
      filter_note:
        "Chỉ lọc các giảng viên thuộc nhóm công việc [Giảng dạy] và xếp hạng theo độ trễ dự báo thấp nhất.",
      recommended_lead: {
        lecturer_id: 2,
        lecturer_code: "GV0001",
        full_name: "ThS. Nguyễn Minh Khoa",
        degree: "ThS",
        department_name: "Bộ môn Công nghệ Phần mềm",
        probability: 0.142,
        lead_score: 91.5,
        conditions: candidates[0].lead_conditions,
        reason_summary:
          "Đạt điểm tiêu chí Phụ trách chính cao nhất (91.5/100): nguy cơ trễ thấp nhất (14.2%), đã hoàn thành 14 việc thuộc nhóm Giảng dạy và không có việc quá hạn.",
      },
      candidates,
    });
  }

  // 9. Thao tác công việc nhóm, nộp minh chứng thành viên, báo thiếu sót
  if (url.includes("/member-evidence")) {
    return jsonResponse({
      message: "Đã gửi minh chứng thành viên lên Trưởng nhóm (Người phụ trách chính) chờ kiểm duyệt.",
    });
  }
  if (url.includes("/feedback")) {
    return jsonResponse({
      message: "Đã gửi thông báo nhắc nhở thiếu sót và cập nhật trạng thái cho thành viên nhóm.",
    });
  }
  if (url.includes("/delegate")) {
    return jsonResponse({
      message: "Đã lưu phân công nhiệm vụ cho các thành viên trong nhóm.",
    });
  }
  if (url.includes("/api/tasks/extensions")) return jsonResponse(MOCK_EXTENSIONS);
  if (url.includes("/detail")) {
    return jsonResponse({
      ...MOCK_TASKS[0],
      progress_logs: [
        {
          id: 1,
          lecturer_name: "ThS. Nguyễn Minh Khoa",
          progress_pct: 65,
          note: "Đã hoàn thành rà soát chuẩn đầu ra và gửi Trưởng nhóm",
          evidence_file_name: "MinhChung_CDR_CNPM.pdf",
          evidence_file_url: "/uploads/evidence/demo.pdf",
          created_at: "2026-10-20 15:30",
        },
      ],
    });
  }
  if (url.includes("/api/tasks")) {
    if (method === "POST") {
      return jsonResponse({
        id: 999,
        code: "CV-2611-NEW",
        reviewer_name: "TS. Nguyễn Văn Lễ",
        message: "Giao việc thành công (Demo Mode)",
      });
    }
    return jsonResponse(MOCK_TASKS);
  }

  return jsonResponse({ success: true, message: "OK (Demo Mode)" });
}
