# =============================================================================
# SenatDigit Apps API - Multi-stage Dockerfile
# Supports: local, development (dev), production (prod)
# Python 3.11 + FastAPI + Gunicorn/Uvicorn
# =============================================================================

# ---------------------
# Stage 1: Base image
# ---------------------
FROM python:3.11-slim AS base

# System dependencies for WeasyPrint, Pango, Cairo, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libcairo2-dev \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    libfontconfig1 \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# ---------------------
# Stage 2: App image
# ---------------------
FROM base AS app

WORKDIR /app

# Copy the entire application
COPY . .

# Make bash scripts executable
RUN find bash/ -name "*.sh" -exec chmod +x {} + 2>/dev/null || true

# Create logs directory
RUN mkdir -p logs bash/seeds/logs

# Default environment variables (overridable via docker-compose / .env)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Expose default port (overridden per env)
EXPOSE 9888

# Use the entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Run as non-root
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser \
    && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${APP_PORT:-9888}/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["serve"]
