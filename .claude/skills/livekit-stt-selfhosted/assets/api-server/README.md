# Self-Hosted STT API Server

FastAPI-based speech-to-text server using Whisper or other Hugging Face models.

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your preferred settings
```

3. Run the server:
```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /` - Health check
- `GET /health` - Detailed health status
- `WebSocket /ws/transcribe` - Real-time transcription

## WebSocket Protocol

### Sending Audio
Send raw audio bytes (16-bit PCM, 16kHz) as binary messages.

### Control Messages
```json
{"type": "config", "language": "en", "detect_language": false}
{"type": "end"}
```

### Response Format
```json
{"type": "interim", "text": "partial transcription..."}
{"type": "final", "text": "complete transcription", "language": "en"}
{"type": "error", "message": "error description"}
```

## Model Selection

Supported models (configure in .env):
- `openai/whisper-large-v3` (best quality, requires GPU)
- `openai/whisper-medium` (balanced)
- `openai/whisper-small` (faster)
- `openai/whisper-tiny` (fastest, can run on CPU)

## Performance

- GPU recommended for large models
- Model loaded once at startup (kept in memory)
- Real-time transcription with ~1 second chunks
