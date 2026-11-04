"""Quản lý Phân quyền dựa trên Vai trò & Phạm vi dữ liệu (RBAC + Data Scope) trong CSDL."""
import json
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import (
    User, Department, RoleDefinition, Permission, RolePermission, UserPermissionScope,
    ROLE_ADMIN, ROLE_MANAGER, ROLE_LECTURER,
    SCOPE_SYSTEM, SCOPE_FACULTY, SCOPE_DEPARTMENT, SCOPE_SELF,
)

ROLE_DEFINITIONS = [
    {
        "code": ROLE_ADMIN,
        "name": "Quản trị viên Hệ thống (System Admin)",
        "hierarchy_level": 3,
        "default_scope": SCOPE_SYSTEM,
        "description": (
            "Toàn quyền quản trị hệ thống, quản lý danh bạ tài khoản, phân quyền, danh mục định mức, "
            "cấu hình và huấn luyện tiếp mô hình dự báo rủi ro trễ hạn TabPFN v2."
        ),
    },
    {
        "code": ROLE_MANAGER,
        "name": "Cán bộ Quản lý (Trưởng Khoa / Trưởng Bộ môn)",
        "hierarchy_level": 2,
        "default_scope": f"{SCOPE_FACULTY} / {SCOPE_DEPARTMENT}",
        "description": (
            "Quản lý công việc, phân công cá nhân/nhóm, phê duyệt gia hạn, nhập kế hoạch công tác năm, "
            "xem cảnh báo rủi ro trễ hạn AI và xuất báo cáo trong phạm vi quản lý (Toàn Khoa nếu department_id=NULL, "
            "hoặc cấp Bộ môn nếu gắn department_id)."
        ),
    },
    {
        "code": ROLE_LECTURER,
        "name": "Giảng viên (Lecturer)",
        "hierarchy_level": 1,
        "default_scope": SCOPE_SELF,
        "description": (
            "Xem danh sách công việc cá nhân và công việc nhóm được phân công, cập nhật tiến độ, "
            "đính kèm minh chứng, điều phối thành viên (khi là Trưởng nhóm), gửi yêu cầu gia hạn "
            "và theo dõi định mức giờ chuẩn cá nhân."
        ),
    },
]

PERMISSIONS_CATALOG = [
    (
        "USER_MANAGE",
        "Quản trị Hệ thống",
        "Quản lý tài khoản & phân quyền",
        "Thêm mới, cập nhật vai trò/bộ môn, khóa/mở khóa hoặc xóa tài khoản người dùng.",
    ),
    (
        "ACCOUNT_DIRECTORY_VIEW",
        "Quản trị Hệ thống",
        "Xem danh bạ tài khoản toàn hệ thống",
        "Tra cứu danh bạ tài khoản, trạng thái trực tuyến và phạm vi phân quyền của toàn bộ người dùng.",
    ),
    (
        "TASK_CREATE",
        "Quản lý Công việc",
        "Khởi tạo & giao công việc mới",
        "Tạo đầu việc mới (cấp Bộ môn, Khoa, Trường) và thiết lập hạn hoàn thành, mức ưu tiên, độ phức tạp.",
    ),
    (
        "TASK_ASSIGN_GROUP",
        "Quản lý Công việc",
        "Phân công việc nhóm & chỉ định Trưởng nhóm",
        "Phân công công việc cho nhiều giảng viên, chỉ định Trưởng nhóm (Lead) và Người kiểm tra duyệt (Reviewer).",
    ),
    (
        "TASK_VIEW_FACULTY",
        "Quản lý Công việc",
        "Giám sát công việc phạm vi Toàn Khoa",
        "Xem, lọc và giám sát tiến độ công việc của tất cả các Bộ môn trong Khoa CNTT.",
    ),
    (
        "TASK_VIEW_DEPARTMENT",
        "Quản lý Công việc",
        "Giám sát công việc phạm vi Bộ môn",
        "Xem, lọc và giám sát tiến độ công việc của các giảng viên thuộc Bộ môn phụ trách.",
    ),
    (
        "TASK_VIEW_SELF",
        "Quản lý Công việc",
        "Xem công việc cá nhân & nhóm tham gia",
        "Xem chi tiết các công việc được giao cho bản thân hoặc nhóm công tác mà giảng viên là thành viên.",
    ),
    (
        "TASK_UPDATE_PROGRESS",
        "Thực hiện Công việc",
        "Cập nhật tiến độ & nộp minh chứng",
        "Cập nhật phần trăm tiến độ (0-100%), ghi chú thực hiện và đính kèm tệp/liên kết minh chứng hoàn thành.",
    ),
    (
        "EXTENSION_REQUEST",
        "Gia hạn & Phê duyệt",
        "Gửi yêu cầu xin gia hạn thời gian",
        "Tạo đề xuất xin gia hạn hạn hoàn thành công việc kèm lý do giải trình khi gặp vướng mắc.",
    ),
    (
        "EXTENSION_APPROVE",
        "Gia hạn & Phê duyệt",
        "Phê duyệt / Từ chối yêu cầu gia hạn",
        "Xem xét lý do, đối chiếu cảnh báo rủi ro ML và quyết định Duyệt hoặc Từ chối gia hạn.",
    ),
    (
        "PLAN_IMPORT_EXPORT",
        "Kế hoạch & Định mức",
        "Nhập / Xuất kế hoạch công tác năm (Excel)",
        "Tải biểu mẫu chuẩn và nhập hàng loạt kế hoạch công việc năm học từ tệp Excel vào hệ thống.",
    ),
    (
        "NORM_CATALOG_MANAGE",
        "Kế hoạch & Định mức",
        "Quản lý danh mục công việc & định mức giờ chuẩn",
        "Cấu hình danh mục 35 loại công việc cấp Khoa, danh mục cấp Trường (FR-06) và khung giờ chuẩn quy đổi.",
    ),
    (
        "ML_RISK_VIEW",
        "Dự báo AI (TabPFN v2)",
        "Xem dự báo xác suất rủi ro trễ hạn & giải thích SHAP",
        "Xem xác suất trễ hạn, mức cảnh báo (Thấp/Trung bình/Cao) và các yếu tố tác động từ mô hình TabPFN v2.",
    ),
    (
        "ML_MODEL_RETRAIN",
        "Dự báo AI (TabPFN v2)",
        "Kiểm định rào chắn & Huấn luyện tiếp mô hình ML",
        "Kích hoạt quy trình học tiếp (Continual Learning) qua 3 rào chắn kiểm định và cập nhật kho phiên bản.",
    ),
    (
        "REPORT_EXPORT",
        "Thống kê & Báo cáo",
        "Xem thống kê KPI & Xuất báo cáo Excel",
        "Xem biểu đồ thống kê thực tế, đối chiếu dự báo - thực tế và xuất báo cáo tổng hợp ra Excel.",
    ),
]

