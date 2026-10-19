"""Băm mật khẩu (bcrypt) và JWT (HS256)."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app import config


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), hashed.encode())
    except ValueError:
        return False


def create_token(user_id: int, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=config.JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "role": role, "exp": exp}, config.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])


def password_problem(pw: str) -> str | None:
    """Quy tắc mật khẩu tối thiểu; trả về thông báo lỗi hoặc None."""
    if len(pw) < 8:
        return "Mật khẩu phải có ít nhất 8 ký tự"
    if not any(c.isdigit() for c in pw) or not any(c.isalpha() for c in pw):
        return "Mật khẩu phải gồm cả chữ và số"
    return None
