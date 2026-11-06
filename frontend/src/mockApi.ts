import ExcelJS from "exceljs";
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
import { calculateProjectProgressFromMembers } from "./rbacWorkflow";

export function installMockApi() {
  const originalFetch = window.fetch;

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;

    // Xử lý trực tiếp các endpoint /api/ bằng dữ liệu nội bộ để không phát sinh lỗi kết nối khi chạy trên môi trường Web
    if (url.includes("/api/")) {
      return await handleMockResponse(url, init);
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

function parseBody(init?: RequestInit): any {
  try {
    return JSON.parse((init?.body as string) || "{}");
  } catch {
    return {};
  }
}

const THIN_BORDER: Partial<ExcelJS.Borders> = {
  top: { style: "thin", color: { argb: "FFCBD5E1" } },
  left: { style: "thin", color: { argb: "FFCBD5E1" } },
  bottom: { style: "thin", color: { argb: "FFCBD5E1" } },
  right: { style: "thin", color: { argb: "FFCBD5E1" } },
};

function styleWorksheet(
  ws: ExcelJS.Worksheet,
  titleLine1: string,
  titleLine2: string,
  subtitleLine3: string,
  headers: string[],
  headerColorHex: string = "1E3A8A"
) {
  const numCols = headers.length;

  // Row 1: Tiêu đề cơ sở
  ws.mergeCells(1, 1, 1, numCols);
  const cell1 = ws.getCell(1, 1);
  cell1.value = titleLine1;
  cell1.font = { name: "Arial", size: 11, bold: true, color: { argb: "FF1E293B" } };
  cell1.alignment = { horizontal: "center", vertical: "middle" };

  // Row 2: Tiêu đề báo cáo chính
  ws.mergeCells(2, 1, 2, numCols);
  const cell2 = ws.getCell(2, 1);
  cell2.value = titleLine2;
  cell2.font = { name: "Arial", size: 14, bold: true, color: { argb: `FF${headerColorHex}` } };
  cell2.alignment = { horizontal: "center", vertical: "middle" };
  ws.getRow(2).height = 24;

  // Row 3: Phụ đề & metadata
  ws.mergeCells(3, 1, 3, numCols);
  const cell3 = ws.getCell(3, 1);
  cell3.value = subtitleLine3;
  cell3.font = { name: "Arial", size: 10, italic: true, color: { argb: "FF475569" } };
  cell3.alignment = { horizontal: "center", vertical: "middle" };

  // Row 4: Trống
  ws.getRow(4).values = [];

  // Row 5: Headers
  const headerRow = ws.getRow(5);
  headerRow.values = headers;
  headerRow.height = 26;

  for (let c = 1; c <= numCols; c++) {
    const cell = headerRow.getCell(c);
    cell.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: `FF${headerColorHex}` },
    };
    cell.font = { name: "Arial", size: 10, bold: true, color: { argb: "FFFFFFFF" } };
    cell.alignment = { horizontal: "center", vertical: "middle", wrapText: true };
    cell.border = THIN_BORDER;
  }
}

function autofitColumns(ws: ExcelJS.Worksheet, startRow = 6) {
  const colCount = ws.columnCount;
  for (let c = 1; c <= colCount; c++) {
    let maxLen = 10;
    ws.eachRow({ includeEmpty: false }, (row, rowNumber) => {
      if (rowNumber <= 3) return; // Không đo các dòng tiêu đề đã merge
      const cell = row.getCell(c);
      if (rowNumber >= startRow) {
        cell.font = { name: "Arial", size: 10 };
        cell.border = THIN_BORDER;
        cell.alignment = { vertical: "middle", wrapText: false };
      }
      const val = cell.value != null ? String(cell.value) : "";
      if (val.length > maxLen) {
        maxLen = val.length;
      }
    });
    ws.getColumn(c).width = Math.min(maxLen + 4, 48);
  }
}

async function createExcelJsResponse(wb: ExcelJS.Workbook): Promise<Response> {
  const buf = await wb.xlsx.writeBuffer();
  return new Response(new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), {
    status: 200,
    headers: {
      "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
  });
}

async function generateMockPlanTemplateExcel(): Promise<Response> {
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet("KeHoach_CongTac");
  const headers = [
    "STT", "Mã Nhiệm vụ", "Tên Công việc / Nhiệm vụ", "Loại Công việc", "Nhóm việc",
    "Quy mô", "Độ phức tạp", "Mức ưu tiên", "Học kỳ", "Ngày bắt đầu",
    "Hạn hoàn thành", "Giờ chuẩn quy đổi dự kiến", "Sản phẩm / Minh chứng bàn giao", "Ghi chú"
  ];
  styleWorksheet(
    ws,
    "TRƯỜNG ĐẠI HỌC CÔNG THƯƠNG TP.HCM (HUIT) — KHOA CÔNG NGHỆ THÔNG TIN",
    "BIỂU MẪU KẾ HOẠCH CÔNG TÁC & NHIỆM VỤ CHUYÊN MÔN NĂM HỌC (2026-2027)",
    "Đồng bộ chuẩn 14 cột phục vụ quản lý và đối soát tiến độ toàn hệ thống",
    headers,
    "0F766E"
  );
  ws.addRow([
    1, "KH-001", "Biên soạn Đề cương chi tiết Trí tuệ nhân tạo", "Biên soạn Giáo trình & Đề cương chi tiết học phần",
    "Đào tạo & Học vụ", "quy mô chuẩn", "Trung bình", "Cao", "HK1", "2026-09-01", "2026-11-30", 30,
    "Hồ sơ Đề cương chi tiết chuẩn AUN-QA", "Mẫu kế hoạch đầu năm"
  ]);
  ws.addRow([
    2, "KH-002", "Chấm bài thi & nộp điểm kết thúc học phần", "Coi thi, Chấm thi & Nộp bảng điểm kết thúc học phần",
    "Đào tạo & Học vụ", "quy mô nhỏ", "Trung bình", "Trung bình", "HK1", "2026-12-01", "2026-12-15", 15,
    "Bảng điểm gốc có chữ ký & túi bài thi", "Theo lịch thi của Phòng Đào tạo"
  ]);
  autofitColumns(ws, 6);
  return await createExcelJsResponse(wb);
}

