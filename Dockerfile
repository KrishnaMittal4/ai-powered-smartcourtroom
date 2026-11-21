# ==============================================================================
# AI-Powered Smart Courtroom - Backend Container
# Python 3.10-slim runtime matching Render production environment
# ==============================================================================

FROM python:3.10-slim

# Prevent Python from writing .pyc files and force unbuffered standard I/O for container logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install essential system libraries:
# - tesseract-ocr: Optical Character Recognition for scanned notices & evidence
# - poppler-utils: PDF rendering utilities (pdftoppm, pdftotext)
# - libgomp1: GNU OpenMP runtime required by FAISS vector search
# - curl: Required for container health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user & group for secure container execution
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Optimize layer caching: Install Python dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code with correct non-root ownership
COPY --chown=appuser:appuser . .

# Ensure storage directories exist with write permissions for non-root user
RUN mkdir -p /app/cases_storage /app/judgments && \
    chown -R appuser:appuser /app

# Switch to non-root execution
USER appuser

# Expose default port
EXPOSE 8000

# Container Healthcheck targeting the FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Graceful shutdown: Use exec so uvicorn receives SIGTERM directly
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
