# --- Stage 1: install dependencies in a virtualenv ---
FROM python:3.13-slim AS builder
WORKDIR /build
RUN python -m venv /venv
COPY app/requirements.txt .
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

# --- Stage 2: small runtime image, no build tools, non-root user ---
FROM python:3.13-slim
ARG APP_VERSION=dev
ENV PATH="/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=$APP_VERSION
RUN useradd --create-home --uid 10001 appuser
COPY --from=builder /venv /venv
WORKDIR /app
COPY --chown=appuser:appuser app/app.py .
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status == 200 else 1)"
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "app:app"]
