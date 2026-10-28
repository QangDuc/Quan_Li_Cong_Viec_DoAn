import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from backend import ml_service

print("=== 1. TAI MO HINH VA THONG TIN PHIEN BAN ===")
print("File mo hinh:", ml_service.MODEL_PATH)
if os.path.exists(ml_service.METRICS_PATH):
    with open(ml_service.METRICS_PATH, "r", encoding="utf-8") as f:
        metrics = json.load(f)
        print("Model Name:", metrics.get("model_name", "risk_model"))
        print("Tập Test ROC-AUC:", metrics.get("test_roc_auc", metrics.get("auc", "N/A")))
        print("Brier Score:", metrics.get("test_brier", metrics.get("brier", "N/A")))
        print("Ngưỡng phân loại:", metrics.get("thresholds", "[0.23, 0.52]"))

wrapper = ml_service.model_wrapper

# Ca 1: Công việc bình thường, giảng viên có kinh nghiệm, tiến độ tốt
sample_normal = {
    "task_group": "Giảng dạy",
    "task_type": "Giảng dạy học phần",
    "scale": "quy mô chuẩn",
    "priority": "Trung bình",
    "complexity": "Trung bình",
    "deadline_pressure": 0.85,
    "available_days": 20,
    "expected_duration_days": 15,
    "active_tasks": 2,
    "workload_next_14d": 18,
    "deadlines_next_7d": 1,
    "hist_count": 25,
    "hist_late_rate": 0.04,
    "years_experience": 8,
    "student_count": 80,
    "department": "K01 - Công nghệ phần mềm"
}

res1 = wrapper.predict(sample_normal)
print("\n=== 2. THU NGHIEM CA 1 (Cong viec chuan, rui ro thap) ===")
print(f"Xac suat tre han: {res1['probability'] * 100:.1f}%")
print(f"Phan loai rui ro: {res1['level']}")
print(f"Do khong chac chan: {res1.get('uncertainty', 0):.4f}")
print("Giai thich yeu to anh huong:")
for p in res1.get("top_factors", []):
    print(f"  • {p}")
print(f"Khuyen nghi: {res1.get('recommendation')}")

# Ca 2: Công việc giao gấp, khối lượng dồn dập, tiền sử hay trễ
sample_urgent = {
    "task_group": "Hành chính & Khác",
    "task_type": "Báo cáo đột xuất",
    "scale": "quy mô lớn",
    "priority": "Khẩn cấp",
    "complexity": "Phức tạp",
    "deadline_pressure": 2.40,
    "available_days": 2,
    "expected_duration_days": 5,
    "active_tasks": 9,
    "overdue_open_tasks": 2,
    "workload_next_14d": 65,
    "deadlines_next_7d": 5,
    "hist_count": 18,
    "hist_late_rate": 0.45,
    "years_experience": 1,
    "department": "K02 - Hệ thống thông tin"
}

res2 = wrapper.predict(sample_urgent)
print("\n=== 3. THU NGHIEM CA 2 (Giao gap, qua tai, rui ro cao) ===")
print(f"Xac suat tre han: {res2['probability'] * 100:.1f}%")
print(f"Phan loai rui ro: {res2['level']}")
print(f"Do khong chac chan: {res2.get('uncertainty', 0):.4f}")
print("Giai thich yeu to anh huong:")
for p in res2.get("top_factors", []):
    print(f"  • {p}")
print(f"Khuyen nghi: {res2.get('recommendation')}")
