# ==============================================================================
# InfraScan Backend Production Dockerfile
# Multi-stage / optimized Python container for AI Civil Infrastructure Platform
# ==============================================================================

FROM python:3.11-slim

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies required by OpenCV, PyTorch, and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy application source code
COPY backend /app/backend
COPY scripts /app/scripts
COPY models /app/models

# Create data directories with appropriate permissions
RUN mkdir -p /app/data/uploads /app/data/results /app/data/reports

# Set environment paths
ENV PYTHONPATH=/app/backend:/app
ENV INFRASCAN_STORAGE_DIR=/app/data
ENV INFRASCAN_DB_PATH=/app/data/infrascan.db
ENV INFRASCAN_UPLOAD_DIR=/app/data/uploads
ENV INFRASCAN_RESULTS_DIR=/app/data/results
ENV INFRASCAN_REPORTS_DIR=/app/data/reports
ENV INFRASCAN_MODELS_DIR=/app/models

# Expose FastAPI backend port
EXPOSE 8000

# Healthcheck to verify FastAPI responsiveness
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Production startup command using Uvicorn without reload
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
