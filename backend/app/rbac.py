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
        "TASK_VIEW",
        "tasks",
        "Xem danh sách và chi tiết công việc theo phạm vi",
        "Xem danh sách và chi tiết công việc theo phạm vi dữ liệu (SYSTEM / FACULTY / DEPARTMENT / SELF).",
    ),
    (
        "TASK_CREATE",
        "tasks",
        "Tạo đầu việc mới trong Khoa/Bộ môn",
        "Khởi tạo đầu việc mới trong phạm vi Toàn Khoa (Admin/Trưởng Khoa) hoặc cấp Bộ môn (Trưởng Bộ môn).",
    ),
    (
        "TASK_UPDATE",
        "tasks",
        "Chỉnh sửa thông tin công việc và hạn chót",
        "Cập nhật thông tin công việc, mức ưu tiên, độ phức tạp và thời hạn hoàn thành.",
    ),
    (
        "TASK_DELETE",
        "tasks",
        "Xóa hoặc hủy bỏ công việc",
        "Xóa hoặc hủy bỏ công việc thuộc thẩm quyền quản lý.",
    ),
    (
        "TASK_ASSIGN",
        "tasks",
        "Phân công giảng viên và chỉ định Trưởng nhóm",
        "Phân công giảng viên thực hiện cá nhân hoặc theo nhóm và chỉ định duy nhất 1 Trưởng nhóm phụ trách chính.",
    ),
    (
        "TASK_UPDATE_PROGRESS",
        "tasks",
        "Cập nhật tiến độ, nộp minh chứng và điều phối nhóm",
        "Giảng viên tự cập nhật % tiến độ cá nhân, nộp minh chứng; Trưởng nhóm duyệt nội bộ để hệ thống tự tính % tiến độ dự án.",
    ),
    (
        "TASK_APPROVE",
        "tasks",
        "Nghiệm thu hoàn thành hoặc duyệt gia hạn",
        "Người kiểm tra / Cấp quản lý nghiệm thu quyết định của Trưởng nhóm hoặc phê duyệt yêu cầu gia hạn.",
    ),
    (
        "TASK_COMMENT",
        "tasks",
        "Gửi ghi chú trao đổi và xem nhật ký tiến độ",
        "Gửi nhận xét, thông báo nhắc nhở thiếu sót và tra cứu nhật ký cập nhật tiến độ.",
    ),
    (
        "PLAN_VIEW",
        "plans",
        "Xem kế hoạch năm học và định mức 270 giờ chuẩn",
        "Tra cứu kế hoạch công tác năm học và theo dõi lũy kế định mức 270 giờ chuẩn theo Thông tư 20/2020/TT-BGDĐT.",
    ),
    (
        "PLAN_MANAGE",
        "plans",
        "Quản lý kế hoạch năm, xuất/nhập báo cáo Excel",
        "Tải biểu mẫu chuẩn 16 cột, nhập hàng loạt kế hoạch năm từ tệp Excel và xuất báo cáo tổng hợp.",
    ),
    (
        "USER_VIEW",
        "users",
        "Xem danh sách giảng viên và hồ sơ công tác 1 năm",
        "Xem danh sách cán bộ giảng viên và tra cứu hồ sơ đánh giá công tác 1 năm.",
    ),
    (
        "USER_MANAGE",
        "users",
        "Thêm/sửa/khóa tài khoản và cấu hình phân quyền RBAC",
        "Đặc quyền Quản trị viên Hệ thống (Admin): Thêm mới, chỉnh sửa, khóa/mở khóa, xóa tài khoản và cấu hình phân quyền RBAC.",
    ),
    (
        "DEPT_MANAGE",
        "departments",
        "Quản lý danh mục Bộ môn và cấu hình hệ thống",
        "Đặc quyền Quản trị viên Hệ thống (Admin): Quản lý danh mục các Bộ môn chuyên môn, danh mục cấp Trường và cấu hình hệ thống.",
    ),
    (
        "ML_PREDICT_VIEW",
        "ml",
        "Xem dự báo xác suất trễ hạn và giải thích TabPFN v2",
        "Xem xác suất rủi ro trễ hạn, mức cảnh báo (Thấp/Trung bình/Cao) và giải thích nhân quả từ mô hình TabPFN v2.",
    ),
    (
        "ML_RECOMMEND_USE",
        "ml",
        "Sử dụng gợi ý phân công AI & Quản trị mô hình MLOps",
        "Sử dụng bảng xếp hạng gợi ý phân công AI, đề xuất Trưởng nhóm và vận hành tái huấn luyện định kỳ MLOps.",
    ),
]

