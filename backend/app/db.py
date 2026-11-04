"""Kết nối CSDL (SQLAlchemy 2.0)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app import config


class Base(DeclarativeBase):
    pass


def make_engine(url=None):
    url = url or config.DATABASE_URL
    kw = dict(pool_pre_ping=True)
    if url.startswith("mssql"):
        kw["fast_executemany"] = True
    elif url.startswith("sqlite"):
        kw["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kw)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
