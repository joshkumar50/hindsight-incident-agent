FROM hindsight_agent-python-base:latest

# Set service name via build arg
ARG SERVICE_NAME
ARG dir
ENV SERVICE_NAME=${SERVICE_NAME}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared core libraries
COPY pkg /app/pkg

# Copy service code
COPY $dir /app/src
WORKDIR /app/src
ENV PYTHONPATH=/app:/app/src

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:8000/health || exit 1
