# =====================================================================
# CouponGPT backend — single image, runs on Hugging Face Spaces or VPS.
# HF Spaces expects the app to listen on $PORT (default 7860); we honour it.
# =====================================================================
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps for asyncmy (MySQL) and lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential default-libmysqlclient-dev pkg-config \
        libxml2-dev libxslt1-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
# PORT lets HF Spaces (7860) and other hosts override the listen port.
# WEB_CONCURRENCY controls worker count (set >1 in production behind a proxy).
ENV PORT=8000 \
    WEB_CONCURRENCY=1

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT}/api/v1/health" || exit 1

# --proxy-headers + --forwarded-allow-ips make X-Forwarded-For trustworthy behind
# a reverse proxy/load balancer (pair with TRUST_PROXY_HEADERS=true).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers ${WEB_CONCURRENCY} --proxy-headers --forwarded-allow-ips='*'"]
