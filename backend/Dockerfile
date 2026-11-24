# API-only image. Build from the backend directory:
#   docker build -t zooffer/backend:latest backend
# The production compose file uses the combined image built from the repository
# root Dockerfile (API + bot), because the Telegram bot imports zooffer.config.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY zooffer/ /app/zooffer/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/alembic.ini

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir /app

EXPOSE 8000

CMD ["uvicorn", "zooffer.main:app", "--host", "0.0.0.0", "--port", "8000"]
