# ==============================================================================
# ZENMARK APEX OUTBOUND — PRODUCTION DOCKERFILE (FORGE v5.8)
# Zero-Cost Sovereign Container for Render, Railway, Fly.io, or VPS
# ==============================================================================

FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install minimal OS dependencies for network & crypto
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source & dashboard
COPY src /app/src
COPY dashboard /app/dashboard
COPY workflows /app/workflows
COPY sql /app/sql
COPY zenmark_local_store.json /app/
COPY .env.example /app/

# Expose standard web port
EXPOSE 8000

# Non-root user execution for security hardening
RUN useradd -u 1001 zenmark && chown -R zenmark:zenmark /app
USER zenmark

# Run Uvicorn directly
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
