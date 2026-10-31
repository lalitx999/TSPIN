# Multi-stage production build for TSPI Clinical Monolith (Python 3.12 + WeasyPrint)
# Enforces Security Isolation & Minimal Attack Surface (Pillars 6, 14)

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /install

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /install/
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt


# Final Runtime Stage
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/deps/bin:$PATH" \
    PYTHONPATH="/install/deps/lib/python3.12/site-packages:$PYTHONPATH"

WORKDIR /app

# Install runtime system libraries required by PostgreSQL and WeasyPrint (Pango, HarfBuzz, Fontconfig)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libjpeg62-turbo \
    libopenjp2-7 \
    libffi8 \
    fonts-sarabun \
    fonts-liberation \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from builder
COPY --from=builder /install/deps /install/deps

# Create unprivileged system user (Pillar 6: Never run as root)
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser

# Copy application source code
COPY . /app/

# Ensure directories for static, media, and logs exist and have correct ownership
RUN mkdir -p /app/staticfiles /app/media /app/private_media /app/logs && \
    chmod +x /app/entrypoint.sh && \
    chown -R appuser:appgroup /app

# Switch to unprivileged user
USER appuser

EXPOSE 8000

# Healthcheck for container orchestrators
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Entrypoint script that migrates, collects static, and starts Gunicorn
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
