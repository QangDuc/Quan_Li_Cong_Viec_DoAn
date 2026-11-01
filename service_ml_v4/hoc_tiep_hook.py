"""Móc ghi dự đoán/kết quả/can thiệp vào kho phản hồi của hoc_tiep (TÙY CHỌN, đặt vào app/ của backend).
Bật bằng biến môi trường:  HOC_TIEP_DB=/duong/dan/feedback.db   HOC_TIEP_PATH=/duong/dan/hoc_tiep_mlops
Không đặt HOC_TIEP_DB thì mọi hàm là no-op. Mỗi lần gọi mở một kết nối SQLite riêng (an toàn khi backend chạy nhiều luồng)."""
import os
import sys

import pandas as pd


def _store():
    db = os.environ.get("HOC_TIEP_DB", "").strip()
    if not db:
        return None
    path = os.environ.get("HOC_TIEP_PATH", "").strip()
    if path and path not in sys.path:
        sys.path.insert(0, path)
    from hoc_tiep import FeedbackStore
    return FeedbackStore(db)


def log_prediction(task_id, lecturer_id, features: dict, assigned_at, probability, level, model_version) -> bool:
    """Gọi sau khi /predict trả 200. `features` = đúng dict đã gửi cho dịch vụ (đặc trưng LÚC GIAO VIỆC, gồm cả đặc trưng ma trận).
    Kho chỉ giữ dự đoán đầu tiên của mỗi (việc, giảng viên)."""
    st = _store()
    if st is None:
        return False
    try:
        row = dict(features)
        row.update(task_id=str(task_id), lecturer_id=str(lecturer_id), assigned_date=pd.Timestamp(assigned_at).normalize())
        st.log_predictions(pd.DataFrame([row]), [float(probability)], [level], str(model_version), kind="static", predicted_at=assigned_at)
        return True
    finally:
        st.close()


def record_outcome(task_id, lecturer_id, completed_at, is_late) -> bool:
    """Gọi khi phân công hoàn thành. is_late: hoàn thành SAU hạn gốc (original_deadline), cùng định nghĩa nhãn lúc huấn luyện."""
    st = _store()
    if st is None:
        return False
    try:
        st.record_outcomes(pd.DataFrame([dict(task_id=str(task_id), lecturer_id=str(lecturer_id), completed_date=completed_at, is_late=int(bool(is_late)))]))
        return True
    finally:
        st.close()


def record_intervention(task_id, lecturer_id, action="") -> bool:
    """Gọi khi người quản lý can thiệp (nới hạn, đổi người, nhắc việc...): việc đó bị loại khỏi dữ liệu huấn luyện lại (chính sách 'exclude')."""
    st = _store()
    if st is None:
        return False
    try:
        st.record_intervention(task_id, lecturer_id, action=action)
        return True
    finally:
        st.close()
