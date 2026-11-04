"""Schemas Pydantic cho request / response các API."""
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# --- Auth ---
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    email: Optional[str] = None
    role: str
    department_id: Optional[int] = None
    lecturer_code: Optional[str] = None
    academic_rank: Optional[str] = "Giảng viên"
    degree: Optional[str] = "Thạc sĩ"
    management_role: Optional[str] = "Không"

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None

# --- Task ---
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    task_type_id: int
    scale: Optional[str] = "quy mô chuẩn"
    school_catalog_id: Optional[int] = None
    priority: Optional[str] = "Trung bình"
    complexity: Optional[str] = "Trung bình"
    assignment_mode: Optional[str] = "Individual"  # Individual / Group
    assignment_level: Optional[str] = "Khoa"
    assignment_channel: Optional[str] = "Hệ thống"
    subtask_count: Optional[int] = 1
    dependency_count: Optional[int] = 0
    require_external_input: Optional[bool] = False
    require_approval: Optional[bool] = False
    estimated_effort_hours: Optional[float] = None
    original_deadline: date
    lecturer_ids: List[int] = Field(..., min_length=1)
    lead_lecturer_id: Optional[int] = None
    reviewer_id: Optional[int] = None
    member_notes: Optional[Dict[str, str]] = None
    plan_id: Optional[int] = None

class GroupDelegateMemberItem(BaseModel):
    lecturer_id: int
    member_task_note: Optional[str] = None

class GroupDelegateRequest(BaseModel):
    members: List[GroupDelegateMemberItem]
    lead_lecturer_id: Optional[int] = None

class TaskRiskPreviewRequest(BaseModel):
    title: Optional[str] = "Dự kiến phân công"
    task_type_id: int
    scale: Optional[str] = "quy mô chuẩn"
    priority: Optional[str] = "Trung bình"
    complexity: Optional[str] = "Trung bình"
    original_deadline: date
    lecturer_ids: Optional[List[int]] = None
    subtask_count: Optional[int] = 1
    dependency_count: Optional[int] = 0
    require_external_input: Optional[bool] = False
    require_approval: Optional[bool] = False
    assignment_level: Optional[str] = "Khoa"
    assignment_channel: Optional[str] = "Hệ thống"

class ProgressUpdateCreate(BaseModel):
    progress_pct: int = Field(..., ge=0, le=100)
    note: Optional[str] = None
    lecturer_id: Optional[int] = None
    evidence_file_name: Optional[str] = None
    evidence_file_url: Optional[str] = None

# --- Extension ---
class ExtensionCreate(BaseModel):
    reason: str
    proposed_deadline: date

class ExtensionReview(BaseModel):
    status: str  # Đã duyệt / Từ chối
    review_note: Optional[str] = None

# --- School Catalog ---
class SchoolCatalogCreate(BaseModel):
    code: str
    name: str
    conversion_hours: float
    task_type_id: Optional[int] = None
    note: Optional[str] = None
