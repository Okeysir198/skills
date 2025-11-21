# Self-Hosted STT for LiveKit Voice Agents

A complete solution for self-hosted Speech-to-Text (STT) in LiveKit voice agents using Whisper models from Hugging Face.

## 🎯 Overview

This project provides two main components:

1. **STT API** (`stt-api/`) - Self-hosted FastAPI service running faster-whisper
2. **LiveKit Plugin** (`livekit-plugin-custom-stt/`) - LiveKit agents plugin to use the STT API

## ✨ Features

- 🚀 **Fast & Efficient** - Uses faster-whisper (CTranslate2 optimization)
- 🔒 **Self-Hosted** - Full control over your infrastructure and data
- 🔄 **Real-Time Streaming** - WebSocket-based streaming transcription
- 📦 **Batch Processing** - REST API for file transcription
- 🌍 **99+ Languages** - Multi-language support with auto-detection
- 🎛️ **Highly Configurable** - Model size, beam search, VAD, and more
- 🐳 **Docker Ready** - Easy deployment with Docker/Docker Compose
- 🔌 **LiveKit Native** - Seamless integration with LiveKit agents

## 🏗️ Architecture

```
┌─────────────────────┐
│   LiveKit Room      │
│  (Voice Session)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐      WebSocket/HTTP      ┌──────────────────┐
│  LiveKit Agent      │ ◄────────────────────── │   STT API        │
│  + Custom STT       │                          │  (FastAPI +      │
│    Plugin           │                          │   faster-whisper)│
└─────────────────────┘                          └──────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Docker (optional, for containerized deployment)
- LiveKit server (for voice agent usage)

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd stt-livekit-plugin

# Start the STT API service
docker-compose up -d

# Verify it's running
curl http://localhost:8000/health
```

### Option 2: Manual Setup

#### 1. Start the STT API

```bash
# Install dependencies
cd stt-api
pip install -r requirements.txt

# Run the API
python main.py
```

The API will start on `http://localhost:8000`.

#### 2. Install the LiveKit Plugin

```bash
# Install the plugin
cd ../livekit-plugin-custom-stt
pip install -e .

# Or install dependencies for development
pip install livekit-agents aiohttp websockets
```

#### 3. Run a Voice Agent

```bash
# Set environment variables
export LIVEKIT_URL=ws://localhost:7880
export LIVEKIT_API_KEY=your-api-key
export LIVEKIT_API_SECRET=your-api-secret
export STT_API_URL=http://localhost:8000

# Run the example voice agent
cd examples
python voice_agent.py
```

## 📖 Usage

### Basic Transcription

```python
from livekit.plugins import custom_stt

# Initialize STT
stt = custom_stt.STT(
    api_url="http://localhost:8000",
    options=custom_stt.STTOptions(
        language="en",
        beam_size=5,
    ),
)

# Transcribe audio buffer
result = await stt.recognize(audio_buffer, language="en")
print(result.alternatives[0].text)
```

### Voice Agent Integration

```python
from livekit import agents
from livekit.plugins import custom_stt

async def entrypoint(ctx: agents.JobContext):
    # Initialize STT
    stt = custom_stt.STT(api_url="http://localhost:8000")

    # Create voice assistant
    assistant = agents.VoiceAssistant(
        stt=stt,
        llm=your_llm,
        tts=your_tts,
    )

    # Start the assistant
    await ctx.connect()
    assistant.start(ctx.room)
```

See `livekit-plugin-custom-stt/examples/` for complete examples.

## ⚙️ Configuration

### STT API Configuration

Configure via environment variables:

| Variable | Default | Options | Description |
|----------|---------|---------|-------------|
| `WHISPER_MODEL_SIZE` | `base` | `tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3` | Whisper model size |
| `WHISPER_DEVICE` | `cpu` | `cpu`, `cuda` | Compute device |
| `WHISPER_COMPUTE_TYPE` | `int8` | `int8`, `float16`, `float32` | Precision |

### Plugin Configuration

```python
options = custom_stt.STTOptions(
    language="en",          # Language code or None for auto-detect
    task="transcribe",      # "transcribe" or "translate" to English
    beam_size=5,           # Beam search size (1-10)
    vad_filter=True,       # Voice Activity Detection
    sample_rate=16000,     # Audio sample rate
)
```

