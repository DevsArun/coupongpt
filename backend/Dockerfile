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

# Only curl is needed at runtime (healthcheck). All Python deps ship as wheels
# (aiomysql, lxml, bcrypt, etc.) so no compiler/build toolchain is required —
# this keeps Hugging Face Spaces builds fast and the image small.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Non-root user (uid 1000 matches the Hugging Face Spaces convention).
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# HF Spaces routes to the port declared by `app_port` in the Space README.
# Keep this in sync (this image + compose use 8000; set app_port: 8000).
EXPOSE 8000
ENV PORT=8000 \
    WEB_CONCURRENCY=1

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT}/api/v1/health" || exit 1

# --proxy-headers + --forwarded-allow-ips make X-Forwarded-For trustworthy behind
# a reverse proxy/load balancer (pair with TRUST_PROXY_HEADERS=true).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers ${WEB_CONCURRENCY} --proxy-headers --forwarded-allow-ips='*'"]
