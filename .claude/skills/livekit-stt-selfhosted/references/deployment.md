# Production Deployment Guide

Best practices for deploying self-hosted STT API and LiveKit plugins in production.

## Deployment Options

### 1. Docker Deployment (Recommended)

#### API Server Dockerfile
```dockerfile
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Install Python
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Download model at build time (optional, saves startup time)
RUN python3 -c "from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor; \
    AutoModelForSpeechSeq2Seq.from_pretrained('openai/whisper-large-v3'); \
    AutoProcessor.from_pretrained('openai/whisper-large-v3')"

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Build and Run
```bash
# Build
docker build -t stt-api:latest .

# Run with GPU
docker run --gpus all -p 8000:8000 -e MODEL_ID=openai/whisper-large-v3 stt-api:latest

# Run CPU-only
docker run -p 8000:8000 -e MODEL_ID=openai/whisper-tiny -e DEVICE=cpu stt-api:latest
```

#### Docker Compose
```yaml
version: '3.8'

services:
  stt-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MODEL_ID=openai/whisper-large-v3
      - DEVICE=cuda:0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
```

### 2. Kubernetes Deployment

#### Deployment YAML
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stt-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: stt-api
  template:
    metadata:
      labels:
        app: stt-api
    spec:
      containers:
      - name: stt-api
        image: stt-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: MODEL_ID
          value: "openai/whisper-large-v3"
        - name: DEVICE
          value: "cuda:0"
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: "12Gi"
          requests:
            nvidia.com/gpu: 1
            memory: "8Gi"
---
apiVersion: v1
kind: Service
metadata:
  name: stt-api
spec:
  selector:
    app: stt-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 3. Cloud Platforms

#### AWS (ECS with GPU)
```bash
# Use g4dn instances for GPU
# Deploy with ECS/Fargate + GPU support
# Use Application Load Balancer for WebSocket
```

#### GCP (Cloud Run with GPU)
```bash
gcloud run deploy stt-api \
  --image gcr.io/PROJECT_ID/stt-api \
  --platform managed \
  --region us-central1 \
  --gpu 1 \
  --memory 8Gi
```

#### Azure (Container Instances)
```bash
az container create \
  --resource-group myResourceGroup \
  --name stt-api \
  --image myregistry.azurecr.io/stt-api:latest \
  --gpu-count 1 \
  --gpu-sku K80 \
  --ports 8000
```

## Scaling Strategies

### Horizontal Scaling

**Load Balancing**
- Use Nginx/HAProxy for WebSocket load balancing
- Sticky sessions recommended for stateful connections
- Health checks on `/health` endpoint

**Nginx Configuration**
```nginx
upstream stt_backend {
    ip_hash;  # Sticky sessions
    server stt-api-1:8000;
    server stt-api-2:8000;
    server stt-api-3:8000;
}

server {
    listen 80;

    location /ws/ {
        proxy_pass http://stt_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    location / {
        proxy_pass http://stt_backend;
    }
}
```

### Vertical Scaling

**GPU Optimization**
- Use larger GPUs (A100, V100) for better throughput
- Increase batch_size for parallel processing
- Use model parallelism for very large models

**Resource Allocation**
```python
# Optimize for your hardware
batch_size = 16  # Increase with more VRAM
num_workers = 4  # CPU cores for data loading
```

## Performance Monitoring

### Metrics to Track

1. **Latency**: Time to first result, total transcription time
2. **Throughput**: Requests per second
3. **Resource Usage**: GPU utilization, memory usage
4. **Error Rate**: Failed requests, timeout rate
5. **Queue Depth**: Concurrent connections

### Prometheus Metrics
```python
from prometheus_client import Counter, Histogram, Gauge
from prometheus_fastapi_instrumentator import Instrumentator

# Add to FastAPI app
Instrumentator().instrument(app).expose(app)

# Custom metrics
transcription_duration = Histogram(
    'stt_transcription_duration_seconds',
    'Time spent transcribing audio'
)

