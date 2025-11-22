# LiveKit Custom STT Plugin

LiveKit Agents plugin for connecting to a self-hosted speech-to-text API.

## Installation

```bash
pip install -e .
```

Or from source:
```bash
git clone <your-repo>
cd livekit-plugins-custom-stt
pip install -e .
```

## Usage

```python
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, silero
from livekit.plugins import custom_stt

async def entrypoint(ctx: JobContext):
    initial_ctx = llm.ChatContext().append(
        role="system",
        text="You are a helpful voice assistant.",
    )

    # Use the custom self-hosted STT
    assistant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=custom_stt.STT(
            api_url="ws://localhost:8000/ws/transcribe",
            language="en",
        ),
        llm=openai.LLM(),
        tts=openai.TTS(),
        chat_ctx=initial_ctx,
    )

    await assistant.start(ctx.room)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
```

## Configuration

### API URL
Point to your self-hosted STT server:
```python
stt=custom_stt.STT(api_url="ws://your-server:8000/ws/transcribe")
```

### Language
Specify the transcription language:
```python
stt=custom_stt.STT(language="es")  # Spanish
```

### Auto-detect Language
Enable automatic language detection:
```python
stt=custom_stt.STT(detect_language=True)
```

## Requirements

- LiveKit Agents SDK >= 0.8.0
- aiohttp >= 3.9.0
- A running self-hosted STT API server

## Development

### Testing
```bash
pip install -e ".[dev]"
pytest
```

### Code Formatting
```bash
black .
mypy .
```

## License

Apache-2.0
