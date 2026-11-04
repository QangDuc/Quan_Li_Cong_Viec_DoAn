"""API Router: Xác thực & Quản trị người dùng (Thêm - Sửa - Xóa & Theo dõi trạng thái hoạt động thực tế)."""
import json
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    User, LecturerProfile, Department, TaskAssignment, Task, ProgressUpdate,
    RiskPrediction, ExtensionRequest, Notification,
    RoleDefinition, Permission, RolePermission, UserPermissionScope,
    ROLES, ROLE_LECTURER, ST_DONE, ST_CANCELLED
)
from app.security import verify_password, hash_password, create_token, password_problem
from app.deps import current_user, admin_only, manager_or_admin
from app.schemas import LoginRequest, TokenResponse, ChangePasswordRequest, UserCreate, UserUpdate
from app.rbac import ensure_rbac_catalog, sync_user_permission_scope, sync_all_users_rbac

router = APIRouter(prefix="/api/auth", tags=["Auth"])

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,50}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.get("/accounts-directory", dependencies=[Depends(admin_only)])
def get_accounts_directory(db: Session = Depends(get_db)):
    """Danh bạ toàn bộ tài khoản giảng viên / quản lý kèm quyền hạn RBAC (dành cho Quản trị viên Hệ thống Admin)."""
    users = db.query(User).order_by(User.id.asc()).all()
    res = []
    for u in users:
        scope = u.permission_scope
        perms = json.loads(scope.granted_permissions_json) if scope and scope.granted_permissions_json else []
        res.append({
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "email": u.email,
            "is_active": u.is_active,
            "department_id": u.department_id,
            "department_name": u.department.name if u.department else "Toàn Khoa CNTT",
            "lecturer_code": u.profile.lecturer_code if u.profile else None,
            "academic_rank": u.profile.academic_rank if u.profile else None,
            "degree": u.profile.degree if u.profile else None,
            "scope_level": scope.scope_level if scope else None,
            "scope_description": scope.scope_description if scope else None,
            "access_constraint_rule": scope.access_constraint_rule if scope else None,
            "permissions": perms,
        })
    return res


@router.get("/rbac-matrix")
def get_rbac_matrix(db: Session = Depends(get_db), _: User = Depends(current_user)):
    """Tra cứu toàn bộ cấu trúc phân quyền RBAC từ CSDL: roles, permissions, role_permissions, user_permission_scopes."""
    roles = db.query(RoleDefinition).order_by(RoleDefinition.hierarchy_level.desc()).all()
    perms = db.query(Permission).order_by(Permission.module.asc(), Permission.code.asc()).all()
    role_perms = db.query(RolePermission).order_by(RolePermission.id.asc()).all()
    user_scopes = db.query(UserPermissionScope).order_by(UserPermissionScope.user_id.asc()).all()
    return {
        "roles": [
            {
                "code": r.code,
                "name": r.name,
                "hierarchy_level": r.hierarchy_level,
                "default_scope": r.default_scope,
                "description": r.description,
            }
            for r in roles
        ],
        "permissions": [
            {
                "code": p.code,
                "module": p.module,
                "name": p.name,
                "description": p.description,
            }
            for p in perms
        ],
        "role_permissions": [
            {
                "id": rp.id,
                "role_code": rp.role_code,
                "permission_code": rp.permission_code,
                "constraint_note": rp.constraint_note,
            }
            for rp in role_perms
        ],
        "user_permission_scopes": [
            {
                "user_id": us.user_id,
                "username": us.username,
                "role_code": us.role_code,
                "scope_level": us.scope_level,
                "department_id": us.department_id,
                "scope_description": us.scope_description,
                "can_manage_users": us.can_manage_users,
                "can_create_task": us.can_create_task,
                "can_assign_task": us.can_assign_task,
                "can_approve_extension": us.can_approve_extension,
                "can_manage_norm_catalog": us.can_manage_norm_catalog,
                "can_import_plan": us.can_import_plan,
                "can_view_ml_risk": us.can_view_ml_risk,
                "can_retrain_ml_model": us.can_retrain_ml_model,
                "can_export_report": us.can_export_report,
                "can_update_own_progress": us.can_update_own_progress,
                "can_request_extension": us.can_request_extension,
                "permissions": json.loads(us.granted_permissions_json) if us.granted_permissions_json else [],
                "access_constraint_rule": us.access_constraint_rule,
            }
            for us in user_scopes
        ],
    }


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    uname = (req.username or "").strip()
    user = db.query(User).filter_by(username=uname).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tên đăng nhập hoặc mật khẩu không đúng")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tài khoản đã bị khóa hoặc ngừng hoạt động")

    now = datetime.now()
    user.last_login_at = now
    user.last_active_at = now
    db.commit()

    token = create_token(user.id, user.role)
    dept_name = user.department.name if user.department else "Toàn Khoa"
    scope = user.permission_scope
    perms = json.loads(scope.granted_permissions_json) if scope and scope.granted_permissions_json else []
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "email": user.email,
            "department_id": user.department_id,
            "department_name": dept_name,
            "lecturer_code": user.profile.lecturer_code if user.profile else None,
            "degree": user.profile.degree if user.profile else None,
            "academic_rank": user.profile.academic_rank if user.profile else None,
            "scope_level": scope.scope_level if scope else None,
            "scope_description": scope.scope_description if scope else None,
            "access_constraint_rule": scope.access_constraint_rule if scope else None,
            "permissions": perms,
        }
    }


