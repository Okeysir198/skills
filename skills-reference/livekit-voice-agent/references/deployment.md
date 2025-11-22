# Production Deployment Guide

## Overview

LiveKit voice agents can be deployed to various platforms. This guide covers best practices for production deployment.

## Infrastructure Requirements

### Compute Resources

**Recommended starting point**:
- **CPU**: 4 cores per worker
- **Memory**: 8GB per worker
- **Storage**: 10GB ephemeral storage
- **Network**: Low-latency connection to LiveKit server

**Concurrent capacity**: Each worker can handle 10-25 concurrent sessions depending on:
- Model complexity (larger LLMs need more resources)
- Tool execution (database queries, API calls)
- Audio processing requirements

### Scaling Considerations

- Workers connect via WebSocket to LiveKit server
- No inbound ports required (outbound WebSocket only)
- Optional: Expose health check endpoint (default: http://0.0.0.0:8081)
- Scale horizontally by adding more workers

---

## Docker Deployment

### Basic Dockerfile

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY pyproject.toml .
COPY uv.lock .

# Install dependencies
RUN pip install uv
RUN uv sync --frozen

# Copy application code
COPY src/ ./src/

# Download required models at build time
RUN uv run python src/agent.py download-files

# Expose health check port (optional)
EXPOSE 8081

# Run agent worker
CMD ["uv", "run", "python", "src/agent.py", "start"]
```

### Multi-stage Build (Optimized)

```dockerfile
# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ ./src/
RUN uv run python src/agent.py download-files

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy only necessary files
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /root/.cache /root/.cache

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8081

CMD ["python", "src/agent.py", "start"]
```

### Build and Run

```bash
# Build image
docker build -t my-voice-agent:latest .

# Run container
docker run \
  -e LIVEKIT_URL=wss://your-project.livekit.cloud \
  -e LIVEKIT_API_KEY=your-api-key \
  -e LIVEKIT_API_SECRET=your-api-secret \
  -e OPENAI_API_KEY=your-openai-key \
  -e DEEPGRAM_API_KEY=your-deepgram-key \
  -e CARTESIA_API_KEY=your-cartesia-key \
  --name voice-agent \
  my-voice-agent:latest
```

---

## Environment Configuration

### Environment Variables

**Required**:
```bash
# LiveKit connection
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# Provider API keys (based on your stack)
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
CARTESIA_API_KEY=...
```

**Optional**:
```bash
# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Health check
HEALTH_CHECK_PORT=8081

# Performance tuning
WORKER_CONCURRENCY=20  # Max concurrent sessions per worker
WORKER_TIMEOUT=600     # Session timeout in seconds

# Feature flags
ENABLE_METRICS=true
ENABLE_TRACING=true
```

### Secrets Management

**Never commit secrets to git**. Use secure secret management:

**Docker Compose with .env**:
```yaml
# docker-compose.yml
version: '3.8'
services:
  agent:
    image: my-voice-agent:latest
    env_file:
      - .env.local  # Git-ignored file
    restart: unless-stopped
```

**Kubernetes Secrets**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: agent-secrets
type: Opaque
stringData:
  LIVEKIT_API_KEY: "your-api-key"
  LIVEKIT_API_SECRET: "your-api-secret"
  OPENAI_API_KEY: "sk-..."
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: voice-agent
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: agent
        image: my-voice-agent:latest
        envFrom:
        - secretRef:
            name: agent-secrets
```

**Cloud Platform Secrets** (AWS/GCP/Azure):
- AWS: Use AWS Secrets Manager or Parameter Store
- GCP: Use Secret Manager
- Azure: Use Key Vault

---

## Deployment Platforms

### LiveKit Cloud (Recommended)

**Easiest option** - fully managed agent deployment.

```bash
# Install LiveKit CLI
brew install livekit-cli  # macOS
# or download from https://github.com/livekit/livekit-cli

# Authenticate
lk cloud auth

# Deploy agent
lk cloud deploy --name my-voice-agent --dockerfile Dockerfile
```

**Features**:
- Auto-scaling based on load
- Built-in monitoring and logging
- Global edge deployment
- Zero infrastructure management
- Integrated with LiveKit Inference (model serving)

**Pricing**: Based on usage (compute + network)

---

### Render

Simple cloud deployment with Docker support.

**Steps**:
1. Connect GitHub repository
2. Create new Web Service
3. Configure:
   - **Environment**: Docker
   - **Dockerfile**: ./Dockerfile
   - **Plan**: At least 1GB RAM, 0.5 CPU
   - **Environment Variables**: Add all required keys
4. Deploy

**Auto-deploy**: Commits to main branch auto-deploy

---

### Railway

Similar to Render, with simple deployment flow.

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Deploy
railway up
```

Add environment variables in Railway dashboard.

---

### Kubernetes

For self-managed clusters (GKE, EKS, AKS, etc.).

**Deployment manifest**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: voice-agent
  labels:
    app: voice-agent
spec:
  replicas: 3  # Start with 3 workers
  selector:
    matchLabels:
      app: voice-agent
  template:
    metadata:
      labels:
        app: voice-agent
    spec:
      containers:
      - name: agent
        image: your-registry/voice-agent:latest
        resources:
          requests:
            memory: "8Gi"
            cpu: "4"
          limits:
            memory: "8Gi"
            cpu: "4"
        envFrom:
        - secretRef:
            name: agent-secrets
        ports:
        - containerPort: 8081  # Health check
          name: health
        livenessProbe:
          httpGet:
            path: /health
            port: 8081
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8081
          initialDelaySeconds: 10
          periodSeconds: 5
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 600"]  # Grace period for jobs
---
apiVersion: v1
kind: Service
metadata:
  name: voice-agent
spec:
  selector:
    app: voice-agent
  ports:
  - port: 8081
    targetPort: 8081
    name: health
  type: ClusterIP
```

**Horizontal Pod Autoscaler**:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: voice-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: voice-agent
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

### AWS ECS/Fargate

**Task Definition**:
```json
{
  "family": "voice-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "4096",
  "memory": "8192",
  "containerDefinitions": [
    {
      "name": "agent",
      "image": "your-ecr-repo/voice-agent:latest",
      "essential": true,
      "secrets": [
        {
          "name": "LIVEKIT_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:livekit-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/voice-agent",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

**Service with Auto-scaling**:
```json
{
  "serviceName": "voice-agent-service",
  "cluster": "production",
  "taskDefinition": "voice-agent",
  "desiredCount": 3,
  "launchType": "FARGATE",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": ["subnet-xxx", "subnet-yyy"],
      "securityGroups": ["sg-xxx"]
    }
  }
}
```

---

## Graceful Shutdown

Workers must handle shutdown gracefully to avoid interrupting active sessions.

### Implementation

```python
# src/agent.py
import signal
import asyncio
from livekit import agents

