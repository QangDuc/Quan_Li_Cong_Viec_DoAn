"""
Ứng dụng FastAPI chính cho Backend Hệ thống Quản lý Công việc HUIT.
Gộp các routers: Auth, Users, Tasks, Reports, Common.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.routers_auth import router as auth_router, user_router
from app.routers_tasks import router as task_router
from app.routers_reports import router as report_router
from app.routers_common import router as common_router

app = FastAPI(
    title="HUIT Task Management & ML Assignment System API",
    description="Hệ thống quản lý công việc và tối ưu hóa phân công bằng Học máy tại Khoa CNTT - CNTT-KLCN184",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(task_router)
app.include_router(report_router)
app.include_router(common_router)

@app.get("/")
def root():
    return {
        "project": "CNTT-KLCN184",
        "name": "Hệ thống quản lý công việc và tối ưu hóa phân công bằng Học máy",
        "institution": "Khoa CNTT - HUIT",
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
