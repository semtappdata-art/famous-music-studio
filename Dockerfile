# Dockerfile for Famous Music Studio
FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Copy project
COPY . .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Download models
RUN ollama pull gemma2:2b || true
RUN ollama pull phi3.5:latest || true
RUN ollama pull qwen3.5:4b || true

# Env file
COPY .env .env

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run
CMD ["python", "auto_process.py"]