ROLE_PERMISSION_MATRIX = {
    ROLE_ADMIN: [
        ("USER_MANAGE", "Toàn quyền thêm/sửa/khóa/xóa tài khoản trên toàn hệ thống"),
        ("ACCOUNT_DIRECTORY_VIEW", "Xem danh bạ toàn bộ 16+ tài khoản Quản trị, Quản lý và Giảng viên"),
        ("TASK_CREATE", "Khởi tạo công việc ở mọi cấp (Trường / Khoa / Bộ môn)"),
        ("TASK_ASSIGN_GROUP", "Phân công cá nhân hoặc nhóm cho mọi Bộ môn trong Khoa"),
        ("TASK_VIEW_FACULTY", "Truy cập không giới hạn toàn bộ công việc của 24 Bộ môn"),
        ("TASK_VIEW_DEPARTMENT", "Truy cập chi tiết từng Bộ môn K01..K24"),
        ("TASK_VIEW_SELF", "Xem công việc liên quan trực tiếp"),
        ("TASK_UPDATE_PROGRESS", "Can thiệp/cập nhật trạng thái và tiến độ khi cần hỗ trợ kỹ thuật"),
        ("EXTENSION_REQUEST", "Tạo phiếu gia hạn thử nghiệm hoặc hỗ trợ"),
        ("EXTENSION_APPROVE", "Phê duyệt hoặc từ chối mọi yêu cầu gia hạn trên hệ thống"),
        ("PLAN_IMPORT_EXPORT", "Nhập và xuất kế hoạch công tác năm cho mọi giảng viên"),
        ("NORM_CATALOG_MANAGE", "Thêm/sửa/xóa danh mục công việc cấp Trường và định mức giờ chuẩn"),
        ("ML_RISK_VIEW", "Xem toàn bộ lịch sử dự báo rủi ro trễ hạn TabPFN v2 và độ lệch chuẩn"),
        ("ML_MODEL_RETRAIN", "Chạy kiểm định 3 rào chắn và huấn luyện tiếp mô hình TabPFN v2"),
        ("REPORT_EXPORT", "Xuất báo cáo tổng hợp toàn Khoa CNTT"),
    ],
    ROLE_MANAGER: [
        ("USER_MANAGE", "Quản lý thông tin giảng viên trong phạm vi Khoa/Bộ môn"),
        ("TASK_CREATE", "Giao công việc mới trong phạm vi Toàn Khoa (Trưởng Khoa) hoặc Bộ môn (TBM)"),
        ("TASK_ASSIGN_GROUP", "Phân công việc nhóm, chỉ định Trưởng nhóm và Người duyệt"),
        ("TASK_VIEW_FACULTY", "Áp dụng khi department_id IS NULL (Trưởng Khoa / Phó Trưởng Khoa)"),
        ("TASK_VIEW_DEPARTMENT", "Áp dụng khi gắn department_id cụ thể (Trưởng/Phó Bộ môn K01..K04)"),
        ("TASK_VIEW_SELF", "Xem công việc do mình tạo, kiểm tra hoặc trực tiếp thực hiện"),
        ("TASK_UPDATE_PROGRESS", "Cập nhật tiến độ và duyệt minh chứng của thành viên nhóm"),
        ("EXTENSION_APPROVE", "Phê duyệt / Từ chối yêu cầu gia hạn của giảng viên thuộc phạm vi quản lý"),
        ("PLAN_IMPORT_EXPORT", "Nhập/xuất kế hoạch công việc năm học từ file Excel"),
        ("NORM_CATALOG_MANAGE", "Cấu hình danh mục công việc cấp Trường và ánh xạ giờ chuẩn"),
        ("ML_RISK_VIEW", "Xem cảnh báo sớm rủi ro trễ hạn TabPFN v2 khi giao việc và duyệt gia hạn"),
        ("ML_MODEL_RETRAIN", "Kích hoạt huấn luyện lại mô hình từ dữ liệu công việc hoàn thành thực tế"),
        ("REPORT_EXPORT", "Xem Dashboard quản lý và xuất báo cáo Excel theo phạm vi Khoa/Bộ môn"),
    ],
    ROLE_LECTURER: [
        ("TASK_VIEW_SELF", "Chỉ xem công việc được giao cho cá nhân hoặc nhóm mà mình tham gia (lecturer_scope=[user.id])"),
        ("TASK_UPDATE_PROGRESS", "Cập nhật % tiến độ, nộp minh chứng; nếu là Trưởng nhóm được xác nhận minh chứng thành viên"),
        ("EXTENSION_REQUEST", "Gửi yêu cầu xin gia hạn kèm lý do khi công việc chưa hoàn thành"),
        ("ML_RISK_VIEW", "Xem đối chiếu kết quả thực tế với dự báo AI sau khi công việc đã hoàn thành"),
        ("REPORT_EXPORT", "Xem thống kê giờ chuẩn quy đổi (Định mức 270 giờ chuẩn/năm) của cá nhân"),
    ],
}


