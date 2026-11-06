"""Mô hình dữ liệu (SQL Server). Chuỗi dùng Unicode (NVARCHAR) để lưu tiếng Việt.
Thời gian lưu theo giờ địa phương (Asia/Ho_Chi_Minh), không kèm múi giờ."""
import uuid
from datetime import date, datetime

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Integer, Unicode, UnicodeText,
                        UniqueConstraint, Index)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# Vai trò (đúng 3 vai trò theo tài liệu nghiệp vụ)
ROLE_ADMIN, ROLE_MANAGER, ROLE_LECTURER = "admin", "manager", "lecturer"
ROLES = (ROLE_ADMIN, ROLE_MANAGER, ROLE_LECTURER)

# Phạm vi phân quyền dữ liệu (Data Scope)
SCOPE_SYSTEM, SCOPE_FACULTY, SCOPE_DEPARTMENT, SCOPE_SELF = "SYSTEM", "FACULTY", "DEPARTMENT", "SELF"
SCOPES = (SCOPE_SYSTEM, SCOPE_FACULTY, SCOPE_DEPARTMENT, SCOPE_SELF)

# Trạng thái công việc / phân công
ST_NEW, ST_DOING, ST_DONE, ST_CANCELLED = "Mới giao", "Đang thực hiện", "Hoàn thành", "Đã hủy"
EXT_PENDING, EXT_APPROVED, EXT_REJECTED = "Chờ duyệt", "Đã duyệt", "Từ chối"
PRIORITIES = ["Thấp", "Trung bình", "Cao", "Khẩn cấp"]
COMPLEXITIES = ["Thấp", "Trung bình", "Cao"]
SCALES = ["quy mô nhỏ", "quy mô chuẩn", "quy mô lớn"]
LEVELS_ASSIGN = ["Bộ môn", "Khoa", "Trường"]


