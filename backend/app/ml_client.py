"""
Client gọi sang ML Service (port 8001) với cơ chế timeout, fallback và lưu lịch sử dự đoán (FR-10).
Nếu ML Service lỗi hoặc quá timeout:
- Giao việc vẫn thành công.
- Lưu bản ghi RiskPrediction trạng thái 'pending' hoặc 'failed' với ghi chú 'chưa có dự đoán'.
"""
import time
import json
import logging
import httpx
from datetime import datetime
from sqlalchemy.orm import Session

from app import config
from app.models import RiskPrediction, Notification, User, ROLE_MANAGER
from app.ml_extract import extract_features_for_assignment

logger = logging.getLogger("ml_client")

def predict_and_record_risk(
    db: Session,
    task_id: int,
    assignment_id: int,
    lecturer_id: int,
    trigger: str = "assign",
    timeout: float | None = None
) -> RiskPrediction:
    timeout = timeout or config.ML_TIMEOUT_SECONDS
    pred_record = RiskPrediction(
        task_id=task_id,
        assignment_id=assignment_id,
        lecturer_id=lecturer_id,
        trigger=trigger,
        status="pending",
        created_at=datetime.now()
    )
    db.add(pred_record)
    db.flush()

    try:
        t0 = time.time()
        features = extract_features_for_assignment(db, task_id, lecturer_id, at=pred_record.created_at)
        pred_record.features_json = json.dumps(features, ensure_ascii=False)

        # Gọi ML Service
        url = f"{config.ML_SERVICE_URL.rstrip('/')}/predict"
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json={"features": features})

        elapsed_ms = int((time.time() - t0) * 1000)
        pred_record.latency_ms = elapsed_ms

        if resp.status_code == 200:
            data = resp.json()
            pred_record.status = "ok"
            pred_record.probability = data.get("probability")
            pred_record.level = data.get("level")
            pred_record.uncertainty = data.get("uncertainty")
            pred_record.top_factors = json.dumps(data.get("top_factors", []), ensure_ascii=False)
            pred_record.recommendation = data.get("recommendation")
            pred_record.low_confidence = data.get("low_confidence", False)
            pred_record.model_version = data.get("model_version")
            pred_record.predicted_at = datetime.now()

            # Thông báo chủ động cho Quản lý nếu rủi ro Cao (UC-02)
            if pred_record.level == "Cao":
                _notify_manager_high_risk(db, task_id, lecturer_id, pred_record)
        else:
            pred_record.status = "failed"
            pred_record.error = f"HTTP {resp.status_code}: {resp.text[:300]}"
            pred_record.notes = "chưa có dự đoán (ML service báo lỗi)"

    except httpx.TimeoutException:
        pred_record.status = "failed"
        pred_record.error = f"Quá thời gian phản hồi ({timeout}s)"
        pred_record.notes = "chưa có dự đoán (quá thời gian chờ)"
        logger.warning(f"ML predict timeout cho task {task_id}, assignment {assignment_id}")

    except Exception as e:
        pred_record.status = "failed"
        pred_record.error = str(e)[:400]
        pred_record.notes = "chưa có dự đoán (không kết nối được ML service)"
        logger.error(f"Lỗi khi gọi ML service: {e}")

    db.commit()
    db.refresh(pred_record)
    return pred_record


def _notify_manager_high_risk(db: Session, task_id: int, lecturer_id: int, pred: RiskPrediction):
    lecturer = db.get(User, lecturer_id)
    dept_id = lecturer.department_id if lecturer else None

    # Tìm các managers quản lý giảng viên này
    query = db.query(User).filter(User.role == ROLE_MANAGER, User.is_active == True)
    if dept_id:
        managers = query.filter((User.department_id == dept_id) | (User.department_id == None)).all()
    else:
        managers = query.all()

    for mgr in managers:
        notif = Notification(
            user_id=mgr.id,
            kind="risk_high",
            title="Cảnh báo rủi ro trễ hạn: Mức Cao",
            content=(
                f"Công việc được giao cho {lecturer.full_name if lecturer else lecturer_id} "
                f"được mô hình dự đoán có rủi ro trễ hạn mức CAO ({pred.probability*100:.1f}%). "
                f"Khuyến nghị: {pred.recommendation}"
            ),
            task_id=task_id,
            dedupe_key=f"risk_high:{pred.id}:{mgr.id}"
        )
        db.add(notif)


def preview_risk_for_features(features: dict, timeout: float | None = None) -> dict:
    """Gọi ML Service để xem trước rủi ro trễ hạn trước khi xác nhận giao việc."""
    timeout = timeout or config.ML_TIMEOUT_SECONDS
    t0 = time.time()
    try:
        url = f"{config.ML_SERVICE_URL.rstrip('/')}/predict"
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json={"features": features})
        elapsed_ms = int((time.time() - t0) * 1000)
        if resp.status_code == 200:
            data = resp.json()
            data["status"] = "ok"
            data["latency_ms"] = elapsed_ms
            return data
        return {
            "status": "failed",
            "probability": None,
            "level": "Chưa có dự đoán",
            "uncertainty": None,
            "top_factors": [],
            "recommendation": "Không kết nối được dịch vụ dự đoán ML. Vẫn có thể giao việc bình thường.",
            "low_confidence": False,
            "error": f"HTTP {resp.status_code}"
        }
    except Exception as e:
        return {
            "status": "failed",
            "probability": None,
            "level": "Chưa có dự đoán",
            "uncertainty": None,
            "top_factors": [],
            "recommendation": "Dịch vụ ML tạm thời không phản hồi. Vẫn có thể giao việc bình thường.",
            "low_confidence": False,
            "error": str(e)[:200]
        }
