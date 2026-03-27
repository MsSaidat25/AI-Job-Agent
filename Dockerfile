FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies, build Python packages, then remove gcc
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev gcc && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove gcc && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m appuser

# Copy application code and set ownership
COPY --chown=appuser:appuser . .
RUN mkdir -p data

USER appuser

# Cloud Run provides $PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')" || exit 1

CMD ["sh", "-c", "exec uvicorn api:app --host 0.0.0.0 --port ${PORT} --workers ${WEB_CONCURRENCY:-2}"]
