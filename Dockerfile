FROM python:3.10-slim

WORKDIR /app

# Cài đặt các gói hệ thống cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements và cài dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code, model và data
COPY service/ ./service/
COPY model/ ./model/
COPY data/ ./data/

EXPOSE 8000

ENV HOST=0.0.0.0
ENV PORT=8000

CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8000"]
