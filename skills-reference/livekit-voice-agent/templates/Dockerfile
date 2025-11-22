# LiveKit Voice Agent - Production Dockerfile

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/

# Copy environment file (optional - prefer using Docker secrets/env vars)
# COPY .env ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Expose port (if needed for health checks)
# EXPOSE 8080

# Health check (optional)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD curl -f http://localhost:8080/health || exit 1

# Run the agent
CMD ["uv", "run", "python", "src/agent.py", "start"]