def _now():
    return datetime.now()


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(Unicode(50), unique=True)
    name: Mapped[str] = mapped_column(Unicode(200))
    ml_name: Mapped[str] = mapped_column(Unicode(200))   # chuỗi bộ môn mà mô hình đã thấy (vd "K01 - Công nghệ phần mềm")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'manager', 'lecturer')", name="ck_users_valid_role"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(Unicode(100), unique=True)
    password_hash: Mapped[str] = mapped_column(Unicode(200))
    full_name: Mapped[str] = mapped_column(Unicode(200))
    email: Mapped[str | None] = mapped_column(Unicode(200))
    role: Mapped[str] = mapped_column(Unicode(20))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    department: Mapped[Department | None] = relationship()
    profile: Mapped["LecturerProfile | None"] = relationship(back_populates="user", uselist=False)
    permission_scope: Mapped["UserPermissionScope | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class RoleDefinition(Base):
    """Bảng danh mục Vai trò hệ thống (RBAC Role Catalog)."""
    __tablename__ = "roles"
    __table_args__ = (
        CheckConstraint("code IN ('admin', 'manager', 'lecturer')", name="ck_roles_valid_code"),
    )
    code: Mapped[str] = mapped_column(Unicode(30), primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(100))
    hierarchy_level: Mapped[int] = mapped_column(Integer)
    default_scope: Mapped[str] = mapped_column(Unicode(40))
    description: Mapped[str] = mapped_column(Unicode(500))


class Permission(Base):
    """Bảng danh mục Quyền chức năng chi tiết trong hệ thống (RBAC Permissions)."""
    __tablename__ = "permissions"
    code: Mapped[str] = mapped_column(Unicode(50), primary_key=True)
    module: Mapped[str] = mapped_column(Unicode(80))
    name: Mapped[str] = mapped_column(Unicode(150))
    description: Mapped[str] = mapped_column(Unicode(500))


class RolePermission(Base):
    """Bảng ánh xạ Vai trò - Quyền hạn & Ràng buộc nghiệp vụ (Role-Permission Matrix)."""
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_code", "permission_code", name="uq_role_permission"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    role_code: Mapped[str] = mapped_column(ForeignKey("roles.code"))
    permission_code: Mapped[str] = mapped_column(ForeignKey("permissions.code"))
    constraint_note: Mapped[str | None] = mapped_column(Unicode(300))

    role_def: Mapped[RoleDefinition] = relationship()
    permission: Mapped[Permission] = relationship()


class UserPermissionScope(Base):
    """Bảng lưu trữ tường minh quyền hạn và ràng buộc phạm vi dữ liệu của từng tài khoản."""
    __tablename__ = "user_permission_scopes"
    __table_args__ = (
        CheckConstraint("role_code IN ('admin', 'manager', 'lecturer')", name="ck_ups_valid_role"),
        CheckConstraint("scope_level IN ('SYSTEM', 'FACULTY', 'DEPARTMENT', 'SELF')", name="ck_ups_valid_scope"),
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    username: Mapped[str] = mapped_column(Unicode(100), unique=True)
    role_code: Mapped[str] = mapped_column(ForeignKey("roles.code"))
    scope_level: Mapped[str] = mapped_column(Unicode(30))  # SYSTEM | FACULTY | DEPARTMENT | SELF
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    scope_description: Mapped[str] = mapped_column(Unicode(300))
    can_manage_users: Mapped[bool] = mapped_column(Boolean, default=False)
    can_create_task: Mapped[bool] = mapped_column(Boolean, default=False)
    can_assign_task: Mapped[bool] = mapped_column(Boolean, default=False)
    can_approve_extension: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_norm_catalog: Mapped[bool] = mapped_column(Boolean, default=False)
    can_import_plan: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_ml_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    can_retrain_ml_model: Mapped[bool] = mapped_column(Boolean, default=False)
    can_export_report: Mapped[bool] = mapped_column(Boolean, default=False)
    can_update_own_progress: Mapped[bool] = mapped_column(Boolean, default=True)
    can_request_extension: Mapped[bool] = mapped_column(Boolean, default=True)
    granted_permissions_json: Mapped[str] = mapped_column(UnicodeText)
    access_constraint_rule: Mapped[str] = mapped_column(Unicode(300))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    user: Mapped[User] = relationship(back_populates="permission_scope")
    department: Mapped[Department | None] = relationship()


class LecturerProfile(Base):
    """Hồ sơ giảng viên — các trường mô hình cần (chức danh, học vị, tải giảng dạy...)."""
    __tablename__ = "lecturer_profiles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    lecturer_code: Mapped[str] = mapped_column(Unicode(20), unique=True)
    academic_rank: Mapped[str] = mapped_column(Unicode(50), default="Giảng viên")
    degree: Mapped[str] = mapped_column(Unicode(50), default="Thạc sĩ")
    management_role: Mapped[str] = mapped_column(Unicode(50), default="Không")
    career_start_date: Mapped[date | None] = mapped_column(Date)    # -> years_experience
    join_date: Mapped[date | None] = mapped_column(Date)            # -> tenure_days
    teaching_hours_semester: Mapped[float | None] = mapped_column(Float)
    course_count: Mapped[int | None] = mapped_column(Integer)
    student_count: Mapped[int | None] = mapped_column(Integer)
    supervised_student_count: Mapped[int | None] = mapped_column(Integer)

    user: Mapped[User] = relationship(back_populates="profile")


class TaskType(Base):
    """Danh mục loại công việc của Khoa (đúng 35 loại mô hình đã thấy)."""
    __tablename__ = "task_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Unicode(200), unique=True)
    task_group: Mapped[str] = mapped_column(Unicode(100))
    default_complexity: Mapped[str] = mapped_column(Unicode(20), default="Trung bình")
    default_subtask_count: Mapped[int] = mapped_column(Integer, default=1)
    default_dependency_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    scales: Mapped[list["TaskTypeScale"]] = relationship(back_populates="task_type", order_by="TaskTypeScale.id")


class TaskTypeScale(Base):
    """Thang quy đổi: (loại việc, quy mô) -> thời lượng điển hình + giờ chuẩn quy đổi."""
    __tablename__ = "task_type_scales"
    __table_args__ = (UniqueConstraint("task_type_id", "scale"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    task_type_id: Mapped[int] = mapped_column(ForeignKey("task_types.id"))
    scale: Mapped[str] = mapped_column(Unicode(30))
    expected_duration_days: Mapped[float] = mapped_column(Float)
    conversion_hours: Mapped[float | None] = mapped_column(Float)   # NULL = không quy đổi cố định

    task_type: Mapped[TaskType] = relationship(back_populates="scales")


class SchoolCatalogItem(Base):
    """Danh mục công việc cấp Trường (FR-06), có giờ chuẩn quy đổi riêng."""
    __tablename__ = "school_catalog"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(Unicode(30), unique=True)
    name: Mapped[str] = mapped_column(Unicode(300))
    conversion_hours: Mapped[float] = mapped_column(Float)
    task_type_id: Mapped[int | None] = mapped_column(ForeignKey("task_types.id"))
    note: Mapped[str | None] = mapped_column(Unicode(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    task_type: Mapped[TaskType | None] = relationship()


class CalendarEvent(Base):
    """Lịch năm học: ngày nghỉ lễ/Tết (holiday) và đợt kiểm định (accreditation)."""
    __tablename__ = "calendar_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(Unicode(20))
    name: Mapped[str] = mapped_column(Unicode(200))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)


class Plan(Base):
    """Kế hoạch công việc năm của một giảng viên (FR-03); các đầu việc là Task có plan_id."""
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    lecturer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    academic_year: Mapped[str] = mapped_column(Unicode(20))
    file_name: Mapped[str | None] = mapped_column(Unicode(300))
    imported_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    lecturer: Mapped[User] = relationship(foreign_keys=[lecturer_id])

    @property
    def note(self) -> str:
        return f"Kế hoạch công tác năm học {self.academic_year}"


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(Unicode(30), unique=True)
    title: Mapped[str] = mapped_column(Unicode(300))
    description: Mapped[str | None] = mapped_column(UnicodeText)
    task_type_id: Mapped[int] = mapped_column(ForeignKey("task_types.id"))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    scale: Mapped[str] = mapped_column(Unicode(30), default="quy mô chuẩn")
    school_catalog_id: Mapped[int | None] = mapped_column(ForeignKey("school_catalog.id"))
    priority: Mapped[str] = mapped_column(Unicode(20), default="Trung bình")
    complexity: Mapped[str] = mapped_column(Unicode(20), default="Trung bình")
    assignment_mode: Mapped[str] = mapped_column(Unicode(20), default="Individual")   # Individual | Group
    assignment_level: Mapped[str] = mapped_column(Unicode(20), default="Khoa")
    assignment_channel: Mapped[str] = mapped_column(Unicode(30), default="Hệ thống")
    subtask_count: Mapped[int] = mapped_column(Integer, default=1)
    dependency_count: Mapped[int] = mapped_column(Integer, default=0)
    require_external_input: Mapped[bool] = mapped_column(Boolean, default=False)
    require_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    estimated_effort_hours: Mapped[float | None] = mapped_column(Float)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    original_deadline: Mapped[date] = mapped_column(Date)
    current_deadline: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Unicode(30), default=ST_NEW)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)   # Tự động tính từ trung bình cộng tiến độ các thành viên nhóm
    lead_approval_status: Mapped[str] = mapped_column(Unicode(60), default="Chờ Trưởng nhóm duyệt")
    lead_decision_note: Mapped[str | None] = mapped_column(Unicode(500))
    lead_submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    reviewer_approval_status: Mapped[str] = mapped_column(Unicode(60), default="Chờ Người kiểm tra duyệt")
    reviewer_decision_note: Mapped[str | None] = mapped_column(Unicode(500))
    reviewer_approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    lead_lecturer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id"))
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False)   # dữ liệu lịch sử mô phỏng (seed)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    task_type: Mapped[TaskType] = relationship()
    department: Mapped[Department | None] = relationship()
    school_item: Mapped[SchoolCatalogItem | None] = relationship()
    assignments: Mapped[list["TaskAssignment"]] = relationship(back_populates="task", order_by="TaskAssignment.id")
    extensions: Mapped[list["ExtensionRequest"]] = relationship(back_populates="task", order_by="ExtensionRequest.id")
    approval_logs: Mapped[list["TaskApprovalLog"]] = relationship(back_populates="task", order_by="TaskApprovalLog.id")
    creator: Mapped[User | None] = relationship(foreign_keys=[created_by])
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewer_id])
    lead_lecturer: Mapped[User | None] = relationship(foreign_keys=[lead_lecturer_id])