@router.get("/me")
def get_me(user: User = Depends(current_user)):
    dept_name = user.department.name if user.department else "Toàn Khoa"
    profile_data = {}
    if user.profile:
        profile_data = {
            "lecturer_code": user.profile.lecturer_code,
            "academic_rank": user.profile.academic_rank,
            "degree": user.profile.degree,
            "management_role": user.profile.management_role,
            "teaching_hours_semester": user.profile.teaching_hours_semester,
            "student_count": user.profile.student_count,
            "supervised_student_count": user.profile.supervised_student_count,
        }
    scope = user.permission_scope
    perms = json.loads(scope.granted_permissions_json) if scope and scope.granted_permissions_json else []
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "email": user.email,
        "department_id": user.department_id,
        "department_name": dept_name,
        "lecturer_code": user.profile.lecturer_code if user.profile else None,
        "degree": user.profile.degree if user.profile else None,
        "academic_rank": user.profile.academic_rank if user.profile else None,
        "scope_level": scope.scope_level if scope else None,
        "scope_description": scope.scope_description if scope else None,
        "access_constraint_rule": scope.access_constraint_rule if scope else None,
        "permissions": perms,
        "profile": profile_data
    }


@router.post("/change-password")
def change_password(req: ChangePasswordRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not verify_password(req.old_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mật khẩu hiện tại không đúng")
    prob = password_problem(req.new_password)
    if prob:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, prob)

    user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"message": "Đổi mật khẩu thành công"}


# --- Quản trị người dùng (CRUD: Thêm - Sửa - Xóa & Trạng thái hoạt động thực tế) ---
user_router = APIRouter(prefix="/api/users", tags=["Users"])


@user_router.get("")
def list_users(db: Session = Depends(get_db), _: User = Depends(current_user)):
    users = db.query(User).order_by(User.id.asc()).all()
    now = datetime.now()
    res = []
    for u in users:
        open_tasks = (
            db.query(TaskAssignment)
            .filter(
                TaskAssignment.lecturer_id == u.id,
                TaskAssignment.status != ST_DONE,
                TaskAssignment.status != ST_CANCELLED
            )
            .count()
        )
        done_tasks = (
            db.query(TaskAssignment)
            .filter(TaskAssignment.lecturer_id == u.id, TaskAssignment.status == ST_DONE)
            .count()
        )
        # Xác định trạng thái trực tuyến và cơ sở đánh giá hoạt động
        is_online = False
        if u.last_active_at:
            diff_min = (now - u.last_active_at).total_seconds() / 60.0
            is_online = diff_min <= 15.0

        if not u.is_active:
            status_label = "Đã khóa (Ngừng hoạt động)"
            activity_basis = "Tài khoản bị vô hiệu hóa bởi Quản trị viên, không thể đăng nhập hay nhận việc mới."
        elif is_online:
            status_label = "Đang trực tuyến (Online)"
            activity_basis = f"Vừa tương tác trên hệ thống • Đang thực hiện {open_tasks} việc ({done_tasks} việc đã xong)"
        elif open_tasks > 0:
            status_label = "Đang hoạt động (Có phân công)"
            last_seen = u.last_active_at.strftime("%d/%m/%Y %H:%M") if u.last_active_at else "Trong học kỳ"
            activity_basis = f"Tài khoản kích hoạt • Đang đảm nhận {open_tasks} công việc • Truy cập: {last_seen}"
        else:
            status_label = "Sẵn sàng nhận việc"
            last_seen = u.last_active_at.strftime("%d/%m/%Y %H:%M") if u.last_active_at else "Chưa ghi nhận phiên mới"
            activity_basis = f"Tài khoản kích hoạt (`is_active=True`) • Hiện không có việc tồn đọng • Truy cập: {last_seen}"

        scope = u.permission_scope
        perms = json.loads(scope.granted_permissions_json) if scope and scope.granted_permissions_json else []
        res.append({
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "email": u.email,
            "department_id": u.department_id,
            "department_name": u.department.name if u.department else "Toàn Khoa CNTT",
            "is_active": u.is_active,
            "is_online": is_online,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "last_active_at": u.last_active_at.isoformat() if u.last_active_at else None,
            "open_tasks_count": open_tasks,
            "completed_tasks_count": done_tasks,
            "status_label": status_label,
            "activity_basis": activity_basis,
            "lecturer_code": u.profile.lecturer_code if u.profile else f"CB{u.id:04d}",
            "degree": u.profile.degree if u.profile else "Thạc sĩ",
            "academic_rank": u.profile.academic_rank if u.profile else ("Quản trị" if u.role == "admin" else "Giảng viên"),
            "teaching_hours_semester": u.profile.teaching_hours_semester if u.profile else 135.0,
            "scope_level": scope.scope_level if scope else None,
            "scope_description": scope.scope_description if scope else None,
            "access_constraint_rule": scope.access_constraint_rule if scope else None,
            "permissions": perms,
        })
    return res