async function generateMockTasksExcel(academicYear = "2026-2027", semester = ""): Promise<Response> {
  const wb = new ExcelJS.Workbook();
  const ws1 = wb.addWorksheet("BaoCao_CongViec");

  // Sheet 1: BaoCao_CongViec (28 cột chuẩn dữ liệu toàn hệ thống)
  const headers = [
    "STT", "Mã Công việc", "Tên Công việc", "Loại Công việc", "Nhóm việc", "Quy mô", "Mức ưu tiên", "Độ phức tạp",
    "Danh mục Trường", "Họ và tên Giảng viên", "Mã GV", "Học vị / Chức danh", "Bộ môn", "Vai trò",
    "Nhiệm vụ thành viên", "Người kiểm tra tiến độ", "Học kỳ", "Ngày giao", "Hạn chót gốc", "Hạn hiện tại",
    "Tiến độ (%)", "Trạng thái", "Đánh giá hạn", "Độ lệch (ngày)", "Dự báo Rủi ro ML",
    "Giờ chuẩn quy đổi", "Trạng thái Minh chứng", "File Minh chứng"
  ];

  const semLabel = semester || "Cả năm học";
  styleWorksheet(
    ws1,
    "TRƯỜNG ĐẠI HỌC CÔNG THƯƠNG TP.HCM (HUIT) — KHOA CÔNG NGHỆ THÔNG TIN",
    `BÁO CÁO TỔNG HỢP PHÂN CÔNG, TIẾN ĐỘ & QUY ĐỔI GIỜ CHUẨN (${academicYear} - ${semLabel})`,
    `Ngày trích xuất: ${new Date().toLocaleDateString("vi-VN")} | Tổng số bản ghi phân công: ${MOCK_TASKS.length}`,
    headers,
    "1E3A8A"
  );

  let stt = 1;
  for (const t of MOCK_TASKS) {
    const assignees = t.assignees && t.assignees.length > 0 ? t.assignees : [
      {
        lecturer_name: t.lead_lecturer_name || "ThS. Nguyễn Minh Khoa",
        lecturer_code: "GV0101",
        is_lead: true,
        member_task_note: "Thực hiện theo mô tả chung",
        latest_evidence_name: "Chưa nộp",
        member_evidence_status: "Chưa nộp",
        progress_pct: t.progress_pct || 0,
        status: t.status || "Đang thực hiện",
        is_late: t.is_late || false,
        delay_days: t.delay_days || 0,
      }
    ];

    for (const a of assignees) {
      const mlStr = t.ml_prediction ? `${t.ml_prediction.level} (${Math.round((t.ml_prediction.probability || 0) * 100)}%)` : "Chưa dự báo";
      const lateStr = a.is_late || t.is_late ? "Hoàn thành trễ hạn" : (t.status === "Hoàn thành" ? "Đúng hạn" : "Trong hạn");
      const roleStr = a.is_lead ? "Phụ trách chính (Trưởng nhóm)" : (t.assignment_mode === "Group" ? "Thành viên nhóm" : "Cá nhân");
      
      ws1.addRow([
        stt++,
        t.code,
        t.title,
        t.task_type_name || "",
        t.task_group || "Đào tạo & Học vụ",
        t.scale || "quy mô chuẩn",
        t.priority || "Trung bình",
        t.complexity || "Trung bình",
        t.school_catalog_code || "Cấp Khoa/Bộ môn",
        a.lecturer_name || t.lead_lecturer_name || "",
        a.lecturer_code || "GV0101",
        "Thạc sĩ / Giảng viên",
        t.department_name || "Bộ môn Công nghệ phần mềm (K01)",
        roleStr,
        a.member_task_note || "Thực hiện theo phân công",
        t.reviewer_name || "TS. Nguyễn Văn Lễ (Trưởng Khoa CNTT)",
        t.semester || "HK1",
        t.assigned_at || "2026-10-01",
        t.original_deadline || "2026-11-15",
        t.current_deadline || "2026-11-15",
        a.progress_pct ?? t.progress_pct ?? 0,
        a.status || t.status || "Đang thực hiện",
        lateStr,
        a.delay_days || t.delay_days || 0,
        mlStr,
        t.conversion_hours || 30.0,
        a.member_evidence_status || (a.latest_evidence_name ? "Đã nộp" : "Chưa nộp"),
        a.latest_evidence_name || "Chưa nộp"
      ]);
    }
  }
  autofitColumns(ws1, 6);

  // Sheet 2: TongHop_GioChuan_GV
  const ws2 = wb.addWorksheet("TongHop_GioChuan_GV");
  const headers2 = [
    "STT", "Mã Giảng viên", "Họ và tên Giảng viên", "Học vị / Chức danh", "Bộ môn",
    "Tổng đầu việc", "Số lần làm Trưởng nhóm", "Hoàn thành Đúng hạn", "Hoàn thành Trễ hạn",
    "Tỷ lệ Đúng hạn (%)", "Giờ giảng dạy năm (Định mức 270h)", "Giờ chuẩn công tác quy đổi",
    "Tổng giờ chuẩn tích lũy", "Xếp loại hoàn thành"
  ];

  styleWorksheet(
    ws2,
    "TRƯỜNG ĐẠI HỌC CÔNG THƯƠNG TP.HCM (HUIT) — KHOA CÔNG NGHỆ THÔNG TIN",
    `BẢNG TỔNG HỢP KHỐI LƯỢNG GIỜ CHUẨN & ĐÁNH GIÁ GIẢNG VIÊN (${academicYear} - ${semLabel})`,
    "Áp dụng theo khung Thông tư 20/2020/TT-BGDĐT của Bộ GD&ĐT và Quy chế chi tiêu nội bộ",
    headers2,
    "0F766E"
  );

  const lecturers = MOCK_USERS.filter((u: any) => u.role === "lecturer" || u.role === "manager");
  let stt2 = 1;
  for (const lec of lecturers) {
    const totalTasks = MOCK_TASKS.filter((t: any) => 
      t.lead_lecturer_id === lec.id || (t.assignees && t.assignees.some((a: any) => a.lecturer_id === lec.id))
    ).length;
    const leadCount = MOCK_TASKS.filter((t: any) => t.lead_lecturer_id === lec.id).length;
    const completedTasks = MOCK_TASKS.filter((t: any) => 
      t.status === "Hoàn thành" && (t.lead_lecturer_id === lec.id || (t.assignees && t.assignees.some((a: any) => a.lecturer_id === lec.id)))
    ).length;
    const lateTasks = MOCK_TASKS.filter((t: any) => 
      t.is_late && (t.lead_lecturer_id === lec.id || (t.assignees && t.assignees.some((a: any) => a.lecturer_id === lec.id)))
    ).length;
    const onTimeTasks = Math.max(0, completedTasks - lateTasks);
    const onTimeRate = completedTasks > 0 ? Math.round((onTimeTasks / completedTasks) * 100) : 100;
    const teachingHrs = 270.0;
    const dutyHrs = totalTasks * 25.0;
    const totalHrs = teachingHrs + dutyHrs;
    const rankEval = onTimeRate >= 90 && dutyHrs >= 50 ? "Hoàn thành xuất sắc" : (onTimeRate >= 80 ? "Hoàn thành tốt" : "Cần nhắc nhở tiến độ");

    ws2.addRow([
      stt2++,
      lec.lecturer_code || `GV${String(lec.id).padStart(4, "0")}`,
      lec.full_name,
      `${lec.degree || "Thạc sĩ"} / ${lec.academic_rank || "Giảng viên"}`,
      lec.department_name || "Khoa CNTT",
      totalTasks,
      leadCount,
      onTimeTasks,
      lateTasks,
      onTimeRate,
      teachingHrs,
      dutyHrs,
      totalHrs,
      rankEval
    ]);
  }
  autofitColumns(ws2, 6);

  return await createExcelJsResponse(wb);
}