active_connections = Gauge(
    'stt_active_connections',
    'Number of active WebSocket connections'
)
```

### Logging
```python
import logging
import sys

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('stt-api.log')
    ]
)
```

## Security

### API Authentication

**API Keys**
```python
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header()):
    if x_api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.websocket("/ws/transcribe")
async def websocket_transcribe(
    websocket: WebSocket,
    x_api_key: str = Header()
):
    await verify_api_key(x_api_key)
    # ...
```

**JWT Tokens**
```python
from fastapi import Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials = Depends(security)):
    # Verify JWT token
    pass
```

### HTTPS/WSS

**Use SSL certificates for production**
```bash
# With Nginx
server {
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /ws/ {
        proxy_pass http://stt_backend;
        # ... WebSocket config
    }
}
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.websocket("/ws/transcribe")
@limiter.limit("10/minute")
async def websocket_transcribe(websocket: WebSocket):
    # ...
```

## Cost Optimization

### Model Selection
- **Large models**: Higher cost, better accuracy
- **Small models**: Lower cost, faster, acceptable quality
- Use smallest model that meets quality requirements

### GPU Utilization
- Keep models loaded in memory (avoid reload overhead)
- Batch processing for better GPU utilization
- Use spot/preemptible instances for cost savings

### Caching
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def transcribe_cached(audio_hash: str) -> str:
    # Cache transcriptions for repeated audio
    pass
```

## High Availability

### Redundancy
- Deploy multiple instances across availability zones
- Use database for shared state if needed
- Implement graceful shutdown

### Failover
```python
import signal
import sys

def graceful_shutdown(signum, frame):
    logger.info("Shutting down gracefully...")
    # Close connections, save state
    sys.exit(0)

signal.signal(signal.SIGTERM, graceful_shutdown)
```

### Health Checks
```python
@app.get("/health")
async def health():
    checks = {
        "model_loaded": pipe is not None,
        "gpu_available": torch.cuda.is_available(),
        "memory_ok": check_memory(),
    }

    if all(checks.values()):
        return {"status": "healthy", "checks": checks}
    else:
        raise HTTPException(status_code=503, detail={"status": "unhealthy", "checks": checks})
```

## Disaster Recovery

### Backup Strategy
- Container images versioned and stored
- Configuration in version control
- Model weights cached or stored in S3/GCS

### Rollback Plan
```bash
# Keep previous versions
docker tag stt-api:latest stt-api:v1.2.0
docker tag stt-api:latest stt-api:previous

# Quick rollback
docker run stt-api:previous
```

## Maintenance

### Model Updates
```python
# Download new model
MODEL_ID = os.getenv("MODEL_ID", "openai/whisper-large-v3")

# Test new model
# Deploy with canary/blue-green deployment
```

### Zero-Downtime Updates
1. Deploy new version alongside old
2. Route small % of traffic to new version
3. Monitor metrics
4. Gradually shift traffic
5. Decommission old version

## Best Practices Summary

1. **Use Docker** for consistent deployments
2. **Enable GPU** for production workloads
3. **Monitor metrics** actively (latency, errors, resources)
4. **Implement authentication** for API access
5. **Use HTTPS/WSS** in production
6. **Scale horizontally** for high availability
7. **Cache results** where appropriate
8. **Implement graceful shutdown**
9. **Keep models in memory** to avoid reload overhead
10. **Version everything** (code, models, configs)

## Troubleshooting

### High Memory Usage
- Use smaller model
- Reduce batch_size
- Enable low_cpu_mem_usage

### Slow Response Times
- Check GPU utilization
- Increase batch_size
- Use FP16 precision
- Optimize chunk size

### Connection Issues
- Check firewall rules
- Verify WebSocket support in load balancer
- Increase timeout settings
- Check network bandwidth

## Resources

- Docker GPU Support: https://docs.docker.com/config/containers/resource_constraints/#gpu
- Kubernetes GPU: https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/
- FastAPI Deployment: https://fastapi.tiangolo.com/deployment/
- NVIDIA Container Toolkit: https://github.com/NVIDIA/nvidia-docker
