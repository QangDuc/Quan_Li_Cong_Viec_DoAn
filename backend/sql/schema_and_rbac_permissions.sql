-- =============================================================================
-- HỆ THỐNG QUẢN LÝ CÔNG VIỆC & TỐI ƯU PHÂN CÔNG BẰNG HỌC MÁY TẠI KHOA CNTT (HUIT)
-- FILE SQL: THIẾT KẾ CƠ SỞ DỮ LIỆU, KHÓA CHÍNH, KHÓA NGOẠI, TRIGGER TỰ ĐỘNG TÍNH
--           TIẾN ĐỘ DỰ ÁN TỪ 3 THÀNH VIÊN & PHÂN QUYỀN RBAC 5 CẤP RÕ RÀNG
-- =============================================================================
-- Quy trình nghiệp vụ 5 cấp phân quyền:
--   1. GIẢNG VIÊN (MEMBER - role='lecturer'):
--      Tự cập nhật % tiến độ cá nhân (progress_pct) và minh chứng phần việc được giao.
--   2. TRƯỞNG NHÓM / NGƯỜI PHỤ TRÁCH CHÍNH (GROUP_LEAD - is_lead=1 / lead_lecturer_id):
--      Không nhập thay % của thành viên khác; chỉ phê duyệt (Đã duyệt / Yêu cầu sửa)
--      tiến độ từng thành viên và gửi quyết định tổng hợp của nhóm lên hệ thống.
--   3. HỆ THỐNG (SYSTEM AUTO-CALCULATION TRIGGER):
--      Tự động tính toán % tiến độ của toàn dự án/công việc (tasks.progress_pct)
--      dựa trên trung bình cộng tiến độ của 3 thành viên trong nhóm.
--   4. NGƯỜI KIỂM TRA (REVIEWER - reviewer_id / role='reviewer'):
--      Quan sát được tiến độ từng thành viên trong nhóm và phê duyệt quyết định
--      của Trưởng nhóm (Đã phê duyệt quyết định Trưởng nhóm / Yêu cầu bổ sung).
--   5. TRƯỞNG BỘ MÔN (DEPT_HEAD) & TRƯỞNG KHOA (DEAN):
--      Cấp quản lý vĩ mô trên Người kiểm tra; không cần soi xét từng phần trăm
--      tiến độ của từng thành viên trong bảng công việc, chỉ theo dõi phần trăm
--      tiến độ chung của công việc/dự án (tasks.progress_pct).
-- =============================================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- 1. BẢNG BỘ MÔN (DEPARTMENTS)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    head_lecturer_id INTEGER NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 2. BẢNG VAI TRÒ HỆ THỐNG & QUYỀN HẠN CHI TIẾT (RBAC TABLES)
-- -----------------------------------------------------------------------------
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
    granted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_code, permission_code),
    CONSTRAINT fk_rp_role
        FOREIGN KEY (role_code) REFERENCES rbac_roles(role_code)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_rp_permission
        FOREIGN KEY (permission_code) REFERENCES rbac_permissions(permission_code)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- -----------------------------------------------------------------------------
-- 3. BẢNG NGƯỜI DÙNG / TÀI KHOẢN GIẢNG VIÊN & QUẢN LÝ (USERS)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) NULL UNIQUE,
    role VARCHAR(32) NOT NULL DEFAULT 'lecturer'
        CHECK (role IN ('lecturer', 'reviewer', 'manager', 'admin')),
    rbac_role_code VARCHAR(50) NOT NULL DEFAULT 'LECTURER_MEMBER',
    department_id INTEGER NULL,
    lecturer_code VARCHAR(32) NULL UNIQUE,
    degree VARCHAR(64) NOT NULL DEFAULT 'Thạc sĩ',
    academic_rank VARCHAR(64) NOT NULL DEFAULT 'Giảng viên',
    management_role VARCHAR(64) NOT NULL DEFAULT 'Không',
    teaching_hours_semester REAL NOT NULL DEFAULT 135.0 CHECK (teaching_hours_semester >= 0),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    last_login_at DATETIME NULL,
    last_active_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_department
        FOREIGN KEY (department_id) REFERENCES departments(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_users_rbac_role
        FOREIGN KEY (rbac_role_code) REFERENCES rbac_roles(role_code)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_users_role_dept ON users(role, department_id);
CREATE INDEX IF NOT EXISTS idx_users_rbac_role ON users(rbac_role_code);

-- -----------------------------------------------------------------------------
-- 4. BẢNG LOẠI CÔNG VIỆC & DANH MỤC GIỜ CHUẨN (TASK_TYPES & SCHOOL_CATALOG)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS task_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_group VARCHAR(120) NOT NULL,
    name VARCHAR(255) NOT NULL,
    default_complexity VARCHAR(32) NOT NULL DEFAULT 'Trung bình',
    expected_duration_days INTEGER NOT NULL DEFAULT 14 CHECK (expected_duration_days > 0),
    conversion_hours REAL NOT NULL DEFAULT 20.0 CHECK (conversion_hours >= 0)
);