class TaskAssignment(Base):
    """Một giảng viên thực hiện một công việc (việc nhóm có nhiều dòng). Nhãn ML gắn ở mức này."""
    __tablename__ = "task_assignments"
    __table_args__ = (UniqueConstraint("task_id", "lecturer_id"),
                      Index("ix_assign_lecturer_completed", "lecturer_id", "completed_at"))
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    lecturer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_lead: Mapped[bool] = mapped_column(Boolean, default=False)
    member_task_note: Mapped[str | None] = mapped_column(Unicode(500))
    latest_evidence_name: Mapped[str | None] = mapped_column(Unicode(300))
    latest_evidence_url: Mapped[str | None] = mapped_column(Unicode(500))
    member_evidence_status: Mapped[str | None] = mapped_column(Unicode(50))   # Đã gửi Trưởng nhóm | Đã xác nhận | Cần bổ sung
    lead_approval_status: Mapped[str] = mapped_column(Unicode(60), default="Chờ Trưởng nhóm duyệt")
    lead_approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    lead_approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    review_feedback: Mapped[str | None] = mapped_column(Unicode(500))         # Nhận xét / thông báo thiếu sót từ Trưởng nhóm hoặc Người kiểm tra
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    self_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(Unicode(30), default=ST_NEW)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_late: Mapped[bool | None] = mapped_column(Boolean)              # so với HẠN GỐC (= nhãn is_late của mô hình)
    is_late_current: Mapped[bool | None] = mapped_column(Boolean)      # so với hạn hiện hành (sau gia hạn) — dùng thống kê
    delay_days: Mapped[float | None] = mapped_column(Float)            # số ngày trễ so với hạn gốc (âm = sớm)

    task: Mapped[Task] = relationship(back_populates="assignments")
    lecturer: Mapped[User] = relationship(foreign_keys=[lecturer_id])
    lead_approver: Mapped[User | None] = relationship(foreign_keys=[lead_approved_by])
    progress_updates: Mapped[list["ProgressUpdate"]] = relationship(back_populates="assignment", order_by="ProgressUpdate.id")


