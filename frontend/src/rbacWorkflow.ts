export type WorkflowRoleCode =
  | "MEMBER"
  | "GROUP_LEAD"
  | "REVIEWER"
  | "DEPT_HEAD"
  | "DEAN";

export type WorkflowRoleFilter = "AUTO" | WorkflowRoleCode;

export interface WorkflowAssignee {
  assignment_id?: number;
  lecturer_id: number;
  lecturer_name: string;
  lecturer_code?: string;
  department_id?: number;
  department_name?: string;
  is_lead?: boolean;
  progress_pct: number;
  lead_approval_status?: string;
  member_evidence_status?: string;
  latest_evidence_name?: string | null;
  latest_evidence_url?: string | null;
  review_feedback?: string | null;
  status?: string;
}

export interface TaskRoleEvaluation {
  effectiveRole: WorkflowRoleCode;
  effectiveRoleLabel: string;
  projectProgressPct: number;
  showIndividualMemberProgress: boolean;
  canSelfUpdateProgress: boolean;
  canLeadApproveMembers: boolean;
  canReviewerApproveDecision: boolean;
  targetSelfAssignee: WorkflowAssignee | null;
  approvedMemberCount: number;
  totalMemberCount: number;
  taskDepartmentId: number;
  taskDepartmentName: string;
  managedDepartmentId: number | null;
  isWithinDepartmentScope: boolean;
}

export const FACULTY_DEPARTMENT_NAMES: Record<number, string> = {
  1: "Bộ môn Công nghệ phần mềm (K01)",
  2: "Bộ môn Hệ thống thông tin (K02)",
  3: "Bộ môn Khoa học máy tính (K03)",
  4: "Bộ môn Mạng máy tính & ATTT (K04)",
};

export function resolveTaskDepartmentId(task: any): number {
  if (task?.department_id !== undefined && task?.department_id !== null) {
    return Number(task.department_id);
  }
  const firstAssigneeDept = task?.assignees?.[0]?.department_id;
  if (firstAssigneeDept !== undefined && firstAssigneeDept !== null) {
    return Number(firstAssigneeDept);
  }
  return 1;
}

export function resolveTaskDepartmentName(task: any): string {
  if (task?.department_name) return String(task.department_name);
  const deptId = resolveTaskDepartmentId(task);
  return FACULTY_DEPARTMENT_NAMES[deptId] || `Bộ môn K0${deptId}`;
}

/**
 * Kiểm tra xem Trưởng Bộ môn (gắn với department_id cụ thể của Khoa) có quyền quản lý
 * công việc này hay không. Trưởng Bộ môn CHỈ quản lý được các công việc thuộc Bộ môn đó của Khoa.
 */
export function isTaskManagedByDepartmentHead(
  task: any,
  deptHeadDepartmentId: number | null | undefined
): boolean {
  if (deptHeadDepartmentId === null || deptHeadDepartmentId === undefined) {
    return false;
  }
  const taskDeptId = resolveTaskDepartmentId(task);
  if (Number(taskDeptId) === Number(deptHeadDepartmentId)) {
    return true;
  }
  const assignees: WorkflowAssignee[] = Array.isArray(task?.assignees)
    ? task.assignees
    : [];
  return assignees.some(
    (a) =>
      a.department_id !== undefined &&
      a.department_id !== null &&
      Number(a.department_id) === Number(deptHeadDepartmentId)
  );
}

/**
 * Lọc danh sách công việc theo vai trò & phạm vi Bộ môn trong Khoa:
 * - Trưởng Khoa (DEAN): Quản lý tất cả các công việc của mọi Bộ môn trong Khoa (K01..K04).
 * - Trưởng Bộ môn (DEPT_HEAD): CHỈ quản lý được các công việc thuộc đúng Bộ môn đó của Khoa (tasks.department_id = deptHeadDepartmentId).
 * - Người kiểm tra / Trưởng nhóm / Thành viên: Theo phạm vi phân công hoặc toàn danh sách mẫu.
 */
