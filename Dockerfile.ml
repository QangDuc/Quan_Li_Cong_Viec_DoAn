FROM python:3.10-bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn pydantic

COPY features.py ./
COPY train_model.py ./
COPY backend/ml_service.py ./backend/
COPY model/ ./model/
COPY data/ ./data/

ENV PYTHONIOENCODING=utf-8
EXPOSE 8001

CMD ["uvicorn", "backend.ml_service:app", "--host", "0.0.0.0", "--port", "8001"]
