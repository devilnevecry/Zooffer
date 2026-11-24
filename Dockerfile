# Full Zooffer application image: FastAPI backend + Telegram bot.
# Build from the repository root:
#   docker build -t zooffer/app:latest -f Dockerfile .
# The API runs by default; the bot container overrides the command with
#   ["python", "-m", "zooffer_bot"]
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the backend package (zooffer) and the bot package (zooffer_bot).
COPY backend/ /app/
COPY bot/pyproject.toml /tmp/bot/pyproject.toml
COPY bot/zooffer_bot/ /tmp/bot/zooffer_bot/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /app \
    && pip install --no-cache-dir /tmp/bot \
    && rm -rf /tmp/bot

# Operational scripts (seed, admin bootstrap) are run with `docker compose run`.
COPY scripts/ /app/scripts/

EXPOSE 8000 8081

CMD ["uvicorn", "zooffer.main:app", "--host", "0.0.0.0", "--port", "8000"]