export function filterTasksByRoleAndDepartment(
  tasks: any[],
  currentUser: any,
  roleOverride: WorkflowRoleFilter = "AUTO",
  selectedDeptHeadDeptId?: number | null
): any[] {
  if (!Array.isArray(tasks)) return [];

  // Xác định vai trò hiệu lực ở cấp danh sách
  let isDeptHeadMode = false;
  let activeDeptId: number | null = null;

  if (roleOverride === "DEPT_HEAD") {
    isDeptHeadMode = true;
    activeDeptId =
      selectedDeptHeadDeptId ??
      (currentUser?.department_id ? Number(currentUser.department_id) : 1);
  } else if (
    roleOverride === "AUTO" &&
    currentUser?.role === "manager" &&
    currentUser?.department_id !== null &&
    currentUser?.department_id !== undefined
  ) {
    isDeptHeadMode = true;
    activeDeptId =
      selectedDeptHeadDeptId ?? Number(currentUser.department_id);
  }

  if (isDeptHeadMode && activeDeptId !== null) {
    return tasks.filter((t) => isTaskManagedByDepartmentHead(t, activeDeptId));
  }

  return tasks;
}

/**
 * Hệ thống tự động tính toán % tiến độ của dự án/công việc dựa trên trung bình cộng
 * tiến độ của các thành viên trong nhóm (VD: 3 giảng viên trong nhóm).
 */
export function calculateProjectProgressFromMembers(
  assignees: Array<{ progress_pct?: number | null }> | null | undefined,
  fallbackPct = 0
): number {
  if (!Array.isArray(assignees) || assignees.length === 0) {
    return Math.max(0, Math.min(100, Math.round(Number(fallbackPct || 0))));
  }
  const sum = assignees.reduce((acc, item) => {
    const val = Math.max(0, Math.min(100, Number(item?.progress_pct ?? 0)));
    return acc + val;
  }, 0);
  return Math.round(sum / assignees.length);
}

/**
 * Xác định vai trò phân quyền thực tế của tài khoản trên một công việc cụ thể
 * và quy tắc hiển thị tiến độ + phạm vi Bộ môn:
 * - Thành viên (MEMBER): Tự cập nhật % tiến độ cá nhân -> gửi Trưởng nhóm.
 * - Trưởng nhóm / Người phụ trách chính (GROUP_LEAD): Phê duyệt tiến độ thành viên -> gửi hệ thống tự tính % từ 3 người -> trình Người kiểm tra.
 * - Người kiểm tra (REVIEWER): Quan sát tiến độ từng thành viên & phê duyệt quyết định của Trưởng nhóm.
 * - Trưởng Bộ môn (DEPT_HEAD): Chỉ quản lý các công việc thuộc Bộ môn đó của Khoa (tasks.department_id = users.department_id) & chỉ hiển thị % tiến độ chung công việc.
 * - Trưởng Khoa (DEAN): Quản lý công việc toàn Khoa (tất cả Bộ môn) & chỉ hiển thị % tiến độ chung công việc.
 */