shutdown_event = asyncio.Event()

def signal_handler(sig, frame):
    """Handle shutdown signals."""
    print(f"Received signal {sig}, initiating graceful shutdown...")
    shutdown_event.set()

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@agents.entrypoint
async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    # Your agent logic
    session = agents.AgentSession(...)
    session.start(ctx.room)

    # Wait for completion or shutdown
    done, pending = await asyncio.wait(
        [
            asyncio.create_task(session.wait_for_complete()),
            asyncio.create_task(shutdown_event.wait())
        ],
        return_when=asyncio.FIRST_COMPLETED
    )

    if shutdown_event.is_set():
        print("Shutdown requested, completing current session...")
        # Allow current session to finish
        await session.wait_for_complete()
```

### Kubernetes Grace Period

```yaml
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 600  # 10 minutes for long conversations
      containers:
      - name: agent
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 600"]
```

**Why 600 seconds?**
- Voice conversations can be long (5-10+ minutes)
- Abrupt termination creates poor user experience
- Workers finish current jobs, then shut down

---

## Health Checks

Expose health endpoint for monitoring.

```python
# src/agent.py
from aiohttp import web
import asyncio

async def health_check(request):
    """Health check endpoint."""
    return web.Response(text="OK", status=200)

async def start_health_server():
    """Start health check HTTP server."""
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/readiness', health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, '0.0.0.0', 8081)
    await site.start()
    print("Health check server running on http://0.0.0.0:8081")

# In main
if __name__ == "__main__":
    asyncio.create_task(start_health_server())
    # ... start agent worker
```

---

## Monitoring and Logging

### Metrics Collection

```python
from livekit.agents.metrics import UsageCollector
import time

@agents.entrypoint
async def entrypoint(ctx: agents.JobContext):
    start_time = time.time()
    usage = UsageCollector()

    session = agents.AgentSession(
        # ... components
        metrics_collector=usage,
    )

    session.start(ctx.room)
    await session.wait_for_complete()

    # Log metrics
    duration = time.time() - start_time
    print(f"Session metrics:")
    print(f"  Duration: {duration:.2f}s")
    print(f"  STT audio: {usage.stt.audio_duration:.2f}s")
    print(f"  LLM tokens: {usage.llm.total_tokens}")
    print(f"  TTS characters: {usage.tts.characters}")

    # Send to monitoring system (Datadog, CloudWatch, etc.)
    await send_metrics_to_monitoring({
        "session_duration": duration,
        "stt_audio_duration": usage.stt.audio_duration,
        "llm_total_tokens": usage.llm.total_tokens,
        "tts_characters": usage.tts.characters,
    })
```

### Structured Logging

```python
import logging
import json

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

logger = logging.getLogger(__name__)

