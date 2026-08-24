# syntax=docker/dockerfile:1
FROM python:3.13-slim

WORKDIR /app

# Set environment variables for Cloud Run
ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PYTHONDONTWRITEBYTECODE=1

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install core runtime python packages
COPY pyproject.toml ./
RUN pip install --no-cache-dir pyyaml google-cloud-bigquery matplotlib

# Copy repository source files
COPY . .

# Expose Cloud Run default port
EXPOSE 8080

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/healthz || exit 1

# Start the Telco Enterprise Agents server
CMD ["python", "server.py"]
