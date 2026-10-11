import sys
import os
import io
from pathlib import Path

# Đảm bảo console Windows in được tiếng Việt UTF-8
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Thêm thư mục hiện tại vào sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from service.schemas import TaskRiskInput, LecturerCandidate, RecommendationRequest
from service.predictor import predictor

def main():
    print("=== KIỂM TRA TASK RISK PREDICTION SERVICE ===")
    print(f"Model loaded: {predictor.bundle is not None}")
    print(f"Thresholds: {predictor.thresholds}")
    print(f"TabPFN available: {predictor.is_tabpfn_available}")

    # Test 1: Single Task Prediction
    sample_task = TaskRiskInput(
        task_id="T_TEST_001",
        lecturer_id="GV226",
        faculty="CNTT",
        department="K05 - Công nghệ phần mềm",
        task_type="Xử lý cảnh báo học vụ của SV",
        priority="Cao",
        complexity="Cao",
        available_days=5.0,
        estimated_effort_hours=20.0,
        active_tasks=14.0,
        overdue_open_tasks=1.0,
        hist_late_rate=0.35,
        hist_count=120.0
    )

    print("\n--- Test 1: Dự đoán rủi ro đơn lẻ ---")
    res = predictor.predict_single(sample_task)
    print(f"Task ID: {res.task_id}")
    print(f"Lecturer ID: {res.lecturer_id}")
    print(f"Xác suất trễ hạn: {res.risk_probability}")
    print(f"Mức độ rủi ro: {res.risk_level}")
    print(f"Top factors: {res.top_factors}")

    # Test 2: Recommendation for Multiple Candidates
    print("\n--- Test 2: Gợi ý phân công giảng viên tối ưu ---")
    candidates = [
        LecturerCandidate(lecturer_id="GV001", lecturer_name="ThS. Nguyễn Văn A", department="CNPM", active_tasks=2.0, overdue_open_tasks=0.0),
        LecturerCandidate(lecturer_id="GV002", lecturer_name="TS. Trần Thị B", department="CNPM", active_tasks=15.0, overdue_open_tasks=2.0),
        LecturerCandidate(lecturer_id="GV003", lecturer_name="ThS. Lê Văn C", department="CNPM", active_tasks=7.0, overdue_open_tasks=0.0),
    ]

    base_task = TaskRiskInput(
        task_id="T_TEST_002",
        lecturer_id="",
        task_type="Hướng dẫn khóa luận/đồ án tốt nghiệp",
        priority="Cao",
        complexity="Cao",
        available_days=10.0,
        estimated_effort_hours=25.0
    )

    rec_res = predictor.recommend_candidates(base_task, candidates)
    for c in rec_res.recommended_candidates:
        print(f"Rank #{c.rank}: {c.lecturer_id} ({c.lecturer_name}) -> Rủi ro: {c.risk_probability} ({c.risk_level}) | {c.recommendation_note}")

    print("\n=> TẤT CẢ KIỂM TRA ĐỀU THÀNH CÔNG!")

if __name__ == "__main__":
    main()
