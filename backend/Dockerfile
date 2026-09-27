# ====================================================================
# AI-RCI Backend - Python FastAPI Microservice
# ====================================================================
# Build:  docker build -f Dockerfile.backend -t airci-backend .
# Run:    docker run -p 8000:8000 airci-backend
# ====================================================================

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install standard system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list first (Docker caching optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend source code
COPY main.py .
COPY agent/ ./agent/
COPY config/ ./config/
COPY lambda_/ ./lambda_/
COPY shared/ ./shared/
COPY .env.example ./.env

# Expose the FastAPI port
EXPOSE 8000

# Health check for container orchestrators
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start the FastAPI server
CMD ["python", "main.py"]