async function generateMockLateExcel(academicYear = "2026-2027", semester = ""): Promise<Response> {
  const wb = new ExcelJS.Workbook();
  const wsDetail = wb.addWorksheet("DS_ChiTiet_TreHan");

  // Sheet 1: DS_ChiTiet_TreHan (18 CỘT - ĐÃ LOẠI BỎ MINH CHỨNG KẾT QUẢ THEO YÊU CẦU)
  const headersDetail = [
    "STT", "Mã Giảng viên", "Họ và tên Giảng viên", "Bộ môn", "Vai trò trong CV",
    "Mã Công việc", "Tên Công việc", "Loại Công việc", "Mức ưu tiên",
    "Người giao việc", "Người kiểm tra tiến độ",
    "Ngày giao", "Hạn chót gốc", "Hạn chót hiện tại", "Ngày hoàn thành",
    "Tiến độ (%)", "Phân loại trễ hạn", "Số ngày trễ (ngày)"
  ];

  const semLabel = semester || "Cả năm học";
  const lateTasks = MOCK_TASKS.filter((t: any) => t.is_late || t.status === "Quá hạn" || (t.delay_days && t.delay_days > 0));
  const sampleLateTasks = lateTasks.length > 0 ? lateTasks : [
    {
      code: "CV-2611-HK106",
      title: "Xây dựng ngân hàng 300 câu hỏi chuẩn đầu ra học phần Lập trình Web",
      task_type_name: "Phản biện/duyệt đề thi",
      priority: "Cao",
      department_name: "Bộ môn Công nghệ phần mềm (K01)",
      assigned_at: "2026-11-18",
      original_deadline: "2026-11-28",
      current_deadline: "2026-12-02",
      completed_at: "2026-12-05",
      progress_pct: 100,
      status: "Hoàn thành",
      is_late: true,
      delay_days: 3,
      lead_lecturer_name: "ThS. Nguyễn Minh Khoa",
      reviewer_name: "PGS.TS. Hoàng Văn Minh (TBM CNPM)"
    }
  ];

  styleWorksheet(
    wsDetail,
    "TRƯỜNG ĐẠI HỌC CÔNG THƯƠNG TP.HCM (HUIT) — KHOA CÔNG NGHỆ THÔNG TIN",
    `BÁO CÁO DANH SÁCH GIẢNG VIÊN & CÔNG VIỆC TRỄ HẠN / QUÁ HẠN (${academicYear} - ${semLabel})`,
    `Ngày trích xuất: ${new Date().toLocaleDateString("vi-VN")} | Tổng số trường hợp trễ / quá hạn: ${sampleLateTasks.length}`,
    headersDetail,
    "991B1B"
  );

  let stt = 1;
  for (const t of sampleLateTasks) {
    const isCompleted = t.status === "Hoàn thành" || t.progress_pct === 100;
    const lateType = isCompleted ? "Hoàn thành trễ hạn" : "Đang quá hạn (Chưa xong)";
    const compStr = isCompleted ? (t.completed_at || "2026-12-05") : "Chưa hoàn thành";
    wsDetail.addRow([
      stt++,
      "GV0101",
      t.lead_lecturer_name || "ThS. Nguyễn Minh Khoa",
      t.department_name || "Bộ môn Công nghệ phần mềm (K01)",
      "Thực hiện cá nhân",
      t.code,
      t.title,
      t.task_type_name || "Nhiệm vụ chuyên môn",
      t.priority || "Cao",
      "TS. Nguyễn Văn Lễ (Trưởng Khoa CNTT)",
      t.reviewer_name || "PGS.TS. Hoàng Văn Minh (TBM CNPM)",
      t.assigned_at || "2026-11-18",
      t.original_deadline || "2026-11-28",
      t.current_deadline || "2026-12-02",
      compStr,
      t.progress_pct || 100,
      lateType,
      t.delay_days || 3
    ]);
  }
  autofitColumns(wsDetail, 6);

  // Sheet 2: TongHop_GiangVien_TreHan
  const wsSummary = wb.addWorksheet("TongHop_GiangVien_TreHan");
  const headersSummary = [
    "STT", "Mã Giảng viên", "Họ và tên Giảng viên", "Bộ môn", "Email liên hệ",
    "Tổng số việc được giao", "Số việc hoàn thành trễ hạn", "Số việc đang quá hạn chưa xong",
    "Tổng số việc trễ / quá hạn", "Tỷ lệ trễ hạn (%)", "Số ngày trễ trung bình", "Danh sách Mã CV trễ hạn"
  ];

  styleWorksheet(
    wsSummary,
    "TRƯỜNG ĐẠI HỌC CÔNG THƯƠNG TP.HCM (HUIT) — KHOA CÔNG NGHỆ THÔNG TIN",
    `BẢNG TỔNG HỢP THEO GIẢNG VIÊN CÓ CÔNG VIỆC TRỄ HẠN / QUÁ HẠN (${academicYear} - ${semLabel})`,
    "Thống kê tự động phục vụ công tác giám sát tiến độ & bình xét thi đua",
    headersSummary,
    "991B1B"
  );

  wsSummary.addRow([
    1,
    "GV0101",
    "ThS. Nguyễn Minh Khoa",
    "Bộ môn Công nghệ phần mềm (K01)",
    "khoanm@huit.edu.vn",
    9,
    1,
    0,
    1,
    11.1,
    3.0,
    sampleLateTasks.map((t: any) => t.code).join(", ")
  ]);
  autofitColumns(wsSummary, 6);

  return await createExcelJsResponse(wb);
}