def ensure_rbac_catalog(db: Session) -> None:
    """Đảm bảo các bảng roles, permissions, role_permissions và trigger ràng buộc role trong CSDL."""
    try:
        bind = db.get_bind()
        if bind and bind.dialect.name == "sqlite":
            db.execute(text("""
                CREATE TRIGGER IF NOT EXISTS trg_users_check_role_insert
                BEFORE INSERT ON users
                FOR EACH ROW
                WHEN NEW.role NOT IN ('admin', 'manager', 'lecturer')
                BEGIN
                    SELECT RAISE(ABORT, 'RBAC Constraint Violation: role must be admin, manager, or lecturer');
                END;
            """))
            db.execute(text("""
                CREATE TRIGGER IF NOT EXISTS trg_users_check_role_update
                BEFORE UPDATE OF role ON users
                FOR EACH ROW
                WHEN NEW.role NOT IN ('admin', 'manager', 'lecturer')
                BEGIN
                    SELECT RAISE(ABORT, 'RBAC Constraint Violation: role must be admin, manager, or lecturer');
                END;
            """))
    except Exception:
        pass

    # Chuẩn hóa tên hiển thị của 4 Bộ môn chính trong Khoa CNTT (giữ nguyên ml_name/code cho mô hình ML)
    main_dept_names = {
        1: "Bộ môn Công nghệ phần mềm (K01)",
        2: "Bộ môn Hệ thống thông tin (K02)",
        3: "Bộ môn Khoa học máy tính (K03)",
        4: "Bộ môn Mạng máy tính & ATTT (K04)",
    }
    for did, dname in main_dept_names.items():
        d_obj = db.get(Department, did)
        if d_obj and d_obj.name != dname:
            d_obj.name = dname
    db.flush()

    for r_data in ROLE_DEFINITIONS:
        role_obj = db.get(RoleDefinition, r_data["code"])
        if not role_obj:
            db.add(RoleDefinition(**r_data))
        else:
            role_obj.name = r_data["name"]
            role_obj.hierarchy_level = r_data["hierarchy_level"]
            role_obj.default_scope = r_data["default_scope"]
            role_obj.description = r_data["description"]
    db.flush()

    for code, module, name, desc in PERMISSIONS_CATALOG:
        perm_obj = db.get(Permission, code)
        if not perm_obj:
            db.add(Permission(code=code, module=module, name=name, description=desc))
        else:
            perm_obj.module = module
            perm_obj.name = name
            perm_obj.description = desc
    db.flush()

    for role_code, items in ROLE_PERMISSION_MATRIX.items():
        for perm_code, note in items:
            exists = (
                db.query(RolePermission)
                .filter_by(role_code=role_code, permission_code=perm_code)
                .first()
            )
            if not exists:
                db.add(
                    RolePermission(
                        role_code=role_code,
                        permission_code=perm_code,
                        constraint_note=note,
                    )
                )
            else:
                exists.constraint_note = note
    db.flush()


