# Self-Hosted STT API

A FastAPI-based Speech-to-Text API using faster-whisper for efficient transcription.

## Features

- 🚀 **Fast transcription** using optimized faster-whisper (CTranslate2)
- 🔄 **Real-time streaming** via WebSocket
- 📁 **Batch processing** via REST API
- 🌍 **Multi-language support** with auto-detection
- 🎯 **Voice Activity Detection** (VAD) filtering
- 🐳 **Docker support** for easy deployment

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Running the API

```bash
# Basic usage (CPU, base model)
python main.py

# With custom configuration
export WHISPER_MODEL_SIZE=small
export WHISPER_DEVICE=cuda
export WHISPER_COMPUTE_TYPE=float16
python main.py
```

### Using Docker

```bash
# Build the image
docker build -t stt-api .

# Run the container
docker run -p 8000:8000 -e WHISPER_MODEL_SIZE=base stt-api

# With GPU support
docker run --gpus all -p 8000:8000 \
  -e WHISPER_DEVICE=cuda \
  -e WHISPER_COMPUTE_TYPE=float16 \
  stt-api
```

## Configuration

Environment variables:

- `WHISPER_MODEL_SIZE`: Model size (`tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3`)
  - Default: `base`
- `WHISPER_DEVICE`: Device to use (`cpu`, `cuda`)
  - Default: `cpu`
- `WHISPER_COMPUTE_TYPE`: Compute precision (`int8`, `float16`, `float32`)
  - Default: `int8`

## API Endpoints

### Health Check

```bash
curl http://localhost:8000/health
```

### Batch Transcription

```bash
curl -X POST "http://localhost:8000/transcribe" \
  -F "file=@audio.wav" \
  -F "language=en"
```

Response:
```json
{
  "text": "Hello world, this is a test.",
  "segments": [
    {
      "start": 0.0,
      "end": 2.5,
      "text": "Hello world, this is a test.",
      "confidence": -0.234
    }
  ],
  "language": "en",
  "language_probability": 0.99,
  "duration": 2.5
}
```

### Streaming Transcription (WebSocket)

Connect to `ws://localhost:8000/ws/transcribe`

1. Send configuration as first message:
```json
{
  "language": "en",
  "sample_rate": 16000,
  "task": "transcribe"
}
```

2. Receive ready confirmation:
```json
{
  "type": "ready",
  "message": "Ready to receive audio"
}
```

3. Send raw PCM audio data (int16 bytes)

4. Receive transcription events:
```json
{
  "type": "final",
  "text": "Hello world",
  "start": 0.0,
  "end": 1.5,
  "confidence": -0.234
}
```

## Performance

Model size vs. speed/accuracy trade-offs:

| Model | Parameters | Speed (CPU) | WER |
|-------|-----------|-------------|-----|
| tiny | 39M | ~32x | ~10% |
| base | 74M | ~16x | ~7% |
| small | 244M | ~6x | ~5% |
| medium | 769M | ~2x | ~4% |
| large-v3 | 1550M | ~1x | ~3% |

*Speeds are relative to real-time on CPU. GPU acceleration is much faster.*

## License

MIT License
