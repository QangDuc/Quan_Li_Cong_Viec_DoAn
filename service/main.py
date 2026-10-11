import logging
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from service.config import PORT, HOST
from service.schemas import (
    TaskRiskInput, TaskRiskResponse,
    BatchTaskRiskRequest, BatchTaskRiskResponse,
    RecommendationRequest, RecommendationResponse,
    ModelInfoResponse
)
from service.predictor import predictor

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="HUIT Task Risk Prediction & Assignment API",
    description="Dịch vụ Học máy dự đoán rủi ro trễ hạn và tối ưu hóa phân công công việc giảng viên - Đồ án Khóa luận CNTT-KLCN184",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Kích hoạt CORS để ASP.NET Core hoặc Single Page App gọi trực tiếp
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Hệ thống"])
def root():
    return {
        "service": "HUIT Task Risk Prediction API",
        "status": "online",
        "docs": "/docs",
        "model_loaded": predictor.bundle is not None,
        "is_tabpfn_available": predictor.is_tabpfn_available
    }


@app.get("/health", tags=["Hệ thống"])
def health_check():
    return {
        "status": "healthy",
        "model_loaded": predictor.bundle is not None
    }


@app.get("/api/model-info", response_model=ModelInfoResponse, tags=["Thông tin mô hình"])
def get_model_info():
    """Lấy thông số chi tiết của mô hình, độ chính xác thực nghiệm (AUC, Brier) và các ngưỡng cảnh báo."""
    meta = predictor.bundle.get("meta", {}) if predictor.bundle else {}
    return ModelInfoResponse(
        model_name="TabPFN v2 (In-Context Foundation Model for Tabular Data)",
        version=predictor.bundle.get("tabpfn_version", "v2") if predictor.bundle else "v2",
        trained_at=meta.get("trained_at"),
        device="cuda" if predictor.is_tabpfn_available else "cpu",
        n_bags=len(predictor.bundle.get("contexts", [])) if predictor.bundle else 4,
        thresholds=predictor.thresholds,
        metrics=predictor.metrics
    )


@app.post("/api/predict", response_model=TaskRiskResponse, tags=["Dự đoán rủi ro"])
def predict_single_task(task: TaskRiskInput):
    """
    Dự đoán xác suất trễ hạn cho một công việc được phân công.
    Trả về xác suất (0.0 - 1.0), mức độ rủi ro (Thấp / Trung bình / Cao) và các yếu tố giải thích (top factors).
    """
    try:
        return predictor.predict_single(task)
    except Exception as e:
        logger.error(f"Lỗi khi dự đoán: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Đã xảy ra lỗi khi xử lý dự đoán: {str(e)}"
        )


@app.post("/api/predict-batch", response_model=BatchTaskRiskResponse, tags=["Dự đoán rủi ro"])
def predict_batch_tasks(batch: BatchTaskRiskRequest):
    """Dự đoán rủi ro cho một danh sách nhiều công việc cùng lúc."""
    try:
        results = predictor.predict_batch(batch.tasks)
        return BatchTaskRiskResponse(total=len(results), results=results)
    except Exception as e:
        logger.error(f"Lỗi khi dự đoán batch: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Đã xảy ra lỗi khi xử lý dự đoán batch: {str(e)}"
        )


@app.post("/api/recommend-assignee", response_model=RecommendationResponse, tags=["Tối ưu phân công"])
def recommend_optimal_assignee(request: RecommendationRequest):
    """
    Đánh giá danh sách giảng viên ứng viên và đề xuất người phân công tối ưu nhất 
    (xếp hạng theo mức độ rủi ro trễ hạn thấp nhất).
    """
    if not request.candidate_lecturers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Danh sách giảng viên ứng viên không được để trống."
        )
    try:
        return predictor.recommend_candidates(request.task, request.candidate_lecturers)
    except Exception as e:
        logger.error(f"Lỗi khi đề xuất giảng viên: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Đã xảy ra lỗi khi đề xuất ứng viên: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("service.main:app", host=HOST, port=PORT, reload=True)
