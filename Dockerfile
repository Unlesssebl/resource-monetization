FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgomp1 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# Copy project package and scripts
COPY src/ ./src/
COPY configs/ ./configs/
COPY scripts/ ./scripts/

RUN mkdir -p /app/data /app/logs

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src:/app

CMD ["python", "scripts/run_bot.py"]