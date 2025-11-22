# LiveKit Custom STT Plugin

A LiveKit plugin for self-hosted Speech-to-Text using faster-whisper. This plugin connects to a custom STT API service for transcription, allowing you to run Whisper models on your own infrastructure.

## Features

- 🎯 **Self-hosted**: Run your own STT infrastructure
- 🚀 **Fast**: Uses faster-whisper (optimized with CTranslate2)
- 🔄 **Streaming**: Real-time transcription via WebSocket
- 📦 **Batch**: Non-streaming transcription for audio files
- 🌍 **Multi-language**: Supports 99+ languages with auto-detection
- 🔧 **Configurable**: Adjust model size, beam search, VAD, etc.

## Installation

```bash
pip install livekit-plugins-custom-stt
```

Or install from source:

```bash
cd livekit-plugin-custom-stt
pip install -e .
```

## Prerequisites

You need a running STT API service. See the `../stt-api` directory for the API implementation.

Quick start with Docker:

```bash
cd ../stt-api
docker build -t stt-api .
docker run -p 8000:8000 stt-api
```

## Usage

### Basic Example

```python
from livekit import agents
from livekit.plugins import custom_stt

# Initialize the STT plugin
stt_plugin = custom_stt.STT(
    api_url="http://localhost:8000",
    options=custom_stt.STTOptions(
        language="en",
        task="transcribe",
    ),
)

# Use in a voice agent
async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()

    # Use STT for voice pipeline
    assistant = agents.VoiceAssistant(
        stt=stt_plugin,
        llm=...,  # Your LLM
        tts=...,  # Your TTS
    )

    assistant.start(ctx.room)

    # Transcribe an audio file
    with open("audio.wav", "rb") as f:
        buffer = agents.utils.AudioBuffer(data=f.read())
        result = await stt_plugin.recognize(buffer, language="en")
        print(result.alternatives[0].text)


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
```

### Streaming Example

```python
from livekit import rtc
from livekit.plugins import custom_stt

# Create streaming session
stt_plugin = custom_stt.STT(api_url="http://localhost:8000")
stream = stt_plugin.stream(language="en")

# Push audio frames
async for event in stream:
    # Get audio frame from microphone/room
    audio_frame = ...  # rtc.AudioFrame
    stream.push_frame(audio_frame)

# Receive transcriptions
async for event in stream:
    if event.type == agents.stt.SpeechEventType.FINAL_TRANSCRIPT:
        print(f"Transcription: {event.alternatives[0].text}")
```

### Configuration Options

```python
options = custom_stt.STTOptions(
    language="en",          # Language code or None for auto-detect
    task="transcribe",      # "transcribe" or "translate"
    beam_size=5,           # Beam search size (1-10)
    vad_filter=True,       # Enable VAD filtering
    sample_rate=16000,     # Audio sample rate in Hz
)

stt_plugin = custom_stt.STT(
    api_url="http://localhost:8000",
    options=options,
)
```

## STT API Configuration

The STT API service can be configured via environment variables:

- `WHISPER_MODEL_SIZE`: Model size (`tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3`)
- `WHISPER_DEVICE`: Device (`cpu`, `cuda`)
- `WHISPER_COMPUTE_TYPE`: Precision (`int8`, `float16`, `float32`)

## Architecture

```
┌─────────────────┐      WebSocket/HTTP      ┌──────────────────┐
│  LiveKit Agent  │ ◄────────────────────── │   STT API        │
│  (with plugin)  │                          │  (FastAPI +      │
└─────────────────┘                          │   faster-whisper)│
                                             └──────────────────┘
```

1. **LiveKit Agent**: Uses this plugin to transcribe audio
2. **STT API**: Self-hosted FastAPI service running Whisper model
3. **Communication**: HTTP for batch, WebSocket for streaming

## Performance Tips

### Model Selection

Choose model size based on your requirements:

| Model | Speed | Accuracy | Use Case |
|-------|-------|----------|----------|
| tiny | Fastest | Good | Real-time, low latency |
| base | Fast | Better | General purpose |
| small | Medium | Great | Balanced |
| medium | Slow | Excellent | High accuracy needed |
| large-v3 | Slowest | Best | Maximum accuracy |

### Hardware Recommendations

- **CPU**: Works well with base/small models
- **GPU**: Recommended for medium/large models
  - Use `WHISPER_DEVICE=cuda` and `WHISPER_COMPUTE_TYPE=float16`

### Latency Optimization

For real-time streaming:
1. Use `tiny` or `base` model
2. Enable GPU if available
3. Reduce `beam_size` to 3
4. Enable `vad_filter=True` to skip silence

## API Reference

### `STT`

Main STT plugin class.

**Constructor:**
- `api_url` (str): URL of the STT API service
- `options` (STTOptions): Configuration options
- `http_session` (aiohttp.ClientSession): Optional session for connection pooling

**Methods:**
- `recognize(buffer, language)`: Transcribe audio buffer (batch)
- `stream(language)`: Create streaming transcription session
- `aclose()`: Clean up resources

### `STTOptions`

Configuration dataclass.

**Fields:**
- `language` (str | None): Language code (e.g., "en", "es", "fr")
- `task` ("transcribe" | "translate"): Task type
- `beam_size` (int): Beam search size (default: 5)
- `vad_filter` (bool): Enable VAD (default: True)
- `sample_rate` (int): Audio sample rate (default: 16000)

### `SpeechStream`

Streaming transcription session.

**Methods:**
- `push_frame(frame)`: Send audio frame for transcription
- `flush()`: Flush buffered audio
- `end_input()`: Signal no more audio
- `aclose()`: Close stream

**Async Iterator:**
Returns `SpeechEvent` objects with transcription results.

## Troubleshooting

### Connection Errors

```python
# Check API health
import aiohttp
async with aiohttp.ClientSession() as session:
    async with session.get("http://localhost:8000/health") as resp:
        print(await resp.json())
```

### Audio Format Issues

Ensure audio is:
- Sample rate: 16000 Hz (or configure in options)
- Format: PCM int16
- Channels: Mono

### Performance Issues

- Use smaller model for real-time
- Enable GPU acceleration
- Reduce beam size
- Check CPU/memory usage on API server

## Examples

See the `examples/` directory for complete working examples:

- `basic_usage.py`: Simple transcription example
- `streaming_agent.py`: Real-time voice agent
- `batch_transcribe.py`: Batch transcription of audio files

## License

MIT License

## Contributing

Contributions are welcome! Please open issues and pull requests on GitHub.

## Related Projects

- [LiveKit Agents](https://github.com/livekit/agents)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [OpenAI Whisper](https://github.com/openai/whisper)
