FROM python:3.12-slim AS base

# Install system dependencies (FFmpeg for audio/video, libgomp for OpenMP, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgomp1 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium & dependencies
RUN playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# Copy project code
COPY shared/ ./shared/
COPY services/ ./services/
COPY configs/ ./configs/
COPY manage.py .

# Create persistent data and log directories
RUN mkdir -p /app/data /app/logs

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "manage.py", "status"]