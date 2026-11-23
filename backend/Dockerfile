FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/ /app/backend/

RUN pip install --no-cache-dir -e /app/backend

EXPOSE 8000
CMD ["uvicorn", "zooffer.main:app", "--host", "0.0.0.0", "--port", "8000"]