CREATE TABLE IF NOT EXISTS school_task_catalog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    conversion_hours REAL NOT NULL DEFAULT 15.0 CHECK (conversion_hours >= 0),
    task_type_id INTEGER NULL,
    note TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_catalog_task_type
        FOREIGN KEY (task_type_id) REFERENCES task_types(id)
        ON DELETE SET NULL ON UPDATE CASCADE
);

-- -----------------------------------------------------------------------------
-- 5. BẢNG CÔNG VIỆC / DỰ ÁN (TASKS)
-- Lưu tiến độ chung của dự án (progress_pct) được tự động tính toán từ 3 thành viên,
-- trạng thái phê duyệt của Trưởng nhóm và trạng thái phê duyệt của Người kiểm tra.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code VARCHAR(32) NOT NULL UNIQUE,
    title VARCHAR(300) NOT NULL,
    description TEXT NULL,
    task_type_id INTEGER NOT NULL,
    school_catalog_id INTEGER NULL,
    department_id INTEGER NULL,
    scale VARCHAR(50) NOT NULL DEFAULT 'quy mô chuẩn',
    priority VARCHAR(32) NOT NULL DEFAULT 'Trung bình'
        CHECK (priority IN ('Thấp', 'Trung bình', 'Cao', 'Khẩn cấp')),
    complexity VARCHAR(32) NOT NULL DEFAULT 'Trung bình'
        CHECK (complexity IN ('Thấp', 'Trung bình', 'Cao', 'Khẩn cấp')),
    assignment_mode VARCHAR(32) NOT NULL DEFAULT 'Group'
        CHECK (assignment_mode IN ('Individual', 'Group')),
    status VARCHAR(50) NOT NULL DEFAULT 'Mới giao'
        CHECK (status IN ('Mới giao', 'Đang thực hiện', 'Chờ duyệt hoàn thành', 'Hoàn thành', 'Quá hạn')),
    -- Tiến độ chung của dự án (%) được hệ thống tự động tính từ trung bình 3 thành viên
    progress_pct INTEGER NOT NULL DEFAULT 0
        CHECK (progress_pct BETWEEN 0 AND 100),
    conversion_hours REAL NOT NULL DEFAULT 0.0 CHECK (conversion_hours >= 0),
    assigned_at DATE NOT NULL,
    original_deadline DATE NOT NULL,
    current_deadline DATE NOT NULL,
    completed_at DATETIME NULL,
    academic_year VARCHAR(20) NOT NULL DEFAULT '2026-2027',
    semester VARCHAR(16) NOT NULL DEFAULT 'HK1',

    -- Phân công các vai trò điều phối trên dự án
    created_by INTEGER NULL,
    lead_lecturer_id INTEGER NOT NULL, -- Trưởng nhóm (Người phụ trách chính)
    reviewer_id INTEGER NULL,          -- Người kiểm tra (Phê duyệt quyết định Trưởng nhóm)

    -- Trạng thái phê duyệt của Trưởng nhóm (Người phụ trách chính)
    lead_approval_status VARCHAR(64) NOT NULL DEFAULT 'Chờ Trưởng nhóm duyệt'
        CHECK (lead_approval_status IN (
            'Chờ Trưởng nhóm duyệt',
            'Đã duyệt & Trình Người kiểm tra',
            'Yêu cầu thành viên chỉnh sửa'
        )),
    lead_decision_note TEXT NULL,
    lead_submitted_at DATETIME NULL,

    -- Trạng thái phê duyệt của Người kiểm tra đối với quyết định của Trưởng nhóm
    reviewer_approval_status VARCHAR(64) NOT NULL DEFAULT 'Chờ Người kiểm tra duyệt'
        CHECK (reviewer_approval_status IN (
            'Chờ Người kiểm tra duyệt',
            'Đã phê duyệt quyết định Trưởng nhóm',
            'Yêu cầu Trưởng nhóm rà soát lại'
        )),
    reviewer_decision_note TEXT NULL,
    reviewer_approved_at DATETIME NULL,

    CONSTRAINT fk_tasks_task_type
        FOREIGN KEY (task_type_id) REFERENCES task_types(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_tasks_school_catalog
        FOREIGN KEY (school_catalog_id) REFERENCES school_task_catalog(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_tasks_department
        FOREIGN KEY (department_id) REFERENCES departments(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_tasks_created_by
        FOREIGN KEY (created_by) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_tasks_lead_lecturer
        FOREIGN KEY (lead_lecturer_id) REFERENCES users(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_tasks_reviewer
        FOREIGN KEY (reviewer_id) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tasks_lead_lecturer ON tasks(lead_lecturer_id);
CREATE INDEX IF NOT EXISTS idx_tasks_reviewer ON tasks(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_tasks_dept_status ON tasks(department_id, status);

-- -----------------------------------------------------------------------------
-- 6. BẢNG PHÂN CÔNG THÀNH VIÊN NHÓM (TASK_ASSIGNMENTS)
-- Mỗi giảng viên trong nhóm (3 thành viên) tự cập nhật progress_pct của mình.
-- Trưởng nhóm phê duyệt trên từng dòng phân công (lead_approval_status).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS task_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    lecturer_id INTEGER NOT NULL,
    is_lead BOOLEAN NOT NULL DEFAULT 0,
    member_task_note TEXT NULL,

    -- Giảng viên tự cập nhật tiến độ cá nhân (0% -> 100%)
    progress_pct INTEGER NOT NULL DEFAULT 0
        CHECK (progress_pct BETWEEN 0 AND 100),
    self_updated_at DATETIME NULL,

    -- Minh chứng cá nhân của thành viên
    latest_evidence_name VARCHAR(255) NULL,
    latest_evidence_url VARCHAR(500) NULL,
    member_evidence_status VARCHAR(64) NOT NULL DEFAULT 'Chưa nộp'
        CHECK (member_evidence_status IN (
            'Chưa nộp',
            'Đã gửi Trưởng nhóm',
            'Đã xác nhận',
            'Cần bổ sung',
            'Minh chứng chính thức của Nhóm'
        )),

    -- Quyết định phê duyệt của Trưởng nhóm đối với tiến độ thành viên
    lead_approval_status VARCHAR(64) NOT NULL DEFAULT 'Chờ Trưởng nhóm duyệt'
        CHECK (lead_approval_status IN (
            'Chờ Trưởng nhóm duyệt',
            'Trưởng nhóm đã duyệt',
            'Yêu cầu chỉnh sửa'
        )),
    lead_approved_by INTEGER NULL,
    lead_approved_at DATETIME NULL,
    review_feedback TEXT NULL,

    status VARCHAR(50) NOT NULL DEFAULT 'Mới giao'
        CHECK (status IN ('Mới giao', 'Đang thực hiện', 'Hoàn thành', 'Quá hạn')),
    completed_at DATETIME NULL,
    is_late BOOLEAN NOT NULL DEFAULT 0,
    delay_days INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT uq_task_lecturer UNIQUE (task_id, lecturer_id),
    CONSTRAINT fk_assign_task
        FOREIGN KEY (task_id) REFERENCES tasks(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_assign_lecturer
        FOREIGN KEY (lecturer_id) REFERENCES users(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_assign_lead_approver
        FOREIGN KEY (lead_approved_by) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_assign_task_id ON task_assignments(task_id);
CREATE INDEX IF NOT EXISTS idx_assign_lecturer_id ON task_assignments(lecturer_id);

-- -----------------------------------------------------------------------------
-- 7. BẢNG NHẬT KÝ CẬP NHẬT TIẾN ĐỘ & LỊCH SỬ PHÊ DUYỆT ĐA CẤP (TASK_APPROVAL_LOGS)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS task_approval_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    assignment_id INTEGER NULL,
    actor_user_id INTEGER NOT NULL,
    actor_role VARCHAR(50) NOT NULL
        CHECK (actor_role IN ('LECTURER_MEMBER', 'GROUP_LEAD', 'TASK_REVIEWER', 'DEPT_HEAD', 'DEAN', 'SYSTEM')),
    action_type VARCHAR(64) NOT NULL
        CHECK (action_type IN (
            'MEMBER_SELF_UPDATE_PROGRESS',
            'LEAD_APPROVE_MEMBER',
            'LEAD_REQUEST_REVISION',
            'LEAD_SUBMIT_GROUP_DECISION',
            'SYSTEM_AUTO_CALC_PROJECT_PROGRESS',
            'REVIEWER_APPROVE_LEAD_DECISION',
            'REVIEWER_REJECT_LEAD_DECISION'
        )),
    member_progress_pct INTEGER NULL CHECK (member_progress_pct BETWEEN 0 AND 100),
    calculated_project_pct INTEGER NULL CHECK (calculated_project_pct BETWEEN 0 AND 100),
    approval_status VARCHAR(64) NOT NULL,
    note TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_log_task
        FOREIGN KEY (task_id) REFERENCES tasks(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_log_assignment
        FOREIGN KEY (assignment_id) REFERENCES task_assignments(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_log_actor
        FOREIGN KEY (actor_user_id) REFERENCES users(id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_approval_logs_task ON task_approval_logs(task_id, created_at DESC);

-- -----------------------------------------------------------------------------
-- 8. TRIGGER HỆ THỐNG TỰ ĐỘNG TÍNH TOÁN % TIẾN ĐỘ DỰ ÁN DỰA TRÊN 3 THÀNH VIÊN
-- Khi giảng viên tự cập nhật tiến độ hoặc Trưởng nhóm phê duyệt tiến độ thành viên,
-- hệ thống tự động tính trung bình cộng progress_pct của tất cả thành viên trong nhóm
-- (ví dụ: ROUND((member1 + member2 + member3) / 3.0)) và cập nhật vào tasks.progress_pct.
-- -----------------------------------------------------------------------------
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
    ),
    status = CASE
        WHEN (
            SELECT CAST(ROUND(AVG(CAST(ta.progress_pct AS REAL)), 0) AS INTEGER)
            FROM task_assignments ta
            WHERE ta.task_id = NEW.task_id
        ) >= 100 AND reviewer_approval_status = 'Đã phê duyệt quyết định Trưởng nhóm'
            THEN 'Hoàn thành'
        WHEN (
            SELECT CAST(ROUND(AVG(CAST(ta.progress_pct AS REAL)), 0) AS INTEGER)
            FROM task_assignments ta
            WHERE ta.task_id = NEW.task_id
        ) > 0
            THEN 'Đang thực hiện'
        ELSE status
    END
    WHERE id = NEW.task_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_auto_calc_task_progress_on_insert
AFTER INSERT ON task_assignments
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

-- -----------------------------------------------------------------------------
-- 9. KHỞI TẠO DỮ LIỆU PHÂN QUYỀN RBAC 5 CẤP RÕ RÀNG
-- -----------------------------------------------------------------------------
INSERT OR IGNORE INTO rbac_roles (role_code, role_name, hierarchy_level, can_view_member_detail, can_view_project_summary, description) VALUES
('LECTURER_MEMBER', 'Giảng viên (Thành viên Nhóm)', 1, 1, 1, 'Tự cập nhật % tiến độ cá nhân và nộp file minh chứng phần việc được giao.'),
('GROUP_LEAD',      'Trưởng nhóm (Người phụ trách chính)', 2, 1, 1, 'Phê duyệt tiến độ do các thành viên tự cập nhật và gửi lên hệ thống để tự động tính % tiến độ dự án từ 3 thành viên.'),
('TASK_REVIEWER',   'Người kiểm tra công việc', 3, 1, 1, 'Quan sát chi tiết tiến độ từng thành viên trong nhóm và phê duyệt quyết định của Trưởng nhóm.'),
('DEPT_HEAD',       'Trưởng Bộ môn', 4, 0, 1, 'Quản lý cấp Bộ môn: chỉ quản lý được các công việc thuộc Bộ môn đó của Khoa (tasks.department_id = users.department_id) và chỉ cần xem % tiến độ tổng thể của công việc.'),
('DEAN',            'Trưởng Khoa', 5, 0, 1, 'Quản lý cấp Khoa: quản lý toàn bộ các Bộ môn của Khoa (users.department_id IS NULL) và chỉ cần xem % tiến độ tổng thể của công việc.'),
('SYSTEM_ADMIN',    'Quản trị viên Hệ thống', 6, 1, 1, 'Quản trị toàn diện tài khoản, phân quyền RBAC và cấu hình hệ thống.');

INSERT OR IGNORE INTO rbac_permissions (permission_code, permission_name, module_name, description) VALUES
('MEMBER_SELF_UPDATE_PROGRESS',   'Giảng viên tự cập nhật % tiến độ cá nhân', 'PROGRESS', 'Cho phép thành viên nhóm tự kéo thanh % tiến độ của chính mình và đính kèm minh chứng.'),
('LEAD_APPROVE_MEMBER_PROGRESS',  'Trưởng nhóm phê duyệt tiến độ thành viên', 'APPROVAL', 'Trưởng nhóm duyệt hoặc yêu cầu chỉnh sửa đối với tiến độ thành viên đã tự cập nhật.'),
('LEAD_SUBMIT_GROUP_TO_SYSTEM',   'Trưởng nhóm gửi quyết định lên hệ thống',  'APPROVAL', 'Gửi tiến độ nhóm đã duyệt để hệ thống tự tính % dự án từ 3 người và trình Người kiểm tra.'),
('REVIEWER_INSPECT_MEMBER_PCT',   'Người kiểm tra quan sát % từng thành viên', 'REVIEW',   'Hiển thị chi tiết % tiến độ và minh chứng của từng thành viên trong nhóm cho Người kiểm tra.'),
('REVIEWER_APPROVE_LEAD_DECISION','Người kiểm tra phê duyệt quyết định Trưởng nhóm', 'REVIEW', 'Người kiểm tra xác nhận hoặc trả lại quyết định tổng hợp tiến độ của Trưởng nhóm.'),
('MANAGER_VIEW_PROJECT_SUMMARY',  'Trưởng Bộ môn / Trưởng Khoa xem % tổng dự án', 'OVERSIGHT', 'Chỉ hiển thị thanh % tiến độ chung của công việc/dự án, ẩn chi tiết % từng thành viên để tránh quá tải thông tin.'),
('DEPT_HEAD_MANAGE_OWN_DEPT_ONLY','Trưởng Bộ môn chỉ quản lý công việc thuộc Bộ môn mình', 'DEPARTMENT_SCOPE', 'Ràng buộc dữ liệu cấp Bộ môn: Trưởng Bộ môn chỉ được xem, giao việc, duyệt gia hạn và quản lý các công việc có tasks.department_id = users.department_id.'),
('DEAN_MANAGE_ALL_FACULTY_DEPTS', 'Trưởng Khoa quản lý công việc tất cả Bộ môn thuộc Khoa', 'FACULTY_SCOPE', 'Phạm vi toàn Khoa CNTT: Trưởng Khoa giám sát tiến độ chung của tất cả các Bộ môn (K01..K04) trong Khoa.');

INSERT OR IGNORE INTO rbac_role_permissions (role_code, permission_code) VALUES
-- 1. Giảng viên (Thành viên)
('LECTURER_MEMBER', 'MEMBER_SELF_UPDATE_PROGRESS'),
-- 2. Trưởng nhóm (Người phụ trách chính)
('GROUP_LEAD', 'MEMBER_SELF_UPDATE_PROGRESS'),
('GROUP_LEAD', 'LEAD_APPROVE_MEMBER_PROGRESS'),
('GROUP_LEAD', 'LEAD_SUBMIT_GROUP_TO_SYSTEM'),
-- 3. Người kiểm tra
('TASK_REVIEWER', 'REVIEWER_INSPECT_MEMBER_PCT'),
('TASK_REVIEWER', 'REVIEWER_APPROVE_LEAD_DECISION'),
-- 4. Trưởng Bộ môn (Chỉ quản lý Bộ môn mình + Chỉ xem % chung công việc)
('DEPT_HEAD', 'MANAGER_VIEW_PROJECT_SUMMARY'),
('DEPT_HEAD', 'DEPT_HEAD_MANAGE_OWN_DEPT_ONLY'),
-- 5. Trưởng Khoa (Quản lý toàn Khoa + Chỉ xem % chung công việc)
('DEAN', 'MANAGER_VIEW_PROJECT_SUMMARY'),
('DEAN', 'DEAN_MANAGE_ALL_FACULTY_DEPTS'),
-- 6. Admin
('SYSTEM_ADMIN', 'MEMBER_SELF_UPDATE_PROGRESS'),
('SYSTEM_ADMIN', 'LEAD_APPROVE_MEMBER_PROGRESS'),
('SYSTEM_ADMIN', 'LEAD_SUBMIT_GROUP_TO_SYSTEM'),
('SYSTEM_ADMIN', 'REVIEWER_INSPECT_MEMBER_PCT'),
('SYSTEM_ADMIN', 'REVIEWER_APPROVE_LEAD_DECISION'),
('SYSTEM_ADMIN', 'MANAGER_VIEW_PROJECT_SUMMARY'),
('SYSTEM_ADMIN', 'DEAN_MANAGE_ALL_FACULTY_DEPTS');

-- -----------------------------------------------------------------------------
-- 10. TRIGGER KIỂM SOÁT PHẠM VI BỘ MÔN CỦA TRƯỞNG BỘ MÔN (DEPT_HEAD SCOPE)
-- Trưởng Bộ môn chỉ được phép tạo hoặc tác động lên công việc thuộc đúng Bộ môn
-- mà mình phụ trách (tasks.department_id = users.department_id).
-- -----------------------------------------------------------------------------
CREATE TRIGGER IF NOT EXISTS trg_enforce_dept_head_task_insert
BEFORE INSERT ON tasks
FOR EACH ROW
WHEN NEW.created_by IS NOT NULL
  AND (SELECT rbac_role_code FROM users WHERE id = NEW.created_by) = 'DEPT_HEAD'
  AND NEW.department_id IS NOT NULL
  AND NEW.department_id != (SELECT department_id FROM users WHERE id = NEW.created_by)
BEGIN
    SELECT RAISE(ABORT, 'RBAC Department Scope Violation: Trưởng Bộ môn chỉ được quản lý và giao các công việc thuộc Bộ môn của mình trong Khoa!');
END;

CREATE TRIGGER IF NOT EXISTS trg_check_dept_head_scope_on_approval
BEFORE INSERT ON task_approval_logs
FOR EACH ROW
WHEN NEW.actor_role = 'DEPT_HEAD'
  AND (SELECT department_id FROM tasks WHERE id = NEW.task_id) != (SELECT department_id FROM users WHERE id = NEW.actor_user_id)
BEGIN
    SELECT RAISE(ABORT, 'RBAC Department Scope Violation: Trưởng Bộ môn không được phép phê duyệt hoặc can thiệp công việc của Bộ môn khác!');
END;

-- -----------------------------------------------------------------------------
-- 11. VIEW PHÂN QUYỀN HIỂN THỊ DÀNH CHO TRƯỞNG BỘ MÔN & TRƯỞNG KHOA
-- - vw_manager_project_progress_summary: View tổng hợp % tiến độ chung cho cấp Quản lý.
-- - vw_dept_head_department_tasks: Ràng buộc Trưởng Bộ môn chỉ truy vấn được các công việc
--   thuộc đúng Bộ môn mình quản lý (t.department_id = u_head.department_id).
-- -----------------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS vw_manager_project_progress_summary AS
SELECT
    t.id AS task_id,
    t.code AS task_code,
    t.title AS task_title,
    t.department_id,
    d.code AS department_code,
    d.name AS department_name,
    t.assignment_mode,
    t.status AS task_status,
    t.progress_pct AS project_progress_pct,
    COUNT(ta.id) AS member_count,
    SUM(CASE WHEN ta.lead_approval_status = 'Trưởng nhóm đã duyệt' THEN 1 ELSE 0 END) AS approved_member_count,
    t.lead_lecturer_id,
    t.lead_approval_status,
    t.reviewer_id,
    t.reviewer_approval_status,
    t.original_deadline,
    t.current_deadline
FROM tasks t
LEFT JOIN departments d ON d.id = t.department_id
LEFT JOIN task_assignments ta ON ta.task_id = t.id
GROUP BY
    t.id, t.code, t.title, t.department_id, d.code, d.name, t.assignment_mode,
    t.status, t.progress_pct, t.lead_lecturer_id, t.lead_approval_status,
    t.reviewer_id, t.reviewer_approval_status, t.original_deadline, t.current_deadline;

CREATE VIEW IF NOT EXISTS vw_dept_head_department_tasks AS
SELECT
    u_head.id AS dept_head_user_id,
    u_head.username AS dept_head_username,
    u_head.department_id AS managed_department_id,
    v.*
FROM users u_head
INNER JOIN vw_manager_project_progress_summary v
    ON v.department_id = u_head.department_id
WHERE u_head.rbac_role_code = 'DEPT_HEAD'
  AND u_head.department_id IS NOT NULL;