def log_event(event_type: str, **kwargs):
    """Log structured event."""
    log_entry = {
        "timestamp": time.time(),
        "event_type": event_type,
        **kwargs
    }
    logger.info(json.dumps(log_entry))

# Usage
log_event("session_started", room_id=ctx.room.name)
log_event("tool_called", tool="lookup_weather", location="San Francisco")
log_event("session_ended", duration=120.5, tokens_used=5000)
```

### Error Tracking

```python
import sentry_sdk

# Initialize Sentry
sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=0.1,
)

@agents.entrypoint
async def entrypoint(ctx: agents.JobContext):
    try:
        # Your agent logic
        await run_agent(ctx)
    except Exception as e:
        # Capture exception
        sentry_sdk.capture_exception(e)
        logger.error(f"Agent error: {e}", exc_info=True)
        raise
```

---

## Performance Optimization

### Connection Pooling

Reuse HTTP connections for external APIs:

```python
import httpx

# Global HTTP client (connection pooling)
http_client = httpx.AsyncClient(
    timeout=10.0,
    limits=httpx.Limits(max_keepalive_connections=50, max_connections=100)
)

@function_tool
async def call_external_api(self, context: RunContext, query: str):
    """Call external API with connection pooling."""
    response = await http_client.get(f"https://api.example.com/search?q={query}")
    return response.json(), "Results found"
```

### Model Pre-loading

Download models at build time, not runtime:

```python
# src/agent.py
import sys

def download_models():
    """Download required models."""
    from livekit.plugins import silero, turn_detector

    print("Downloading Silero VAD...")
    silero.VAD.load()

    print("Downloading turn detector model...")
    turn_detector.MultilingualModel.load(languages=["en"])

    print("Models downloaded successfully!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "download-files":
        download_models()
        sys.exit(0)
```

In Dockerfile:
```dockerfile
RUN uv run python src/agent.py download-files
```

### Memory Management

```python
import gc

@agents.entrypoint
async def entrypoint(ctx: agents.JobContext):
    # Your agent logic
    await run_agent(ctx)

    # Clean up after session
    gc.collect()
```

---

## CI/CD Pipeline

### GitHub Actions Example

```yaml
name: Deploy Voice Agent

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: |
          ghcr.io/${{ github.repository }}:latest
          ghcr.io/${{ github.repository }}:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/voice-agent \
          agent=ghcr.io/${{ github.repository }}:${{ github.sha }}
        kubectl rollout status deployment/voice-agent
```

---

## Cost Optimization

### Regional Deployment

Deploy close to users to reduce latency and network costs:
- **US users**: us-west-2 (Oregon) or us-east-1 (Virginia)
- **EU users**: eu-west-1 (Ireland)
- **Asia users**: ap-southeast-1 (Singapore)

### Model Selection

Balance cost vs quality:

**Production**: deepgram + gpt-4.1-mini + cartesia = ~$4.40/hour
**Budget**: deepgram + gpt-4.1-mini + openai-tts = ~$3.50/hour
**Premium**: assemblyai + gpt-4o + elevenlabs = ~$10/hour

### Caching

Cache expensive operations:

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
async def expensive_lookup(query: str):
    """Cached lookup."""
    return await database.query(query)
```

### Prompt Optimization

Shorter prompts = fewer tokens = lower cost:

```python
# Before (verbose)
instructions = """
You are an extremely helpful and friendly AI assistant designed to help users
with their questions. You should always be polite, courteous, and aim to provide
the most helpful and accurate information possible...
"""

# After (concise)
instructions = "You are a helpful assistant. Be concise and accurate."
```

---

## Multi-Environment Setup

Maintain separate environments:

```bash
# Development
LIVEKIT_URL=wss://dev-project.livekit.cloud

# Staging
LIVEKIT_URL=wss://staging-project.livekit.cloud

# Production
LIVEKIT_URL=wss://prod-project.livekit.cloud
```

**Best practice**: Use separate LiveKit projects for each environment.

---

## Troubleshooting

### Common Deployment Issues

**Issue**: "Connection refused" or WebSocket errors
**Solution**: Check LIVEKIT_URL, API_KEY, and API_SECRET. Verify network connectivity.

**Issue**: "Model download failed"
**Solution**: Ensure models are downloaded at build time, not runtime. Check disk space.

**Issue**: High memory usage
**Solution**: Reduce WORKER_CONCURRENCY. Check for memory leaks in tools.

**Issue**: Slow response times
**Solution**: Monitor each pipeline component. Check network latency to provider APIs.

**Issue**: Container exits immediately
**Solution**: Check logs. Verify all required environment variables are set.

### Debugging in Production

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Add request IDs for tracing:
```python
import uuid

@agents.entrypoint
async def entrypoint(ctx: agents.JobContext):
    request_id = str(uuid.uuid4())
    logger.info(f"[{request_id}] Session started", extra={"request_id": request_id})
    # ... rest of code
```