@user_router.post("", dependencies=[Depends(manager_or_admin)])
def create_user(req: UserCreate, db: Session = Depends(get_db), current: User = Depends(current_user)):
    uname = (req.username or "").strip()
    if not USERNAME_RE.match(uname):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Tên đăng nhập phải từ 3–50 ký tự và chỉ chứa chữ cái, chữ số hoặc dấu gạch dưới (_)"
        )
    if db.query(User).filter_by(username=uname).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Tên đăng nhập '{uname}' đã tồn tại trong hệ thống")

    fname = (req.full_name or "").strip()
    if len(fname) < 3:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Họ và tên phải có ít nhất 3 ký tự")

    email_clean = (req.email or "").strip() or f"{uname}@huit.edu.vn"
    if not EMAIL_RE.match(email_clean):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Địa chỉ Email không đúng định dạng (VD: ten@huit.edu.vn)")

    prob = password_problem(req.password)
    if prob:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, prob)

    if req.role not in ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Vai trò phải thuộc: {ROLES}")

    # Ràng buộc phân cấp RBAC khi tạo tài khoản
    if req.role == "admin" and current.role != "admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Chỉ Quản trị viên Hệ thống (admin) mới có quyền tạo tài khoản cấp Quản trị viên"
        )
    target_dept_id = req.department_id
    if current.role == "manager" and current.department_id is not None:
        if target_dept_id is not None and target_dept_id != current.department_id:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Trưởng Bộ môn chỉ được phép tạo tài khoản giảng viên thuộc Bộ môn mình quản lý"
            )
        target_dept_id = current.department_id

    user = User(
        username=uname,
        password_hash=hash_password(req.password),
        full_name=fname,
        email=email_clean,
        role=req.role,
        department_id=target_dept_id,
        is_active=True
    )
    db.add(user)
    db.flush()

    code = (req.lecturer_code or "").strip() or f"GV{user.id:04d}"
    if db.query(LecturerProfile).filter_by(lecturer_code=code).first():
        code = f"GV{user.id:04d}"
    profile = LecturerProfile(
        user_id=user.id,
        lecturer_code=code,
        academic_rank=req.academic_rank or "Giảng viên",
        degree=req.degree or "Thạc sĩ",
        management_role=req.management_role or ("Trưởng bộ môn" if req.role == "manager" else "Không"),
        teaching_hours_semester=req.teaching_hours_semester if req.teaching_hours_semester is not None else 135.0,
        course_count=3,
        student_count=180,
        supervised_student_count=3
    )
    db.add(profile)
    ensure_rbac_catalog(db)
    sync_user_permission_scope(db, user)
    db.commit()
    return {"message": f"Đã tạo tài khoản '{fname}' ({uname}) thành công", "user_id": user.id, "id": user.id}