export function handleMockResponse(url: string, init?: RequestInit): Response | Promise<Response> {
  const method = (init?.method || "GET").toUpperCase();

  // 1. Auth: Đăng nhập
  if (url.includes("/api/auth/login") && method === "POST") {
    const body = parseBody(init);
    const username = (body.username || "truongkhoa").trim().toLowerCase();
    const matchedUser = MOCK_USERS.find((u) => u.username.toLowerCase() === username) || {
      id: 99,
      username,
      full_name: username === "truongkhoa" ? "TS. Nguyễn Văn Lễ (Trưởng Khoa CNTT)" : "Cán bộ / Giảng viên Khoa CNTT",
      role: username.includes("gv") ? "lecturer" : username.includes("admin") ? "admin" : "manager",
      department_id: 1,
      department_name: "Bộ môn Công nghệ phần mềm (K01)",
      lecturer_code: "GV0099",
      degree: "Thạc sĩ",
      is_active: true,
      is_online: true,
    };

    return jsonResponse({
      access_token: `mock-demo-token-${username}`,
      token_type: "bearer",
      user: matchedUser,
    });
  }

  if (url.includes("/api/auth/change-password") && method === "POST") {
    return jsonResponse({ message: "Đã cập nhật mật khẩu thành công!" });
  }

  // 2. Auth: Thông tin người dùng hiện tại
  if (url.includes("/api/auth/me")) {
    const savedToken =
      typeof localStorage !== "undefined" ? localStorage.getItem("token") || "" : "";
    const tokenUser = savedToken.replace(/^mock-demo-token-/, "").trim().toLowerCase();
    const matched =
      MOCK_USERS.find((u) => u.username.toLowerCase() === tokenUser) ||
      MOCK_USERS.find((u) => u.username === "truongkhoa") ||
      MOCK_USERS[0];
    return jsonResponse(matched);
  }

  // 3. AI Assistant: Cấu hình & Chat thông minh theo ngữ cảnh Khoa CNTT
  if (url.includes("/api/ai/config")) {
    if (method === "PUT") {
      return jsonResponse({
        message: "Đã lưu cấu hình AI an toàn",
        provider: "auto",
      });
    }
    return jsonResponse({
      provider: "auto",
      gemini_configured: true,
      gemini_key_masked: "Đã tích hợp sẵn",
      gemini_model: "gemini-2.5-flash",
      groq_configured: false,
      groq_key_masked: "Chưa cấu hình",
      groq_model: "llama-3.3-70b-versatile",
    });
  }

  if (url.includes("/api/ai/chat")) {
    const body = parseBody(init);
    const msg = String(body.message || "").toLowerCase();
    const openCount = MOCK_TASKS.filter((t) => t.status !== "Hoàn thành").length;
    const groupCount = MOCK_TASKS.filter((t) => t.assignment_mode === "Group" || (t.assignees?.length || 0) >= 2).length;

    let reply =
      `**Tổng hợp tình hình công việc Khoa CNTT (Năm học 2026–2027):**\n` +
      `• Hiện có **${MOCK_TASKS.length} công việc trọng tâm** đang theo dõi (${openCount} việc đang mở, ${groupCount} việc nhóm).\n` +
      `• **Việc nhóm tiêu biểu:** [CV-2610-NHOM01] Xây dựng Hồ sơ Tự đánh giá & Minh chứng Kiểm định AUN-QA ngành CNPM (Trưởng nhóm: **ThS. Nguyễn Minh Khoa**, tiến độ **65%**).\n` +
      `• **Cảnh báo rủi ro cao (≥ 52%):** [CV26-002] Thu thập minh chứng Tiêu chuẩn 4 phục vụ Kiểm định AUN-QA (Xác suất trễ dự báo **52.0%** — khuyến nghị bổ sung giảng viên hỗ trợ).`;

    if (msg.includes("trưởng nhóm") || msg.includes("phụ trách") || msg.includes("gợi ý")) {
      reply =
        `**Đề xuất Người phụ trách chính (Trưởng nhóm) & Giảng viên độ trễ thấp nhất:**\n` +
        `> Dựa trên mô hình **TabPFN v2 (9.2.0)** và cặp ngưỡng Pareto **[0.23, 0.52]**:\n` +
        `1. **ThS. Nguyễn Minh Khoa (GV0101)** — Điểm tiêu chí Phụ trách chính: **91.5/100**, xác suất trễ dự báo thấp nhất **14.2% (Mức Thấp)**, tỷ lệ đúng hạn lịch sử **94.4%**.\n` +
        `2. **TS. Trần Thị Mai Anh (GV0102)** — Điểm tiêu chí: **88.2/100**, xác suất trễ dự báo **18.5% (Mức Thấp)**, phù hợp phối hợp nhóm chuyên môn.`;
    } else if (msg.includes("giờ chuẩn") || msg.includes("định mức")) {
      reply =
        `**Thống kê Định mức Giờ chuẩn Quy đổi (Thông tư 20/2020/TT-BGDĐT):**\n` +
        `• Tổng khối lượng quy đổi toàn Khoa: **${MOCK_STATS.total_converted_hours} giờ chuẩn**.\n` +
        `• Định mức chuẩn giảng dạy: **270 giờ chuẩn / năm học**.\n` +
        `• **ThS. Nguyễn Minh Khoa (GV0101):** Đã tích lũy **235.0 / 180.0 giờ chuẩn** công tác kiêm nhiệm & chuyên môn (đạt **130.6%** định mức năm).`;
    } else if (msg.includes("nhắc") || msg.includes("thiếu sót") || msg.includes("minh chứng")) {
      reply =
        `**Mẫu thông báo nhắc nhở thành viên nhóm bổ sung minh chứng:**\n` +
        `> Kính gửi Thầy/Cô thành viên nhóm công tác **[CV-2610-NHOM01]**,\n` +
        `> Đề nghị Thầy/Cô hoàn thiện file minh chứng khảo sát Tiêu chuẩn 6, 7 và gửi lên **Người phụ trách chính (ThS. Nguyễn Minh Khoa)** trước ngày **15/11/2026** để tổng hợp trình Trưởng Bộ môn kiểm duyệt đúng hạn.`;
    }

    return jsonResponse({
      reply,
      engine: "Gemini AI — Trợ lý Điều phối Khoa CNTT (HUIT)",
      used_external_api: true,
    });
  }

  // 4. Báo cáo thống kê & Độ chính xác ML
  if (url.includes("/api/reports/statistics")) return jsonResponse(MOCK_STATS);
  if (url.includes("/api/reports/ml-accuracy")) return jsonResponse(MOCK_ML_ACCURACY);
  if (url.includes("/api/reports/school-catalog/map-task") && method === "POST") {
    const u = new URL(url, "http://localhost");
    const taskId = Number(u.searchParams.get("task_id"));
    const scId = Number(u.searchParams.get("school_catalog_id"));
    const task = MOCK_TASKS.find((t) => t.id === taskId);
    const sc = MOCK_SCHOOL_CATALOG.find((s) => s.id === scId);
    if (task && sc) {
      task.school_catalog_code = sc.code;
      task.conversion_hours = sc.conversion_hours;
    }
    return jsonResponse({
      message: `Đã ánh xạ công việc vào danh mục Trường '${sc?.name || "TR"}' (${sc?.conversion_hours ?? 30} giờ chuẩn)`,
    });
  }
  if (url.includes("/api/reports/school-catalog")) {
    if (method === "POST") {
      const body = parseBody(init);
      const newItem = {
        id: MOCK_SCHOOL_CATALOG.length + 1,
        code: body.code || `TR-0${MOCK_SCHOOL_CATALOG.length + 1}`,
        catalog_code: body.code || `TR-0${MOCK_SCHOOL_CATALOG.length + 1}`,
        name: body.name || "Danh mục công việc cấp Trường mới",
        conversion_hours: Number(body.conversion_hours || 15),
        standard_hours: Number(body.conversion_hours || 15),
        task_type_name: "Công tác cấp Trường",
        note: body.note || "Quyết định quy đổi định mức cấp Trường",
        category: "Cấp Trường",
        mapped_task_count: 0,
      };
      MOCK_SCHOOL_CATALOG.unshift(newItem);
      return jsonResponse({
        message: `Đã thêm danh mục cấp Trường [${newItem.code}] ${newItem.name} (${newItem.conversion_hours} giờ chuẩn)`,
        item: newItem,
      });
    }
    return jsonResponse(MOCK_SCHOOL_CATALOG);
  }
  if (url.includes("/api/reports/lecturer-evaluation")) {
    const match = url.match(/\/lecturer-evaluation\/(\d+)/);
    const lecId = match ? Number(match[1]) : 2;
    const foundUser = MOCK_USERS.find((u) => u.id === lecId) || MOCK_USERS[1];
    return jsonResponse({
      ...MOCK_LECTURER_EVALUATION,
      lecturer: {
        ...MOCK_LECTURER_EVALUATION.lecturer,
        id: foundUser.id,
        username: foundUser.username,
        full_name: foundUser.full_name,
        lecturer_code: foundUser.lecturer_code,
        department_name: foundUser.department_name,
        degree: foundUser.degree,
        academic_rank: foundUser.academic_rank || "Giảng viên",
        email: foundUser.email,
      },
    });
  }

  // 5. Kế hoạch năm & Xuất Excel
  if (url.includes("/api/reports/plans")) {
    if (url.includes("/template") || url.includes("/export")) {
      return generateMockPlanTemplateExcel();
    }
    if (url.includes("/preview")) {
      return jsonResponse({
        rows: [
          {
            plan_code: "KH-001",
            semester: "HK1",
            title: "Biên soạn Đề cương chi tiết Trí tuệ nhân tạo",
            matched_task_type: "Biên soạn Giáo trình & Đề cương chi tiết học phần",
            task_group: "Đào tạo & Học vụ",
            scale: "quy mô chuẩn",
            role_mode: "Cá nhân",
            deliverable: "Hồ sơ Đề cương chi tiết chuẩn AUN-QA",
            deadline: "2026-11-30",
            conversion_hours: 30,
            priority: "Cao",
          },
        ],
      });
    }
    if (url.includes("/import")) {
      return jsonResponse({ message: "Đã import Kế hoạch Công tác Năm thành công!" });
    }
    return jsonResponse(MOCK_PLANS);
  }

  if (url.includes("/api/reports/export-late-excel")) {
    const urlObj = new URL(url, "http://localhost");
    const year = urlObj.searchParams.get("academic_year") || "2026-2027";
    const sem = urlObj.searchParams.get("semester") || "";
    return generateMockLateExcel(year, sem);
  }

  if (url.includes("/api/reports/export-excel")) {
    const urlObj = new URL(url, "http://localhost");
    const year = urlObj.searchParams.get("academic_year") || "2026-2027";
    const sem = urlObj.searchParams.get("semester") || "";
    return generateMockTasksExcel(year, sem);
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
  if (url.includes("/api/common/task-types")) {
    if (method === "PUT" && url.includes("/scales")) {
      const match = url.match(/\/task-types\/(\d+)\/scales/);
      const ttId = match ? Number(match[1]) : 0;
      const body = parseBody(init);
      const found = MOCK_TASK_TYPES.find((t) => t.id === ttId);
      if (found && Array.isArray(body.scales)) {
        found.scales = body.scales;
      }
      return jsonResponse({
        message: `Đã cập nhật định mức giờ chuẩn cho loại công việc "${found?.name || ttId}"`,
      });
    }
    return jsonResponse(MOCK_TASK_TYPES);
  }
  if (url.includes("/api/common/notifications")) {
    if (url.includes("/scan") && method === "POST") {
      return jsonResponse({ message: "Đã quét hạn hoàn thành công việc", scanned: MOCK_TASKS.length });
    }
    if (url.includes("/read-all") && method === "PUT") {
      MOCK_NOTIFICATIONS.forEach((n) => {
        n.is_read = true;
      });
      return jsonResponse({ message: "Đã đánh dấu tất cả thông báo là đã đọc" });
    }
    return jsonResponse(MOCK_NOTIFICATIONS);
  }

  // 7. Quản trị người dùng (CRUD)
  if (url.includes("/api/users")) {
    const getPermsForRole = (r: string) => {
      if (r === "admin") {
        return [
          "TASK_VIEW", "TASK_CREATE", "TASK_UPDATE", "TASK_DELETE", "TASK_ASSIGN",
          "TASK_UPDATE_PROGRESS", "TASK_APPROVE", "TASK_COMMENT", "PLAN_VIEW",
          "PLAN_MANAGE", "USER_VIEW", "USER_MANAGE", "DEPT_MANAGE",
          "ML_PREDICT_VIEW", "ML_RECOMMEND_USE",
        ];
      }
      if (r === "manager") {
        return [
          "TASK_VIEW", "TASK_CREATE", "TASK_UPDATE", "TASK_DELETE", "TASK_ASSIGN",
          "TASK_APPROVE", "TASK_COMMENT", "PLAN_VIEW", "PLAN_MANAGE",
          "USER_VIEW", "ML_PREDICT_VIEW", "ML_RECOMMEND_USE",
        ];
      }
      return ["TASK_VIEW", "TASK_UPDATE_PROGRESS", "TASK_COMMENT", "PLAN_VIEW", "USER_VIEW"];
    };

    if (method === "POST") {
      const body = parseBody(init);
      const dept = MOCK_DEPARTMENTS.find((d) => d.id === Number(body.department_id));
      const r = body.role || "lecturer";
      const scopeLvl =
        r === "admin"
          ? "SYSTEM"
          : r === "manager"
          ? body.department_id
            ? "DEPARTMENT"
            : "FACULTY"
          : "SELF";
      const newUser = {
        id: Math.max(...MOCK_USERS.map((u) => u.id)) + 1,
        username: body.username || `gv_new_${MOCK_USERS.length + 1}`,
        full_name: body.full_name || "Giảng viên Mới",
        role: r,
        department_id: body.department_id ?? 1,
        department_name: dept ? dept.name : "Khoa CNTT (Toàn Khoa)",
        lecturer_code: body.lecturer_code || `GV010${MOCK_USERS.length + 1}`,
        email: body.email || `${body.username || "gv"}@huit.edu.vn`,
        degree: body.degree || "ThS",
        academic_rank: r === "admin" ? "Quản trị Hệ thống" : r === "manager" ? "Quản lý" : "Giảng viên",
        is_active: true,
        is_online: false,
        open_tasks_count: 0,
        completed_tasks_count: 0,
        status_label: "Sẵn sàng nhận việc",
        activity_basis: "Tài khoản kích hoạt (is_active=True) • Hiện không có việc tồn đọng",
        teaching_hours_semester: 135,
        scope_level: scopeLvl,
        scope_description: `Phạm vi ${scopeLvl}`,
        permissions: getPermsForRole(r),
      };
      MOCK_USERS.push(newUser);
      return jsonResponse({ message: `Đã thêm tài khoản ${newUser.full_name} (${newUser.username}) thành công!` });
    }
    if (method === "PUT") {
      const match = url.match(/\/users\/(\d+)/);
      const uid = match ? Number(match[1]) : 0;
      const body = parseBody(init);
      const found = MOCK_USERS.find((u) => u.id === uid);
      if (found) {
        if (body.full_name !== undefined) found.full_name = body.full_name;
        if (body.role !== undefined) {
          found.role = body.role;
          found.permissions = getPermsForRole(body.role);
        }
        if (body.department_id !== undefined) {
          found.department_id = body.department_id;
          const dept = MOCK_DEPARTMENTS.find((d) => d.id === Number(body.department_id));
          found.department_name = dept ? dept.name : "Khoa CNTT (Toàn Khoa)";
        }
        if (body.role !== undefined || body.department_id !== undefined) {
          found.scope_level =
            found.role === "admin"
              ? "SYSTEM"
              : found.role === "manager"
              ? found.department_id
                ? "DEPARTMENT"
                : "FACULTY"
              : "SELF";
        }
        if (body.lecturer_code !== undefined) found.lecturer_code = body.lecturer_code;
        if (body.email !== undefined) found.email = body.email;
        if (body.degree !== undefined) found.degree = body.degree;
        if (body.is_active !== undefined) {
          found.is_active = body.is_active;
          found.status_label = body.is_active ? "Sẵn sàng nhận việc" : "Đã khóa";
        }
      }
      return jsonResponse({ message: "Đã cập nhật thông tin tài khoản thành công!" });
    }
    if (method === "DELETE") {
      const match = url.match(/\/users\/(\d+)/);
      const uid = match ? Number(match[1]) : 0;
      const idx = MOCK_USERS.findIndex((u) => u.id === uid);
      if (idx !== -1) MOCK_USERS.splice(idx, 1);
      return jsonResponse({ message: "Đã xóa tài khoản khỏi danh sách thành công!" });
    }
    return jsonResponse(MOCK_USERS);
  }

  // 8. Gợi ý phân công bằng Machine Learning
  if (url.includes("/api/tasks/preview-risk")) {
    const body = parseBody(init);
    const tt = MOCK_TASK_TYPES.find((t) => t.id === Number(body.task_type_id)) || MOCK_TASK_TYPES[0];
    const groupName = tt?.task_group || "Đào tạo & Học vụ";
    const candidates = [
      {
        rank: 1,
        lecturer_id: 2,
        lecturer_code: "GV0101",
        full_name: "ThS. Nguyễn Minh Khoa",
        degree: "ThS",
        department_name: "Bộ môn Công nghệ phần mềm (K01)",
        task_group_match: groupName,
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
        lecturer_code: "GV0102",
        full_name: "TS. Trần Thị Mai Anh",
        degree: "TS",
        department_name: "Bộ môn Công nghệ phần mềm (K01)",
        task_group_match: groupName,
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
          { feature: "mat_lecturer_type_late_rate", direction: "Giảm nguy cơ", delta_logit: -0.31 },
        ],
        recommendation: "Độ trễ dự báo thấp (18.5%), phù hợp giao việc hoặc phối hợp nhóm.",
      },
      {
        rank: 3,
        lecturer_id: 6,
        lecturer_code: "GV0103",
        full_name: "ThS. Lê Hoàng Nam",
        degree: "ThS",
        department_name: "Bộ môn Công nghệ phần mềm (K01)",
        task_group_match: groupName,
        group_done_count: 8,
        group_on_time_rate: 88.9,
        current_open_tasks: 2,
        current_overdue_tasks: 0,
        hist_completed_count: 9,
        hist_late_rate: 11.1,
        probability: 0.215,
        level: "Thấp",
        is_lowest_delay_group: true,
        lead_score: 84.0,
        is_recommended_lead: false,
        lead_conditions: [
          {
            criterion: "1. Nguy cơ trễ hạn dự báo thấp nhất (ML Risk)",
            passed: true,
            detail: "Xác suất trễ dự báo 21.5% (Mức Thấp)",
          },
          {
            criterion: "2. Kinh nghiệm thực hiện trong Nhóm công việc được chọn",
            passed: true,
            detail: "Đã hoàn thành 8 việc nhóm này (Đúng hạn 88.9%)",
          },
        ],
        top_factors: [
          { feature: "current_open_tasks", direction: "Giảm nguy cơ", delta_logit: -0.22 },
        ],
        recommendation: "Xác suất trễ thấp (21.5%), phù hợp tham gia tổ công tác chuyên môn.",
      },
    ];
    return jsonResponse({
      selected_task_group: groupName,
      total_evaluated_in_group: candidates.length,
      filter_note: `Chỉ lọc các giảng viên thuộc nhóm công việc [${groupName}] và xếp hạng theo độ trễ dự báo thấp nhất.`,
      recommended_lead: {
        lecturer_id: 2,
        lecturer_code: "GV0101",
        full_name: "ThS. Nguyễn Minh Khoa",
        degree: "ThS",
        department_name: "Bộ môn Công nghệ phần mềm (K01)",
        probability: 0.142,
        lead_score: 91.5,
        conditions: candidates[0].lead_conditions,
        reason_summary:
          `Đạt điểm tiêu chí Phụ trách chính cao nhất (91.5/100): nguy cơ trễ thấp nhất (14.2%), đã hoàn thành 14 việc thuộc nhóm ${groupName} và không có việc quá hạn.`,
      },
      candidates,
    });
  }

  // 9. Thao tác công việc nhóm, tiến độ, minh chứng, gia hạn
  if (url.includes("/upload-evidence") && method === "POST") {
    return jsonResponse({
      file_name: "MinhChung_CongViec_HUIT.pdf",
      file_url: "/uploads/evidence/MinhChung_KetQua_CongViec_HUIT.txt",
    });
  }
  if (url.includes("/progress") && method === "POST") {
    const match = url.match(/\/tasks\/(\d+)\/progress/);
    const tid = match ? Number(match[1]) : 0;
    const body = parseBody(init);
    const task = MOCK_TASKS.find((t) => t.id === tid);
    if (task) {
      const pct = Math.max(0, Math.min(100, Number(body.progress_pct ?? 100)));
      const assignee =
        task.assignees?.find((a: any) => a.lecturer_id === Number(body.lecturer_id)) ||
        task.assignees?.[0];
      if (assignee) {
        assignee.progress_pct = pct;
        assignee.status = pct >= 100 ? "Hoàn thành" : pct > 0 ? "Đang thực hiện" : "Mới giao";
        if (body.evidence_file_name) {
          assignee.latest_evidence_name = body.evidence_file_name;
          assignee.latest_evidence_url =
            body.evidence_file_url || "/uploads/evidence/MinhChung_KetQua_CongViec_HUIT.txt";
        }
        const isGroup = task.assignment_mode === "Group" || (task.assignees?.length || 0) >= 2;
        if (isGroup) {
          assignee.lead_approval_status = assignee.is_lead
            ? "Trưởng nhóm đã duyệt"
            : "Chờ Trưởng nhóm duyệt";
          assignee.member_evidence_status = assignee.is_lead
            ? "Minh chứng chính thức của Nhóm"
            : "Đã gửi Trưởng nhóm";
          if (!assignee.is_lead) {
            task.lead_approval_status = "Chờ Trưởng nhóm duyệt";
          }
        } else {
          assignee.lead_approval_status = "Trưởng nhóm đã duyệt";
        }
        if (body.note) {
          assignee.review_feedback = `[Tự cập nhật ${pct}%]: ${body.note}`;
        }
      }
      // HỆ THỐNG TỰ ĐỘNG TÍNH TOÁN % TIẾN ĐỘ DỰ ÁN DỰA TRÊN TIẾN ĐỘ CỦA CÁC THÀNH VIÊN (VD: 3 NGƯỜI)
      const calcPct = calculateProjectProgressFromMembers(task.assignees, pct);
      task.progress_pct = calcPct;
      if (calcPct > 0 && task.status === "Mới giao") {
        task.status = "Đang thực hiện";
      }
      if (calcPct >= 100 && (task.assignment_mode !== "Group" || task.reviewer_approval_status === "Đã phê duyệt quyết định Trưởng nhóm")) {
        task.status = "Hoàn thành";
      }
      return jsonResponse({
        message: `Đã tự cập nhật tiến độ cá nhân (${pct}%). Hệ thống tự động tính tiến độ dự án (${task.assignees?.length || 1} thành viên) = ${calcPct}%!`,
        progress_pct: pct,
        project_progress_pct: calcPct,
        lead_approval_status: assignee?.lead_approval_status,
      });
    }
    return jsonResponse({ message: "Đã cập nhật tiến độ thành công!" });
  }
  if (url.includes("/lead-approve") && method === "POST") {
    const match = url.match(/\/tasks\/(\d+)\/lead-approve/);
    const tid = match ? Number(match[1]) : 0;
    const body = parseBody(init);
    const task = MOCK_TASKS.find((t) => t.id === tid);
    if (task) {
      const approvals: any[] = Array.isArray(body.member_approvals) ? body.member_approvals : [];
      approvals.forEach((item) => {
        const member = task.assignees?.find((a: any) => Number(a.lecturer_id) === Number(item.lecturer_id));
        if (member) {
          member.lead_approval_status = item.approval_status || "Trưởng nhóm đã duyệt";
          member.member_evidence_status =
            item.approval_status === "Yêu cầu chỉnh sửa" ? "Cần bổ sung" : "Đã xác nhận";
          if (item.review_note) {
            member.review_feedback = `[Trưởng nhóm phê duyệt]: ${item.review_note}`;
          }
        }
      });
      // HỆ THỐNG TỰ ĐỘNG TÍNH TOÁN % TIẾN ĐỘ CHO DỰ ÁN DỰA TRÊN TIẾN ĐỘ CỦA 3 NGƯỜI
      const calcPct = calculateProjectProgressFromMembers(task.assignees, task.progress_pct);
      task.progress_pct = calcPct;
      const allApproved = (task.assignees || []).every(
        (a: any) => a.lead_approval_status === "Trưởng nhóm đã duyệt"
      );
      if (body.submit_to_reviewer !== false && allApproved) {
        task.lead_approval_status = "Đã duyệt & Trình Người kiểm tra";
        task.reviewer_approval_status = "Chờ Người kiểm tra duyệt";
      } else {
        task.lead_approval_status = allApproved
          ? "Đã duyệt & Trình Người kiểm tra"
          : "Yêu cầu thành viên chỉnh sửa";
      }
      if (body.lead_decision_note) {
        task.lead_decision_note = body.lead_decision_note;
      }
      return jsonResponse({
        message: `Trưởng nhóm đã phê duyệt! Hệ thống tự động tính toán tiến độ dự án từ ${task.assignees?.length || 3} thành viên đạt ${calcPct}% và gửi lên Người kiểm tra.`,
        project_progress_pct: calcPct,
        lead_approval_status: task.lead_approval_status,
        reviewer_approval_status: task.reviewer_approval_status,
      });
    }
    return jsonResponse({ message: "Đã phê duyệt tiến độ nhóm thành công!" });
  }
  if (url.includes("/reviewer-approve") && method === "POST") {
    const match = url.match(/\/tasks\/(\d+)\/reviewer-approve/);
    const tid = match ? Number(match[1]) : 0;
    const body = parseBody(init);
    const task = MOCK_TASKS.find((t) => t.id === tid);
    if (task) {
      const calcPct = calculateProjectProgressFromMembers(task.assignees, task.progress_pct);
      task.progress_pct = calcPct;
      task.reviewer_approval_status =
        body.approval_status || "Đã phê duyệt quyết định Trưởng nhóm";
      task.reviewer_decision_note = body.reviewer_decision_note || "";
      if (task.reviewer_approval_status === "Đã phê duyệt quyết định Trưởng nhóm") {
        if (calcPct >= 100) {
          task.status = "Hoàn thành";
        }
      } else {
        task.lead_approval_status = "Chờ Trưởng nhóm duyệt";
      }
      return jsonResponse({
        message: `Người kiểm tra đã xác nhận: "${task.reviewer_approval_status}" (Tiến độ chung dự án: ${calcPct}%).`,
        project_progress_pct: calcPct,
        reviewer_approval_status: task.reviewer_approval_status,
        status: task.status,
      });
    }
    return jsonResponse({ message: "Đã phê duyệt quyết định của Trưởng nhóm!" });
  }
  if (url.includes("/member-evidence") && method === "POST") {
    return jsonResponse({
      message: "Đã gửi minh chứng thành viên lên Trưởng nhóm (Người phụ trách chính) chờ kiểm duyệt.",
    });
  }
  if (url.includes("/feedback") && method === "POST") {
    return jsonResponse({
      message: "Đã gửi thông báo nhắc nhở thiếu sót và cập nhật trạng thái cho thành viên nhóm.",
    });
  }
  if (url.includes("/delegate") && method === "POST") {
    return jsonResponse({
      message: "Đã lưu phân công nhiệm vụ cho các thành viên trong nhóm.",
    });
  }
  if (url.includes("/api/tasks/extensions") && url.includes("/review") && method === "PUT") {
    const match = url.match(/\/extensions\/(\d+)\/review/);
    const extId = match ? Number(match[1]) : 0;
    const body = parseBody(init);
    const ext = MOCK_EXTENSIONS.find((e) => e.id === extId);
    if (ext) {
      if (
        body.acting_dept_head_department_id !== undefined &&
        body.acting_dept_head_department_id !== null &&
        Number(ext.department_id || 1) !== Number(body.acting_dept_head_department_id)
      ) {
        return jsonResponse(
          {
            detail:
              "Phân quyền CSDL (RBAC): Trưởng Bộ môn chỉ quản lý và duyệt gia hạn cho các công việc thuộc Bộ môn đó của Khoa!",
          },
          403
        );
      }
      ext.status = body.status || "Đã duyệt";
      if (ext.status === "Đã duyệt") {
        const task = MOCK_TASKS.find((t) => t.id === ext.task_id);
        if (task) task.current_deadline = ext.proposed_deadline;
      }
    }
    return jsonResponse({
      message: `Đã ${body.status || "duyệt"} yêu cầu gia hạn thành công!`,
    });
  }
  if (url.includes("/extensions") && method === "POST") {
    const match = url.match(/\/tasks\/(\d+)\/extensions/);
    const tid = match ? Number(match[1]) : 1;
    const body = parseBody(init);
    const task = MOCK_TASKS.find((t) => t.id === tid) || MOCK_TASKS[0];
    const newExt = {
      id: MOCK_EXTENSIONS.length + 1,
      task_id: task.id,
      task_title: task.title,
      task_code: task.code,
      lecturer_name: task.lead_lecturer_name || "ThS. Nguyễn Minh Khoa",
      lecturer_code: "GV0101",
      current_deadline: task.current_deadline,
      proposed_deadline: body.proposed_deadline || task.current_deadline,
      reason: body.reason || "Đề xuất điều chỉnh thời hạn theo tiến độ thực tế",
      status: "Chờ duyệt",
      created_at: new Date().toISOString().slice(0, 16).replace("T", " "),
    };
    MOCK_EXTENSIONS.unshift(newExt);
    return jsonResponse({ message: "Đã gửi yêu cầu gia hạn thành công!" });
  }
  if (url.includes("/api/tasks/extensions")) return jsonResponse(MOCK_EXTENSIONS);

  if (url.includes("/detail")) {
    const match = url.match(/\/tasks\/(\d+)\/detail/);
    const tid = match ? Number(match[1]) : 29;
    const found = MOCK_TASKS.find((t) => t.id === tid) || MOCK_TASKS[0];
    return jsonResponse({
      ...found,
      progress_logs: [
        {
          id: 1,
          lecturer_name: found.lead_lecturer_name || "ThS. Nguyễn Minh Khoa",
          progress_pct: 65,
          note: "Đã hoàn thành rà soát chuẩn đầu ra và tổng hợp minh chứng giai đoạn 1",
          evidence_file_name: "MinhChung_CDR_CNPM.pdf",
          evidence_file_url: "/uploads/evidence/MinhChung_KetQua_CongViec_HUIT.txt",
          created_at: "2026-10-28 15:30",
        },
      ],
    });
  }

  if (url.includes("/api/tasks")) {
    if (method === "POST") {
      const body = parseBody(init);
      const tt = MOCK_TASK_TYPES.find((t) => t.id === Number(body.task_type_id)) || MOCK_TASK_TYPES[0];
      const scaleObj = tt.scales?.find((s: any) => s.scale === body.scale) || tt.scales?.[1];
      const lecIds: number[] = Array.isArray(body.lecturer_ids) && body.lecturer_ids.length > 0 ? body.lecturer_ids : [2];
      const leadId = Number(body.lead_lecturer_id || lecIds[0]);
      const leadUser = MOCK_USERS.find((u) => u.id === leadId) || MOCK_USERS[1];
      if (
        body.acting_dept_head_department_id !== undefined &&
        body.acting_dept_head_department_id !== null
      ) {
        const targetDept = Number(body.acting_dept_head_department_id);
        const invalidMember = lecIds.some((lid) => {
          const u = MOCK_USERS.find((x) => x.id === Number(lid));
          return u && u.department_id && Number(u.department_id) !== targetDept;
        });
        if (invalidMember) {
          return jsonResponse(
            {
              detail:
                "Phân quyền CSDL (RBAC): Trưởng Bộ môn chỉ quản lý và giao được các công việc thuộc Bộ môn đó của Khoa!",
            },
            403
          );
        }
      }
      const taskDeptId = Number(body.department_id || leadUser.department_id || 1);
      const taskDeptObj = MOCK_DEPARTMENTS.find((d) => d.id === taskDeptId);
      const newCode = `CV-2611-${String(MOCK_TASKS.length + 1).padStart(3, "0")}`;
      const newTask = {
        id: Math.max(...MOCK_TASKS.map((t) => t.id)) + 1,
        task_id: Math.max(...MOCK_TASKS.map((t) => t.id)) + 1,
        code: newCode,
        title: body.title || "Công việc mới phân công",
        department_id: taskDeptId,
        department_name: taskDeptObj?.name || leadUser.department_name || "Bộ môn Công nghệ phần mềm (K01)",
        task_type_id: tt.id,
        task_type_name: tt.name,
        task_group: tt.task_group,
        scale: body.scale || "quy mô chuẩn",
        priority: body.priority || "Cao",
        complexity: body.complexity || "Trung bình",
        assignment_mode: lecIds.length >= 2 ? "Group" : "Individual",
        status: "Mới giao",
        progress_pct: 0,
        lead_approval_status: "Chờ Trưởng nhóm duyệt",
        reviewer_approval_status: "Chờ Người kiểm tra duyệt",
        is_late: false,
        delay_days: 0,
        conversion_hours: scaleObj?.conversion_hours ?? 30.0,
        school_catalog_code: null,
        original_deadline: body.original_deadline || "2026-11-25",
        current_deadline: body.original_deadline || "2026-11-25",
        assigned_at: new Date().toISOString().slice(0, 10),
        reviewer_id: 1,
        reviewer_name: "TS. Nguyễn Văn Lễ",
        lead_lecturer_id: leadId,
        lead_lecturer_name: leadUser.full_name,
        academic_year: "2026-2027",
        semester: "HK1",
        ml_prediction: {
          probability: 0.142,
          level: "Thấp",
          recommendation: "Phân công tối ưu theo gợi ý mô hình TabPFN v2.",
        },
        assignees: lecIds.map((lid, idx) => {
          const u = MOCK_USERS.find((x) => x.id === Number(lid)) || MOCK_USERS[1];
          return {
            assignment_id: Date.now() + idx,
            lecturer_id: u.id,
            lecturer_name: u.full_name,
            lecturer_code: u.lecturer_code,
            department_id: u.department_id || taskDeptId,
            department_name: u.department_name || taskDeptObj?.name,
            is_lead: u.id === leadId,
            member_task_note: body.member_notes?.[String(u.id)] || "",
            progress_pct: 0,
            lead_approval_status: u.id === leadId ? "Trưởng nhóm đã duyệt" : "Chờ Trưởng nhóm duyệt",
            status: "Mới giao",
            is_late: false,
            ml_prediction: {
              probability: 0.142,
              level: "Thấp",
              recommendation: "Độ trễ dự báo thấp nhất trong nhóm chuyên môn.",
            },
          };
        }),
      };
      MOCK_TASKS.unshift(newTask);
      MOCK_STATS.total_tasks += 1;
      MOCK_STATS.new += 1;
      return jsonResponse({
        id: newTask.id,
        code: newTask.code,
        department_id: newTask.department_id,
        department_name: newTask.department_name,
        reviewer_name: newTask.reviewer_name,
        message: "Giao việc thành công",
      });
    }
    return jsonResponse(MOCK_TASKS);
  }

  return jsonResponse({ success: true, message: "OK" });
}