export function evaluateTaskRoleAndVisibility(
  currentUser: any,
  task: any,
  roleOverride: WorkflowRoleFilter = "AUTO",
  selectedDeptHeadDeptId?: number | null
): TaskRoleEvaluation {
  const assignees: WorkflowAssignee[] = Array.isArray(task?.assignees) ? task.assignees : [];
  const projectProgressPct = calculateProjectProgressFromMembers(assignees, task?.progress_pct ?? 0);
  const totalMemberCount = assignees.length;
  const approvedMemberCount = assignees.filter(
    (a) =>
      a.lead_approval_status === "Trưởng nhóm đã duyệt" ||
      a.member_evidence_status === "Đã xác nhận" ||
      a.member_evidence_status === "Minh chứng chính thức của Nhóm"
  ).length;

  const myAssign =
    assignees.find((a) => Number(a.lecturer_id) === Number(currentUser?.id)) || null;
  const isUserLead =
    Boolean(task?.lead_lecturer_id && Number(task.lead_lecturer_id) === Number(currentUser?.id)) ||
    Boolean(myAssign?.is_lead);
  const isUserReviewer =
    Boolean(task?.reviewer_id && Number(task.reviewer_id) === Number(currentUser?.id)) ||
    currentUser?.rbac_role_code === "TASK_REVIEWER" ||
    currentUser?.username === "kiemtra_k01";

  const isSystemAdmin = currentUser?.role === "admin";
  let effectiveRole: WorkflowRoleCode = "MEMBER";

  if (roleOverride !== "AUTO") {
    effectiveRole = roleOverride;
  } else if (currentUser?.role === "manager") {
    if (currentUser?.department_id === null || currentUser?.username === "truongkhoa") {
      effectiveRole = "DEAN";
    } else {
      effectiveRole = "DEPT_HEAD";
    }
  } else if (isSystemAdmin) {
    effectiveRole = "DEAN";
  } else if (isUserReviewer) {
    effectiveRole = "REVIEWER";
  } else if (isUserLead) {
    effectiveRole = "GROUP_LEAD";
  } else {
    effectiveRole = "MEMBER";
  }

  const taskDepartmentId = resolveTaskDepartmentId(task);
  const taskDepartmentName = resolveTaskDepartmentName(task);

  const managedDepartmentId =
    effectiveRole === "DEPT_HEAD"
      ? selectedDeptHeadDeptId ??
        (currentUser?.department_id ? Number(currentUser.department_id) : 1)
      : null;

  const isWithinDepartmentScope =
    effectiveRole === "DEPT_HEAD"
      ? isTaskManagedByDepartmentHead(task, managedDepartmentId)
      : true;

  const roleLabels: Record<WorkflowRoleCode, string> = {
    MEMBER: "Giảng viên (Thành viên tự cập nhật %)",
    GROUP_LEAD: "Trưởng nhóm / Người phụ trách chính (Phê duyệt & Trình hệ thống)",
    REVIEWER: "Người kiểm tra (Quan sát từng thành viên & Phê duyệt Trưởng nhóm)",
    DEPT_HEAD: `Trưởng Bộ môn (Chỉ quản lý công việc thuộc ${FACULTY_DEPARTMENT_NAMES[managedDepartmentId || 1] || "Bộ môn"} & Xem % chung)`,
    DEAN: isSystemAdmin
      ? "Quản trị viên Hệ thống (SYSTEM • Toàn quyền 15/15 quyền nguyên tử)"
      : "Trưởng Khoa (Quản lý Toàn Khoa CNTT & Chỉ xem % tiến độ chung công việc)",
  };

  // Quy tắc hiển thị:
  // Trưởng Bộ môn (DEPT_HEAD) và Trưởng Khoa (DEAN) chỉ cần thể hiện phần trăm tiến độ chung của công việc (projectProgressPct%).
  // Riêng Quản trị viên Hệ thống (admin - SYSTEM 15/15 quyền) có cả TASK_UPDATE_PROGRESS và TASK_APPROVE theo Bảng 3.4.
  const showIndividualMemberProgress =
    isSystemAdmin ||
    effectiveRole === "MEMBER" ||
    effectiveRole === "GROUP_LEAD" ||
    effectiveRole === "REVIEWER";

  let targetSelfAssignee: WorkflowAssignee | null = myAssign;
  if (!targetSelfAssignee && assignees.length > 0) {
    if (effectiveRole === "GROUP_LEAD" || isSystemAdmin) {
      targetSelfAssignee = assignees.find((a) => a.is_lead) || assignees[0];
    } else if (effectiveRole === "MEMBER") {
      targetSelfAssignee = assignees.find((a) => !a.is_lead) || assignees[0];
    }
  }

  const canSelfUpdateProgress =
    isSystemAdmin || effectiveRole === "MEMBER" || effectiveRole === "GROUP_LEAD";
  const canLeadApproveMembers = isSystemAdmin || effectiveRole === "GROUP_LEAD";
  const canReviewerApproveDecision = isSystemAdmin || effectiveRole === "REVIEWER";

  return {
    effectiveRole,
    effectiveRoleLabel: roleLabels[effectiveRole],
    projectProgressPct,
    showIndividualMemberProgress,
    canSelfUpdateProgress,
    canLeadApproveMembers,
    canReviewerApproveDecision,
    targetSelfAssignee,
    approvedMemberCount,
    totalMemberCount,
    taskDepartmentId,
    taskDepartmentName,
    managedDepartmentId,
    isWithinDepartmentScope,
  };
}