## 🎛️ Model Selection Guide

Choose the right model for your use case:

| Model | Size | Speed (CPU) | WER | Best For |
|-------|------|-------------|-----|----------|
| **tiny** | 39M | ~32x | ~10% | Real-time, low latency |
| **base** | 74M | ~16x | ~7% | General purpose |
| **small** | 244M | ~6x | ~5% | Balanced accuracy/speed |
| **medium** | 769M | ~2x | ~4% | High accuracy |
| **large-v3** | 1550M | ~1x | ~3% | Maximum accuracy |

*Speed is relative to real-time on CPU. GPU is much faster.*

### Recommendations

- **Real-time voice agents**: `tiny` or `base` model
- **Batch transcription**: `small` or `medium` model
- **Maximum accuracy**: `large-v3` model with GPU

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Edit docker-compose.yml to configure model size and device
docker-compose up -d

# View logs
docker-compose logs -f stt-api

# Stop services
docker-compose down
```

### Manual Docker

```bash
# Build image
cd stt-api
docker build -t stt-api .

# Run with CPU
docker run -p 8000:8000 \
  -e WHISPER_MODEL_SIZE=base \
  stt-api

# Run with GPU
docker run --gpus all -p 8000:8000 \
  -e WHISPER_DEVICE=cuda \
  -e WHISPER_COMPUTE_TYPE=float16 \
  stt-api
```

## 📊 Performance Optimization

### For Real-Time Voice Agents

1. **Use smaller models** - `tiny` or `base` for low latency
2. **Enable GPU** - 5-10x faster than CPU
3. **Reduce beam size** - Set to 3 for faster decoding
4. **Enable VAD** - Skip silence periods

### For Batch Transcription

1. **Use larger models** - `medium` or `large-v3` for best accuracy
2. **Increase beam size** - Set to 5-10 for better results
3. **GPU acceleration** - Essential for large models

### Hardware Recommendations

- **CPU only**: `tiny` or `base` model, suitable for development
- **GPU (4GB+)**: `small` or `medium` model, good for production
- **GPU (8GB+)**: `large-v3` model, best accuracy

## 🧪 Testing

### Test the STT API

```bash
# Health check
curl http://localhost:8000/health

# Transcribe audio file
curl -X POST http://localhost:8000/transcribe \
  -F "file=@test_audio.wav" \
  -F "language=en"
```

### Test the Plugin

```bash
cd livekit-plugin-custom-stt/examples
python basic_usage.py
```

## 📚 Documentation

- [STT API Documentation](stt-api/README.md)
- [LiveKit Plugin Documentation](livekit-plugin-custom-stt/README.md)
- [LiveKit Agents Documentation](https://docs.livekit.io/agents/)
- [faster-whisper Documentation](https://github.com/SYSTRAN/faster-whisper)

## 🔧 Troubleshooting

### API Connection Issues

```bash
# Check if API is running
curl http://localhost:8000/health

# Check API logs
docker-compose logs stt-api

# Test WebSocket connection
wscat -c ws://localhost:8000/ws/transcribe
```

### Performance Issues

- **Slow transcription**: Use smaller model or enable GPU
- **High memory usage**: Reduce model size or use int8 precision
- **Connection timeouts**: Increase timeout in plugin configuration

### Audio Format Issues

Ensure audio is:
- **Sample rate**: 16000 Hz (configurable)
- **Format**: PCM int16
- **Channels**: Mono

## 🛣️ Roadmap

- [ ] Speaker diarization support
- [ ] Punctuation and formatting improvements
- [ ] Multi-language auto-switching
- [ ] Kubernetes deployment examples
- [ ] Prometheus metrics endpoint
- [ ] Support for more Whisper variants (e.g., distil-whisper)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [LiveKit](https://livekit.io/) - Real-time communication platform
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - Optimized Whisper implementation
- [OpenAI Whisper](https://github.com/openai/whisper) - Original Whisper model
- [Hugging Face](https://huggingface.co/) - Model hosting and community

## 📞 Support

- Issues: [GitHub Issues](https://github.com/yourusername/stt-livekit-plugin/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/stt-livekit-plugin/discussions)
- LiveKit Community: [LiveKit Slack](https://livekit.io/slack)

---

**Note**: This is a community project and is not officially affiliated with LiveKit, OpenAI, or Hugging Face.