# Ma trận 32 ánh xạ quyền chuẩn Bảng 3.4 Khóa luận (Admin: 15 quyền, Manager: 12 quyền, Lecturer: 5 quyền)
ROLE_PERMISSION_MATRIX = {
    ROLE_ADMIN: [
        ("TASK_VIEW", "Xem danh sách và chi tiết toàn bộ công việc trên hệ thống (SYSTEM)"),
        ("TASK_CREATE", "Tạo đầu việc mới ở mọi cấp Trường / Khoa / Bộ môn"),
        ("TASK_UPDATE", "Chỉnh sửa thông tin công việc và hạn chót trên toàn hệ thống"),
        ("TASK_DELETE", "Xóa hoặc hủy bỏ công việc trên toàn hệ thống"),
        ("TASK_ASSIGN", "Phân công giảng viên và chỉ định Trưởng nhóm cho mọi Bộ môn"),
        ("TASK_UPDATE_PROGRESS", "Can thiệp cập nhật tiến độ, nộp minh chứng và điều phối nhóm"),
        ("TASK_APPROVE", "Nghiệm thu hoàn thành hoặc phê duyệt mọi yêu cầu gia hạn"),
        ("TASK_COMMENT", "Gửi ghi chú trao đổi và xem toàn bộ nhật ký tiến độ"),
        ("PLAN_VIEW", "Xem kế hoạch năm học và định mức 270 giờ chuẩn toàn Khoa"),
        ("PLAN_MANAGE", "Quản lý kế hoạch năm, định mức giờ chuẩn và xuất/nhập báo cáo Excel"),
        ("USER_VIEW", "Xem danh sách toàn bộ 18 tài khoản và hồ sơ công tác 1 năm"),
        ("USER_MANAGE", "Toàn quyền thêm/sửa/khóa/xóa tài khoản và cấu hình phân quyền RBAC"),
        ("DEPT_MANAGE", "Quản lý danh mục Bộ môn, danh mục cấp Trường và cấu hình hệ thống"),
        ("ML_PREDICT_VIEW", "Xem dự báo xác suất trễ hạn và giải thích TabPFN v2 toàn hệ thống"),
        ("ML_RECOMMEND_USE", "Sử dụng gợi ý phân công AI & Quản trị tái huấn luyện mô hình MLOps"),
    ],
    ROLE_MANAGER: [
        ("TASK_VIEW", "Xem công việc Toàn Khoa (Trưởng Khoa - FACULTY) hoặc chỉ thuộc Bộ môn mình phụ trách (Trưởng Bộ môn - DEPARTMENT) & xem % tiến độ chung"),
        ("TASK_CREATE", "Tạo đầu việc mới trong phạm vi Khoa (Trưởng Khoa) hoặc Bộ môn phụ trách (Trưởng Bộ môn)"),
        ("TASK_UPDATE", "Chỉnh sửa thông tin công việc và hạn chót trong phạm vi quản lý"),
        ("TASK_DELETE", "Xóa hoặc hủy bỏ công việc trong phạm vi Khoa/Bộ môn quản lý"),
        ("TASK_ASSIGN", "Phân công giảng viên và chỉ định Trưởng nhóm trong phạm vi Khoa/Bộ môn"),
        ("TASK_APPROVE", "Nghiệm thu hoàn thành hoặc duyệt gia hạn trong phạm vi Khoa/Bộ môn"),
        ("TASK_COMMENT", "Gửi ghi chú trao đổi và xem nhật ký tiến độ công việc"),
        ("PLAN_VIEW", "Xem kế hoạch năm học và định mức 270 giờ chuẩn theo phạm vi quản lý"),
        ("PLAN_MANAGE", "Quản lý kế hoạch năm, xuất/nhập báo cáo Excel theo phạm vi Khoa/Bộ môn"),
        ("USER_VIEW", "Xem danh sách giảng viên và hồ sơ công tác 1 năm trong phạm vi quản lý"),
        ("ML_PREDICT_VIEW", "Xem dự báo xác suất trễ hạn và giải thích TabPFN v2"),
        ("ML_RECOMMEND_USE", "Sử dụng gợi ý phân công AI & giám sát mô hình MLOps"),
    ],
    ROLE_LECTURER: [
        ("TASK_VIEW", "Xem danh sách và chi tiết công việc cá nhân hoặc nhóm tham gia (SELF)"),
        ("TASK_UPDATE_PROGRESS", "Giảng viên tự cập nhật % tiến độ cá nhân, nộp minh chứng; Trưởng nhóm phê duyệt thành viên để hệ thống tự tính % dự án"),
        ("TASK_COMMENT", "Gửi ghi chú trao đổi và xem nhật ký tiến độ nhóm"),
        ("PLAN_VIEW", "Xem kế hoạch năm học và định mức 270 giờ chuẩn cá nhân"),
        ("USER_VIEW", "Xem thông tin giảng viên và hồ sơ công tác 1 năm của bản thân"),
    ],
}