export const SQL_RBAC_DDL_TEXT = `-- =============================================================================
-- CÂU LỆNH SQL CƠ SỞ DỮ LIỆU: BẢNG, KHÓA CHÍNH, KHÓA NGOẠI, TRIGGER & PHÂN QUYỀN RBAC
-- File đầy đủ: /backend/sql/schema_and_rbac_permissions.sql
-- =============================================================================

-- 1. BẢNG VAI TRÒ & QUYỀN HẠN PHÂN QUYỀN RÕ RÀNG (RBAC)
CREATE TABLE IF NOT EXISTS rbac_roles (
    role_code VARCHAR(50) PRIMARY KEY,
    role_name VARCHAR(120) NOT NULL,
    hierarchy_level INTEGER NOT NULL CHECK (hierarchy_level BETWEEN 1 AND 6),
    can_view_member_detail BOOLEAN NOT NULL DEFAULT 0,
    can_view_project_summary BOOLEAN NOT NULL DEFAULT 1,
    description TEXT
);

CREATE TABLE IF NOT EXISTS rbac_permissions (
    permission_code VARCHAR(80) PRIMARY KEY,
    permission_name VARCHAR(200) NOT NULL,
    module_name VARCHAR(80) NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS rbac_role_permissions (
    role_code VARCHAR(50) NOT NULL,
    permission_code VARCHAR(80) NOT NULL,
    PRIMARY KEY (role_code, permission_code),
    CONSTRAINT fk_rp_role FOREIGN KEY (role_code) REFERENCES rbac_roles(role_code) ON DELETE CASCADE,
    CONSTRAINT fk_rp_perm FOREIGN KEY (permission_code) REFERENCES rbac_permissions(permission_code) ON DELETE CASCADE
);

-- 2. BẢNG CÔNG VIỆC / DỰ ÁN (TASKS) GẮN KHÓA NGOẠI BỘ MÔN (DEPARTMENT_ID)
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(32) NOT NULL UNIQUE,
    title VARCHAR(300) NOT NULL,
    task_type_id INTEGER NOT NULL,
    -- Khóa ngoại xác định công việc thuộc Bộ môn nào của Khoa (K01, K02, K03, K04)
    department_id INTEGER NOT NULL,
    assignment_mode VARCHAR(32) NOT NULL DEFAULT 'Group' CHECK (assignment_mode IN ('Individual', 'Group')),
    -- Tiến độ chung của dự án (%) được hệ thống tự động tính từ trung bình 3 thành viên
    progress_pct INTEGER NOT NULL DEFAULT 0 CHECK (progress_pct BETWEEN 0 AND 100),
    created_by INTEGER NULL,
    lead_lecturer_id INTEGER NOT NULL,
    reviewer_id INTEGER NULL,
    lead_approval_status VARCHAR(64) NOT NULL DEFAULT 'Chờ Trưởng nhóm duyệt',
    lead_decision_note TEXT NULL,
    lead_submitted_at DATETIME NULL,
    reviewer_approval_status VARCHAR(64) NOT NULL DEFAULT 'Chờ Người kiểm tra duyệt',
    reviewer_decision_note TEXT NULL,
    reviewer_approved_at DATETIME NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Đang thực hiện',
    CONSTRAINT fk_tasks_lead FOREIGN KEY (lead_lecturer_id) REFERENCES users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_tasks_reviewer FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_tasks_dept FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT
);

-- 3. BẢNG PHÂN CÔNG THÀNH VIÊN NHÓM (TASK_ASSIGNMENTS)
CREATE TABLE IF NOT EXISTS task_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    lecturer_id INTEGER NOT NULL,
    is_lead BOOLEAN NOT NULL DEFAULT 0,
    -- Giảng viên tự cập nhật % tiến độ cá nhân
    progress_pct INTEGER NOT NULL DEFAULT 0 CHECK (progress_pct BETWEEN 0 AND 100),
    self_updated_at DATETIME NULL,
    -- Trưởng nhóm phê duyệt tiến độ thành viên
    lead_approval_status VARCHAR(64) NOT NULL DEFAULT 'Chờ Trưởng nhóm duyệt'
        CHECK (lead_approval_status IN ('Chờ Trưởng nhóm duyệt', 'Trưởng nhóm đã duyệt', 'Yêu cầu chỉnh sửa')),
    lead_approved_by INTEGER NULL,
    lead_approved_at DATETIME NULL,
    review_feedback TEXT NULL,
    CONSTRAINT uq_task_lecturer UNIQUE (task_id, lecturer_id),
    CONSTRAINT fk_assign_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    CONSTRAINT fk_assign_lecturer FOREIGN KEY (lecturer_id) REFERENCES users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_assign_lead_approver FOREIGN KEY (lead_approved_by) REFERENCES users(id) ON DELETE SET NULL
);

-- 4. TRIGGER HỆ THỐNG TỰ ĐỘNG TÍNH TOÁN % TIẾN ĐỘ DỰ ÁN DỰA TRÊN 3 THÀNH VIÊN
CREATE TRIGGER IF NOT EXISTS trg_auto_calc_task_progress_on_update
AFTER UPDATE OF progress_pct, lead_approval_status ON task_assignments
FOR EACH ROW
BEGIN
    UPDATE tasks
    SET progress_pct = COALESCE(
        (
            SELECT CAST(ROUND(AVG(CAST(ta.progress_pct AS REAL)), 0) AS INTEGER)
            FROM task_assignments ta
            WHERE ta.task_id = NEW.task_id
        ),
        0
    )
    WHERE id = NEW.task_id;
END;

-- 5. TRIGGER RÀNG BUỘC PHẠM VI BỘ MÔN CỦA TRƯỞNG BỘ MÔN (DEPT_HEAD)
-- Trưởng Bộ môn chỉ quản lý và giao được các công việc thuộc đúng Bộ môn đó của Khoa (tasks.department_id = users.department_id)
CREATE TRIGGER IF NOT EXISTS trg_enforce_dept_head_task_insert
BEFORE INSERT ON tasks
FOR EACH ROW
WHEN NEW.created_by IS NOT NULL
  AND (SELECT rbac_role_code FROM users WHERE id = NEW.created_by) = 'DEPT_HEAD'
  AND NEW.department_id != (SELECT department_id FROM users WHERE id = NEW.created_by)
BEGIN
    SELECT RAISE(ABORT, 'RBAC Department Scope Violation: Trưởng Bộ môn chỉ được quản lý các công việc thuộc Bộ môn của mình trong Khoa!');
END;

-- 6. VIEW PHÂN QUYỀN DÀNH CHO TRƯỞNG BỘ MÔN & TRƯỞNG KHOA (CHỈ HIỂN THỊ % TIẾN ĐỘ CHUNG CÔNG VIỆC)
CREATE VIEW IF NOT EXISTS vw_manager_project_progress_summary AS
SELECT
    t.id AS task_id,
    t.code AS task_code,
    t.title AS task_title,
    t.department_id,
    t.progress_pct AS project_progress_pct,
    COUNT(ta.id) AS member_count,
    t.lead_approval_status,
    t.reviewer_approval_status,
    t.status
FROM tasks t
LEFT JOIN task_assignments ta ON ta.task_id = t.id
GROUP BY t.id, t.code, t.title, t.department_id, t.progress_pct,
         t.lead_approval_status, t.reviewer_approval_status, t.status;

-- 7. VIEW PHÂN QUYỀN DÀNH CHO TRƯỞNG BỘ MÔN (CHỈ LẤY CÔNG VIỆC THUỘC BỘ MÔN ĐÓ CỦA KHOA & % TIẾN ĐỘ CHUNG)
CREATE VIEW IF NOT EXISTS vw_dept_head_department_tasks AS
SELECT
    u_head.id AS dept_head_user_id,
    u_head.username AS dept_head_username,
    u_head.department_id AS managed_department_id,
    d.code AS department_code,
    d.name AS department_name,
    t.id AS task_id,
    t.code AS task_code,
    t.title AS task_title,
    t.progress_pct AS project_progress_pct,
    COUNT(ta.id) AS member_count,
    t.lead_approval_status,
    t.reviewer_approval_status,
    t.status
FROM users u_head
INNER JOIN tasks t ON t.department_id = u_head.department_id
INNER JOIN departments d ON d.id = t.department_id
LEFT JOIN task_assignments ta ON ta.task_id = t.id
WHERE u_head.rbac_role_code = 'DEPT_HEAD'
  AND u_head.department_id IS NOT NULL
GROUP BY u_head.id, u_head.username, u_head.department_id, d.code, d.name,
         t.id, t.code, t.title, t.progress_pct,
         t.lead_approval_status, t.reviewer_approval_status, t.status;`;

