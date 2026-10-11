from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TaskRiskInput(BaseModel):
    """Thông tin đầu vào cho một nhiệm vụ được phân công để dự đoán rủi ro."""
    task_id: str = Field(..., description="Mã công việc/nhiệm vụ (ví dụ: T037961)")
    lecturer_id: str = Field(..., description="Mã giảng viên được phân công (ví dụ: GV226)")
    faculty: Optional[str] = Field("CNTT", description="Khoa (ví dụ: CNTT, K01..K06)")
    department: Optional[str] = Field(None, description="Bộ môn trực thuộc (ví dụ: Công nghệ phần mềm, Mạng máy tính)")
    assigned_date: Optional[str] = Field(None, description="Ngày giao việc (định dạng YYYY-MM-DD)")
    
    # Thuộc tính công việc
    task_group: Optional[str] = Field(None, description="Nhóm công việc (ví dụ: Cố vấn học tập, Hướng dẫn SV, Đào tạo)")
    task_type: Optional[str] = Field(None, description="Loại công việc cụ thể")
    task_subtype: Optional[str] = Field(None, description="Chi tiết loại công việc")
    priority: Optional[str] = Field("Trung bình", description="Mức độ ưu tiên: Thấp, Trung bình, Cao, Khẩn cấp")
    complexity: Optional[str] = Field("Trung bình", description="Độ phức tạp: Thấp, Trung bình, Cao")
    
    # Đặc tả thời hạn và khối lượng
    available_days: Optional[float] = Field(7.0, description="Số ngày có sẵn để hoàn thành deadline")
    working_days_available: Optional[float] = Field(None, description="Số ngày làm việc thực tế")
    estimated_effort_hours: Optional[float] = Field(10.0, description="Ước lượng số giờ làm việc cần thiết")
    deadline_pressure: Optional[float] = Field(None, description="Chỉ số áp lực deadline (tỷ lệ thời gian)")
    converted_workload: Optional[float] = Field(None, description="Khối lượng công việc theo thang quy đổi của trường")
    
    # Ràng buộc nghiệp vụ
    subtask_count: Optional[float] = Field(1.0, description="Số lượng đầu việc con")
    dependency_count: Optional[float] = Field(0.0, description="Số lượng bên phụ thuộc")
    require_external_input: Optional[float] = Field(0.0, description="Có cần đầu vào từ bên ngoài (1: Có, 0: Không)")
    require_approval: Optional[float] = Field(0.0, description="Cần phê duyệt từ cấp trên (1: Có, 0: Không)")
    team_size: Optional[float] = Field(1.0, description="Số lượng người tham gia")
    
    # Ngữ cảnh học kỳ / thời điểm
    academic_period: Optional[str] = Field("mid_semester", description="Giai đoạn học kỳ: semester_start, mid_semester, semester_end, summer")
    peak_season: Optional[int] = Field(0, description="Thời điểm cao điểm chấm thi/báo cáo (1: Có, 0: Không)")
    
    # Trạng thái hiện tại của giảng viên (nếu ASP.NET có sẵn từ CSDL)
    active_tasks: Optional[float] = Field(None, description="Số việc hiện đang mở của giảng viên")
    active_high_priority_tasks: Optional[float] = Field(None, description="Số việc ưu tiên cao đang mở")
    overdue_open_tasks: Optional[float] = Field(None, description="Số việc đang bị trễ hạn")
    deadlines_next_7d: Optional[float] = Field(None, description="Số việc đến hạn trong 7 ngày tới")
    deadlines_next_14d: Optional[float] = Field(None, description="Số việc đến hạn trong 14 ngày tới")
    workload_next_14d: Optional[float] = Field(None, description="Khối lượng việc đến hạn trong 14 ngày tới (giờ)")
    
    # Lịch sử hiệu suất cá nhân (nếu không truyền, hệ thống tự tra cứu trong ma trận lịch sử)
    hist_count: Optional[float] = Field(None, description="Tổng số việc GV đã hoàn thành trước đây")
    hist_late_rate: Optional[float] = Field(None, description="Tỷ lệ trễ hạn lịch sử (0.0 đến 1.0)")
    hist_avg_delay: Optional[float] = Field(None, description="Số ngày trễ trung bình khi bị trễ")
    late_last_30d: Optional[float] = Field(None, description="Số việc trễ trong 30 ngày gần nhất")
    
    extra_features: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Các đặc trưng mở rộng bổ sung")


class TaskRiskResponse(BaseModel):
    """Kết quả dự đoán rủi ro cho một phân công công việc."""
    task_id: str
    lecturer_id: str
    risk_probability: float = Field(..., description="Xác suất trễ hạn dự đoán (0.0 - 1.0)")
    risk_level: str = Field(..., description="Mức độ rủi ro: Thấp, Trung bình, Cao")
    risk_uncertainty: Optional[float] = Field(None, description="Độ bất định của mô hình (độ lệch chuẩn giữa các túi)")
    top_factors: Optional[str] = Field(None, description="Các yếu tố chính làm tăng / giảm rủi ro để giải thích cho người dùng")
    notes: Optional[str] = Field(None, description="Ghi chú cảnh báo (ví dụ: GV mới, thiếu lịch sử)")


class BatchTaskRiskRequest(BaseModel):
    tasks: List[TaskRiskInput]


class BatchTaskRiskResponse(BaseModel):
    total: int
    results: List[TaskRiskResponse]


class LecturerCandidate(BaseModel):
    lecturer_id: str
    lecturer_name: Optional[str] = None
    department: Optional[str] = None
    active_tasks: Optional[float] = None
    overdue_open_tasks: Optional[float] = None


class RecommendationRequest(BaseModel):
    """Yêu cầu gợi ý giảng viên tối ưu nhất để giao công việc."""
    task: TaskRiskInput
    candidate_lecturers: List[LecturerCandidate] = Field(..., description="Danh sách các giảng viên ứng viên cần xem xét")


class RecommendationItem(BaseModel):
    rank: int
    lecturer_id: str
    lecturer_name: Optional[str] = None
    department: Optional[str] = None
    risk_probability: float
    risk_level: str
    risk_uncertainty: Optional[float] = None
    top_factors: Optional[str] = None
    recommendation_note: str


class RecommendationResponse(BaseModel):
    task_id: str
    recommended_candidates: List[RecommendationItem]


class ModelInfoResponse(BaseModel):
    model_name: str
    version: str
    trained_at: Optional[str] = None
    device: str
    n_bags: int
    thresholds: List[float]
    metrics: Dict[str, Any]