class TaskApprovalLog(Base):
    """Bảng lưu vết lịch sử phê duyệt đa cấp (Thành viên -> Trưởng nhóm -> Hệ thống tự tính -> Người kiểm tra)."""
    __tablename__ = "task_approval_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    assignment_id: Mapped[int | None] = mapped_column(ForeignKey("task_assignments.id"))
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    actor_role: Mapped[str] = mapped_column(Unicode(50))
    action_type: Mapped[str] = mapped_column(Unicode(64))
    member_progress_pct: Mapped[int | None] = mapped_column(Integer)
    calculated_project_pct: Mapped[int | None] = mapped_column(Integer)
    approval_status: Mapped[str] = mapped_column(Unicode(64))
    note: Mapped[str | None] = mapped_column(Unicode(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    task: Mapped[Task] = relationship(back_populates="approval_logs")
    actor: Mapped[User] = relationship(foreign_keys=[actor_user_id])


class ProgressUpdate(Base):
    __tablename__ = "progress_updates"
    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("task_assignments.id"))
    progress_pct: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Unicode(1000))
    evidence_file_name: Mapped[str | None] = mapped_column(Unicode(300))
    evidence_file_url: Mapped[str | None] = mapped_column(Unicode(500))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    assignment: Mapped[TaskAssignment] = relationship(back_populates="progress_updates")


class ExtensionRequest(Base):
    __tablename__ = "extension_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Unicode(1000))
    old_deadline: Mapped[date] = mapped_column(Date)
    proposed_deadline: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Unicode(20), default=EXT_PENDING)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    review_note: Mapped[str | None] = mapped_column(Unicode(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    task: Mapped[Task] = relationship(back_populates="extensions")
    requester: Mapped[User] = relationship(foreign_keys=[requested_by])
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewed_by])

    @property
    def requested_at(self) -> datetime:
        return self.created_at



class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(Unicode(30))     # new_task | due_soon | overdue | extension | risk_high | plan
    title: Mapped[str] = mapped_column(Unicode(300))
    content: Mapped[str | None] = mapped_column(Unicode(2000))
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    # khóa chống gửi trùng (vd "due_soon:<assignment>:<ngày>"); luôn có giá trị để dùng UNIQUE trên SQL Server
    dedupe_key: Mapped[str] = mapped_column(Unicode(200), unique=True, default=lambda: uuid.uuid4().hex)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class RiskPrediction(Base):
    """Lịch sử dự đoán rủi ro trễ hạn (FR-10) — bổ sung kết quả thực tế khi việc kết thúc để đối chiếu."""
    __tablename__ = "risk_predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("task_assignments.id"), index=True)
    lecturer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    trigger: Mapped[str] = mapped_column(Unicode(20))      # assign | extension
    status: Mapped[str] = mapped_column(Unicode(20))       # ok | pending | failed
    probability: Mapped[float | None] = mapped_column(Float)
    level: Mapped[str | None] = mapped_column(Unicode(20))
    uncertainty: Mapped[float | None] = mapped_column(Float)
    top_factors: Mapped[str | None] = mapped_column(UnicodeText)       # JSON
    recommendation: Mapped[str | None] = mapped_column(Unicode(1000))
    low_confidence: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Unicode(1000))
    model_version: Mapped[str | None] = mapped_column(Unicode(200))
    features_json: Mapped[str | None] = mapped_column(UnicodeText)     # 58 đặc trưng đã gửi (để kiểm tra/huấn luyện lại)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Unicode(1000))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    predicted_at: Mapped[datetime | None] = mapped_column(DateTime)
    actual_is_late: Mapped[bool | None] = mapped_column(Boolean)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)

    task: Mapped[Task] = relationship()
    lecturer: Mapped[User] = relationship()
