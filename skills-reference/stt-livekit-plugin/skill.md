---
description: Self-hosted Speech-to-Text for LiveKit voice agents using Whisper models. Includes a FastAPI service and LiveKit plugin.
tags: [livekit, stt, speech-to-text, whisper, voice-agent, ai, huggingface, fastapi]
---

# STT LiveKit Plugin

Build self-hosted Speech-to-Text systems for LiveKit voice agents using Whisper models from Hugging Face.

## What's Included

This skill provides a complete self-hosted STT solution:

1. **STT API Service** - FastAPI server running faster-whisper for efficient transcription
2. **LiveKit Plugin** - Native LiveKit agents plugin for seamless integration
3. **Examples** - Working examples of voice agents and transcription
4. **Documentation** - Comprehensive guides and API documentation

## Features

- 🚀 **Fast transcription** with faster-whisper (CTranslate2 optimization)
- 🔒 **Self-hosted** - full control over your data and infrastructure
- 🔄 **Real-time streaming** via WebSocket
- 📦 **Batch processing** via REST API
- 🌍 **99+ languages** with auto-detection
- 🐳 **Docker-ready** for easy deployment

## Quick Start

1. **Start the STT API:**
```bash
cd stt-livekit-plugin
docker-compose up -d
```

2. **Install the plugin:**
```bash
cd livekit-plugin-custom-stt
pip install -e .
```

3. **Use in your voice agent:**
```python
from livekit.plugins import custom_stt

stt = custom_stt.STT(api_url="http://localhost:8000")
assistant = agents.VoiceAssistant(stt=stt, llm=..., tts=...)
```

## Project Structure

```
stt-livekit-plugin/
├── stt-api/                    # Self-hosted STT API service
│   ├── main.py                 # FastAPI application
│   ├── Dockerfile              # Container image
│   └── requirements.txt
├── livekit-plugin-custom-stt/  # LiveKit plugin
│   ├── livekit/plugins/custom_stt/
│   │   ├── __init__.py
│   │   ├── stt.py             # Main plugin implementation
│   │   └── version.py
│   ├── examples/              # Usage examples
│   └── pyproject.toml
├── docker-compose.yml          # Easy deployment
└── README.md                   # Full documentation
```

## Use Cases

- **Voice assistants** - Real-time conversation with AI agents
- **Meeting transcription** - Record and transcribe meetings
- **Call centers** - Analyze customer conversations
- **Podcasts** - Generate transcripts automatically
- **Accessibility** - Live captions and subtitles

## Configuration

Choose the right model for your needs:

| Model | Speed | Accuracy | Best For |
|-------|-------|----------|----------|
| tiny | Fastest | Good | Real-time, low latency |
| base | Fast | Better | General purpose |
| small | Medium | Great | Balanced |
| medium | Slow | Excellent | High accuracy |
| large-v3 | Slowest | Best | Maximum accuracy |

## Learn More

- [Getting Started Guide](GETTING_STARTED.md)
- [STT API Documentation](stt-api/README.md)
- [Plugin Documentation](livekit-plugin-custom-stt/README.md)
- [LiveKit Agents](https://docs.livekit.io/agents/)

## Requirements

- Python 3.9+
- Docker (recommended)
- LiveKit server (for voice agents)
- GPU (optional, for better performance)
