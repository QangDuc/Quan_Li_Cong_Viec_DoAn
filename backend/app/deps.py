"""Phụ thuộc dùng chung cho router: người dùng hiện tại, kiểm tra vai trò, phạm vi dữ liệu."""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ROLE_ADMIN, ROLE_LECTURER, ROLE_MANAGER, User
from app.security import decode_token

_bearer = HTTPBearer(auto_error=False)


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(_bearer), db: Session = Depends(get_db)) -> User:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chưa đăng nhập")
    try:
        data = decode_token(cred.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Phiên đăng nhập đã hết hạn")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token không hợp lệ")
    user = db.get(User, int(data["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tài khoản không tồn tại hoặc đã bị khóa")
    return user


def require_roles(*roles):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Bạn không có quyền thực hiện chức năng này")
        return user
    return dep


admin_only = require_roles(ROLE_ADMIN)
manager_only = require_roles(ROLE_MANAGER)
manager_or_admin = require_roles(ROLE_MANAGER, ROLE_ADMIN)


def lecturer_scope(db: Session, user: User):
    """Danh sách id giảng viên mà người dùng được xem; None = toàn Khoa.
    - Giảng viên: chỉ bản thân.
    - Quản lý có bộ môn (Trưởng/Phó Bộ môn): giảng viên thuộc bộ môn đó.
    - Quản lý không gắn bộ môn (Trưởng Khoa) và Quản trị viên: toàn Khoa."""
    if user.role == ROLE_LECTURER:
        return [user.id]
    if user.role == ROLE_MANAGER and user.department_id is not None:
        return [u.id for u in db.query(User.id).filter(User.department_id == user.department_id, User.role == ROLE_LECTURER)]
    return None


def can_see_lecturer(db: Session, user: User, lecturer_id: int) -> bool:
    scope = lecturer_scope(db, user)
    return scope is None or lecturer_id in scope


def can_see_risk(db: Session, user: User, lecturer_id: int) -> bool:
    """Cảnh báo ML chỉ dành cho người quản lý trong phạm vi của mình (giảng viên không xem — theo bảng quyền hạn)."""
    return user.role == ROLE_MANAGER and can_see_lecturer(db, user, lecturer_id)