def sync_user_permission_scope(db: Session, user: User) -> UserPermissionScope:
    """Tính toán và lưu tường minh quyền hạn + ràng buộc phạm vi của 1 tài khoản vào bảng user_permission_scopes."""
    dept = db.get(Department, user.department_id) if user.department_id else None
    dept_label = dept.name if dept else "Toàn Khoa CNTT (24 Bộ môn)"

    if user.role == ROLE_ADMIN:
        scope_level = SCOPE_SYSTEM
        scope_desc = "Toàn hệ thống (System-wide) — Quản trị tài khoản, cấu hình danh mục & MLOps"
        perms = [p[0] for p in ROLE_PERMISSION_MATRIX[ROLE_ADMIN]]
        rule_sql = "ALL_RECORDS (lecturer_scope = None, role = 'admin')"
    elif user.role == ROLE_MANAGER:
        if user.department_id is None:
            scope_level = SCOPE_FACULTY
            scope_desc = "Cấp Toàn Khoa CNTT — Giám sát, giao việc & duyệt gia hạn tất cả các Bộ môn"
            perms = [
                p[0] for p in ROLE_PERMISSION_MATRIX[ROLE_MANAGER]
                if p[0] != "TASK_VIEW_DEPARTMENT"
            ]
            rule_sql = "FACULTY_WIDE (lecturer_scope = None, department_id IS NULL)"
        else:
            scope_level = SCOPE_DEPARTMENT
            scope_desc = f"Cấp Bộ môn ({dept_label}) — Quản lý giảng viên & công việc thuộc Bộ môn"
            perms = [
                p[0] for p in ROLE_PERMISSION_MATRIX[ROLE_MANAGER]
                if p[0] != "TASK_VIEW_FACULTY"
            ]
            rule_sql = f"DEPARTMENT_ONLY (department_id = {user.department_id} [{dept.code if dept else ''}])"
    else:
        scope_level = SCOPE_SELF
        scope_desc = f"Cá nhân & Nhóm công tác được giao ({dept_label})"
        perms = [p[0] for p in ROLE_PERMISSION_MATRIX[ROLE_LECTURER]]
        rule_sql = f"SELF_OR_GROUP_MEMBER (lecturer_id = {user.id} OR lead_lecturer_id = {user.id})"

    is_admin_or_mgr = user.role in (ROLE_ADMIN, ROLE_MANAGER)
    scope_row = db.get(UserPermissionScope, user.id)
    if not scope_row:
        scope_row = UserPermissionScope(user_id=user.id, username=user.username, role_code=user.role)
        db.add(scope_row)

    scope_row.username = user.username
    scope_row.role_code = user.role
    scope_row.scope_level = scope_level
    scope_row.department_id = user.department_id
    scope_row.scope_description = scope_desc
    scope_row.can_manage_users = is_admin_or_mgr
    scope_row.can_create_task = is_admin_or_mgr
    scope_row.can_assign_task = is_admin_or_mgr
    scope_row.can_approve_extension = is_admin_or_mgr
    scope_row.can_manage_norm_catalog = is_admin_or_mgr
    scope_row.can_import_plan = is_admin_or_mgr
    scope_row.can_view_ml_risk = True
    scope_row.can_retrain_ml_model = is_admin_or_mgr
    scope_row.can_export_report = True
    scope_row.can_update_own_progress = True
    scope_row.can_request_extension = True
    scope_row.granted_permissions_json = json.dumps(perms, ensure_ascii=False)
    scope_row.access_constraint_rule = rule_sql
    scope_row.updated_at = datetime.now()
    db.flush()
    return scope_row


def sync_all_users_rbac(db: Session) -> dict:
    """Đồng bộ toàn bộ bảng phân quyền và quyền của tất cả tài khoản hiện có trong CSDL."""
    ensure_rbac_catalog(db)
    users = db.query(User).order_by(User.id.asc()).all()
    for u in users:
        sync_user_permission_scope(db, u)
    db.commit()
    return {
        "roles_count": db.query(RoleDefinition).count(),
        "permissions_count": db.query(Permission).count(),
        "role_permissions_count": db.query(RolePermission).count(),
        "user_permission_scopes_count": db.query(UserPermissionScope).count(),
    }
