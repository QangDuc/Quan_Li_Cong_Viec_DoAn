"""API Router: Xác thực & Quản trị người dùng."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, LecturerProfile, Department, ROLES, ROLE_LECTURER
from app.security import verify_password, hash_password, create_token, password_problem
from app.deps import current_user, admin_only
from app.schemas import LoginRequest, TokenResponse, ChangePasswordRequest, UserCreate, UserUpdate

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tên đăng nhập hoặc mật khẩu không đúng")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Tài khoản đã bị vô hiệu hóa")

    token = create_token(user.id, user.role)
    dept_name = user.department.name if user.department else "Toàn Khoa"
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
            "department_name": dept_name
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
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "email": user.email,
        "department_id": user.department_id,
        "department_name": dept_name,
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


# --- Quản trị người dùng (Admin) ---
user_router = APIRouter(prefix="/api/users", tags=["Users"])

@user_router.get("")
def list_users(db: Session = Depends(get_db), _: User = Depends(current_user)):
    users = db.query(User).all()
    res = []
    for u in users:
        res.append({
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "email": u.email,
            "department_id": u.department_id,
            "department_name": u.department.name if u.department else None,
            "is_active": u.is_active,
            "lecturer_code": u.profile.lecturer_code if u.profile else None
        })
    return res

@user_router.post("", dependencies=[Depends(admin_only)])
def create_user(req: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter_by(username=req.username).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tên đăng nhập đã tồn tại")
    if req.role not in ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Vai trò phải thuộc: {ROLES}")

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
        email=req.email,
        role=req.role,
        department_id=req.department_id
    )
    db.add(user)
    db.flush()

    if req.role in (ROLE_LECTURER, "manager"):
        code = req.lecturer_code or f"GV{user.id:04d}"
        profile = LecturerProfile(
            user_id=user.id,
            lecturer_code=code,
            academic_rank=req.academic_rank or "Giảng viên",
            degree=req.degree or "Thạc sĩ",
            management_role=req.management_role or "Không"
        )
        db.add(profile)

    db.commit()
    return {"message": "Tạo người dùng thành công", "user_id": user.id}

@user_router.put("/{user_id}", dependencies=[Depends(admin_only)])
def update_user(user_id: int, req: UserUpdate, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy người dùng")

    if req.full_name is not None:
        user.full_name = req.full_name
    if req.email is not None:
        user.email = req.email
    if req.role is not None:
        if req.role not in ROLES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Vai trò không hợp lệ")
        user.role = req.role
    if req.department_id is not None:
        user.department_id = req.department_id
    if req.is_active is not None:
        user.is_active = req.is_active

    db.commit()
    return {"message": "Cập nhật thành công"}
