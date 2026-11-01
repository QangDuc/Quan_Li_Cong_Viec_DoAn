# CPU: chỉ phù hợp bản demo ML_ENGINE=surrogate_hgb
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY service/ml_service.py ./service/ml_service.py
COPY model/ ./model/

ENV PYTHONIOENCODING=utf-8
EXPOSE 8001

# Một worker: mô hình TabPFN nạp một lần (4 túi x 10.000 dòng); nhiều worker nhân bản bộ nhớ GPU/CPU.
# TabPFN trên CPU rất chậm; để chạy bản đã đánh giá hãy dùng image có CUDA (ví dụ pytorch/pytorch:*-cuda*-runtime) và đặt TABPFN_DEVICE=cuda.
CMD ["uvicorn", "service.ml_service:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