@user_router.put("/{user_id}", dependencies=[Depends(manager_or_admin)])
def update_user(user_id: int, req: UserUpdate, db: Session = Depends(get_db), current: User = Depends(current_user)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy người dùng")

    # Ràng buộc phân cấp RBAC khi cập nhật tài khoản
    if (user.role == "admin" or req.role == "admin") and current.role != "admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Chỉ Quản trị viên Hệ thống (admin) mới có quyền chỉnh sửa hoặc nâng quyền Quản trị viên"
        )
    if current.role == "manager" and current.department_id is not None:
        if user.department_id != current.department_id:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Trưởng Bộ môn chỉ được phép chỉnh sửa tài khoản thuộc Bộ môn mình quản lý"
            )

    if req.full_name is not None:
        fname = req.full_name.strip()
        if len(fname) < 3:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Họ và tên phải từ 3 ký tự trở lên")
        user.full_name = fname

    if req.email is not None:
        email_clean = req.email.strip()
        if email_clean and not EMAIL_RE.match(email_clean):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Địa chỉ Email không đúng định dạng")
        user.email = email_clean

    if req.role is not None:
        if req.role not in ROLES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Vai trò không hợp lệ")
        user.role = req.role

    if req.department_id is not None:
        user.department_id = req.department_id if req.department_id > 0 else None

    if req.is_active is not None:
        if user.id == current.id and not req.is_active:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Không thể tự khóa tài khoản đang đăng nhập của chính bạn")
        user.is_active = req.is_active

    if req.new_password:
        prob = password_problem(req.new_password)
        if prob:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, prob)
        user.password_hash = hash_password(req.new_password)

    # Cập nhật thông tin hồ sơ giảng viên
    if not user.profile:
        user.profile = LecturerProfile(
            user_id=user.id,
            lecturer_code=req.lecturer_code or f"GV{user.id:04d}",
            academic_rank=req.academic_rank or "Giảng viên",
            degree=req.degree or "Thạc sĩ",
            management_role=req.management_role or "Không",
            teaching_hours_semester=req.teaching_hours_semester or 135.0
        )
    else:
        if req.lecturer_code:
            user.profile.lecturer_code = req.lecturer_code.strip()
        if req.academic_rank:
            user.profile.academic_rank = req.academic_rank.strip()
        if req.degree:
            user.profile.degree = req.degree.strip()
        if req.management_role:
            user.profile.management_role = req.management_role.strip()
        if req.teaching_hours_semester is not None:
            user.profile.teaching_hours_semester = float(req.teaching_hours_semester)

    ensure_rbac_catalog(db)
    sync_user_permission_scope(db, user)
    db.commit()
    return {"message": f"Đã cập nhật thông tin tài khoản '{user.full_name}' thành công"}


@user_router.delete("/{user_id}", dependencies=[Depends(manager_or_admin)])
def delete_user(user_id: int, db: Session = Depends(get_db), current: User = Depends(current_user)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy tài khoản cần xóa")
    if user.id == current.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bạn không thể tự xóa tài khoản đang đăng nhập của chính mình")
    if user.username == "admin" or user.role == "admin":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Không thể xóa tài khoản Quản trị viên Hệ thống (admin)")
    if current.role == "manager" and current.department_id is not None and user.department_id != current.department_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Trưởng Bộ môn chỉ được phép xóa tài khoản thuộc Bộ môn mình quản lý"
        )

    # Dọn dẹp các bản ghi liên kết để xóa an toàn
    assigns = db.query(TaskAssignment).filter_by(lecturer_id=user.id).all()
    for a in assigns:
        db.query(ProgressUpdate).filter_by(assignment_id=a.id).delete()
        db.query(RiskPrediction).filter_by(assignment_id=a.id).delete()
        db.delete(a)
    db.query(RiskPrediction).filter_by(lecturer_id=user.id).delete()
    db.query(ExtensionRequest).filter_by(requested_by=user.id).delete()
    db.query(Notification).filter_by(user_id=user.id).delete()
    db.query(UserPermissionScope).filter_by(user_id=user.id).delete()
    if user.profile:
        db.delete(user.profile)

    # Bỏ tham chiếu trên Task nếu có
    db.query(Task).filter_by(lead_lecturer_id=user.id).update({"lead_lecturer_id": None})
    db.query(Task).filter_by(reviewer_id=user.id).update({"reviewer_id": None})
    db.query(Task).filter_by(created_by=user.id).update({"created_by": None})

    name_deleted = user.full_name
    db.delete(user)
    db.commit()
    return {"message": f"Đã xóa tài khoản '{name_deleted}' khỏi hệ thống"}
