# Famous Music Studio - Production Dockerfile
# Multi-stage build for optimal size

# Stage 1: Build
FROM python:3.12-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends     ffmpeg     git     curl     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production
FROM python:3.12-slim AS production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends     ffmpeg     git     curl     && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application
COPY . .

# Create directories
RUN mkdir -p /app/projects /app/gorev_izleri /app/upload /app/backup

# Environment variables
ENV PYTHONUNBUFFERED=1     PYTHONDONTWRITEBYTECODE=1     TZ=Europe/Istanbul

# Health check
HEALTHCHECK --interval=60s --timeout=30s --start-period=10s --retries=3     CMD python -c "import saglik_kontrol; print('OK')" || exit 1

# Non-root user for security
RUN useradd -m -u 1000 famous && chown -R famous:famous /app
USER famous

# Run
CMD ["python", "auto_process.py"]
