"""Kiểm thử tích hợp luồng nghiệp vụ: Đăng nhập -> Giao việc -> Cập nhật tiến độ -> Dự đoán ML fallback an toàn."""
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_login_and_auth_flow():
    # 1. Đăng nhập với tài khoản Trưởng Khoa
    resp = client.post("/api/auth/login", json={"username": "truongkhoa", "password": "Manager@123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    token = data["access_token"]

    # 2. Lấy thông tin cá nhân
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "manager"

    # 3. Giao việc mới (khi ML service chưa bật -> fallback ghi nhận 'chưa có dự đoán', không được crash)
    task_payload = {
        "title": "Chấm thi cuối kỳ môn Lập trình Web",
        "description": "Chấm bài thi tự luận học kỳ 1",
        "task_type_id": 1,
        "priority": "Cao",
        "complexity": "Trung bình",
        "original_deadline": str(date.today() + timedelta(days=14)),
        "lecturer_ids": [3]  # ID của 1 giảng viên mẫu
    }
    task_resp = client.post("/api/tasks", json=task_payload, headers={"Authorization": f"Bearer {token}"})
    assert task_resp.status_code == 200
    res_data = task_resp.json()
    assert "task_id" in res_data
    assert len(res_data["predictions"]) > 0
    # Dự đoán trạng thái failed/pending do ML service port 8001 chưa chạy -> Giao việc vẫn thành công
    assert res_data["predictions"][0]["status"] in ["failed", "pending", "ok"]
    assert "chưa có dự đoán" in (res_data["predictions"][0]["notes"] or "")

def test_permission_isolation():
    # Giảng viên đăng nhập
    resp = client.post("/api/auth/login", json={"username": "gv_k01_1", "password": "Lecturer@123"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    # Giảng viên không có quyền giao việc mới
    task_payload = {
        "title": "Tự giao việc",
        "task_type_id": 1,
        "original_deadline": str(date.today() + timedelta(days=14)),
        "lecturer_ids": [3]
    }
    deny_resp = client.post("/api/tasks", json=task_payload, headers={"Authorization": f"Bearer {token}"})
    assert deny_resp.status_code == 403


def test_lecturer_one_year_evaluation_and_extensions():
    # Đăng nhập với tài khoản Trưởng Khoa
    resp = client.post("/api/auth/login", json={"username": "truongkhoa", "password": "Manager@123"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Tìm ID của ThS. Nguyễn Minh Khoa (gv_k01_1) và kiểm tra Hồ sơ đánh giá 1 năm
    users_resp = client.get("/api/users", headers=headers)
    assert users_resp.status_code == 200
    gv_khoa = next(u for u in users_resp.json() if u["username"] == "gv_k01_1")
    khoa_id = gv_khoa["id"]

    eval_resp = client.get(f"/api/reports/lecturer-evaluation/{khoa_id}?academic_year=2026-2027", headers=headers)
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["lecturer"]["lecturer_code"] == "GV0101"
    assert eval_data["summary"]["total_tasks"] >= 18
    assert len(eval_data["semesters"]) == 3
    assert len(eval_data["task_personnel_matrix"]) > 0
    assert eval_data["ml_audit"]["total_evaluated"] >= 10

    # 2. Kiểm tra danh sách yêu cầu gia hạn (FR-09)
    ext_resp = client.get("/api/tasks/extensions", headers=headers)
    assert ext_resp.status_code == 200
    ext_list = ext_resp.json()
    assert isinstance(ext_list, list)
    assert len(ext_list) >= 1

    # 3. Kiểm tra API preview-risk (FR-10 tối ưu phân công)
    preview_resp = client.post(
        "/api/tasks/preview-risk",
        json={
            "task_type_id": 15,
            "priority": "Cao",
            "complexity": "Phức tạp",
            "original_deadline": str(date.today() + timedelta(days=10)),
            "lecturer_ids": [3, 4, 5],
        },
        headers=headers,
    )
    assert preview_resp.status_code == 200
    candidates = preview_resp.json()["candidates"]
    assert len(candidates) == 3

    # 4. Kiểm tra tải file mẫu Kế hoạch năm Excel (FR-06)
    tpl_resp = client.get("/api/reports/plans/template?academic_year=2026-2027", headers=headers)
    assert tpl_resp.status_code == 200
    assert "spreadsheetml" in tpl_resp.headers.get("content-type", "")