def calculate_project_progress_from_assignments(assignments: list) -> int:
    """Hệ thống tự động tính % tiến độ dự án dựa trên trung bình tiến độ của các thành viên trong nhóm (VD: 3 người)."""
    if not assignments:
        return 0
    total = sum(max(0, min(100, int(getattr(a, "progress_pct", 0) or 0))) for a in assignments)
    return int(round(total / len(assignments)))


def is_task_in_manager_department_scope(user: User, task) -> bool:
    """Kiểm tra Trưởng Bộ môn có quyền quản lý công việc này hay không:
    - Admin hoặc Trưởng Khoa (user.department_id is None): Quản lý toàn bộ các Bộ môn của Khoa -> True.
    - Trưởng Bộ môn (user.role == 'manager' and user.department_id is not None):
      Chỉ quản lý được các công việc thuộc Bộ môn đó của Khoa (task.department_id == user.department_id
      hoặc có thành viên trong nhóm thuộc Bộ môn đó).
    """
    if user.role == ROLE_ADMIN:
        return True
    if user.role == ROLE_MANAGER and user.department_id is None:
        return True
    if user.role == ROLE_MANAGER and user.department_id is not None:
        task_dept_id = getattr(task, "department_id", None)
        if task_dept_id is not None:
            return int(task_dept_id) == int(user.department_id)
        for a in getattr(task, "assignments", []) or []:
            lec = getattr(a, "lecturer", None)
            if lec and getattr(lec, "department_id", None) == user.department_id:
                return True
        return False
    return False


def ensure_rbac_catalog(db: Session) -> None:
    """Đảm bảo các bảng roles, permissions, role_permissions và trigger tự động tính % tiến độ dự án trong CSDL."""
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
            db.execute(text("""
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
            """))
    except Exception:
        pass

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

    valid_perm_codes = {code for code, _, _, _ in PERMISSIONS_CATALOG}
    db.query(RolePermission).filter(~RolePermission.permission_code.in_(valid_perm_codes)).delete(synchronize_session=False)
    db.query(Permission).filter(~Permission.code.in_(valid_perm_codes)).delete(synchronize_session=False)
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
        valid_role_perms = {p[0] for p in items}
        db.query(RolePermission).filter(
            RolePermission.role_code == role_code,
            ~RolePermission.permission_code.in_(valid_role_perms),
        ).delete(synchronize_session=False)
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
    dept_label = dept.name if dept else "Toàn Khoa CNTT (4 Bộ môn)"

    if user.role == ROLE_ADMIN:
        scope_level = SCOPE_SYSTEM
        scope_desc = "Toàn hệ thống (SYSTEM • 15/15 quyền) — Quản trị 18 tài khoản, phân quyền RBAC, cấu hình danh mục Bộ môn & MLOps"
        perms = [p[0] for p in ROLE_PERMISSION_MATRIX[ROLE_ADMIN]]
        rule_sql = "ALL_RECORDS (scope = 'SYSTEM', role = 'admin', 15/15 permissions)"
    elif user.role == ROLE_MANAGER:
        perms = [p[0] for p in ROLE_PERMISSION_MATRIX[ROLE_MANAGER]]
        if user.department_id is None:
            scope_level = SCOPE_FACULTY
            scope_desc = "Cấp Toàn Khoa CNTT (FACULTY • 12/15 quyền) — Điều phối, giao việc & nghiệm thu xuyên suốt 4 Bộ môn"
            rule_sql = "FACULTY_WIDE (scope = 'FACULTY', department_id IS NULL, 12/15 permissions)"
        else:
            scope_level = SCOPE_DEPARTMENT
            scope_desc = f"Cấp Bộ môn ({dept_label} • DEPARTMENT • 12/15 quyền) — Chỉ quản lý công việc & nhân sự thuộc Bộ môn phụ trách"
            rule_sql = f"DEPARTMENT_ONLY (scope = 'DEPARTMENT', department_id = {user.department_id} [{dept.code if dept else ''}], 12/15 permissions)"
    else:
        scope_level = SCOPE_SELF
        scope_desc = f"Cá nhân & Nhóm công tác được giao ({dept_label} • SELF • 5/15 quyền)"
        perms = [p[0] for p in ROLE_PERMISSION_MATRIX[ROLE_LECTURER]]
        rule_sql = f"SELF_OR_GROUP_MEMBER (scope = 'SELF', lecturer_id = {user.id} OR lead_lecturer_id = {user.id}, 5/15 permissions)"

    is_admin = user.role == ROLE_ADMIN
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
    scope_row.can_manage_users = is_admin
    scope_row.can_create_task = is_admin_or_mgr
    scope_row.can_assign_task = is_admin_or_mgr
    scope_row.can_approve_extension = is_admin_or_mgr
    scope_row.can_manage_norm_catalog = is_admin
    scope_row.can_import_plan = is_admin_or_mgr
    scope_row.can_view_ml_risk = is_admin_or_mgr
    scope_row.can_retrain_ml_model = is_admin_or_mgr
    scope_row.can_export_report = is_admin_or_mgr
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
