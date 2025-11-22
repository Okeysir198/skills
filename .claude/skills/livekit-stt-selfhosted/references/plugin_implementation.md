# LiveKit STT Plugin Implementation Guide

Complete guide for implementing a custom LiveKit STT plugin.

## Architecture Overview

LiveKit STT plugins implement the `stt.STT` base class and provide:
1. **Non-streaming recognition** - Process complete audio buffers
2. **Streaming recognition** - Real-time transcription with interim results
3. **Event emission** - Send transcription events to the agent

## Base Class Interface

### Required Imports
```python
from livekit import rtc
from livekit.agents import stt, utils
```

### Class Structure
```python
class STT(stt.STT):
    def __init__(self, **kwargs):
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=True,
                interim_results=True,
            )
        )

    async def _recognize_impl(
        self,
        buffer: utils.AudioBuffer,
        *,
        language: Optional[str] = None,
    ) -> stt.SpeechEvent:
        # Implement non-streaming recognition
        pass

    def stream(
        self,
        *,
        language: Optional[str] = None,
    ) -> "SpeechStream":
        # Return streaming session
        return SpeechStream(stt=self, ...)
```

## STT Capabilities

Declare what your plugin supports:

```python
stt.STTCapabilities(
    streaming=True,        # Supports real-time streaming
    interim_results=True,  # Can provide partial results
)
```

## Speech Events

### Event Types
```python
stt.SpeechEventType.START_OF_SPEECH     # Speech detected
stt.SpeechEventType.INTERIM_TRANSCRIPT  # Partial result
stt.SpeechEventType.FINAL_TRANSCRIPT    # Complete result
stt.SpeechEventType.END_OF_SPEECH       # Speech ended
```

### Creating Events
```python
event = stt.SpeechEvent(
    type=stt.SpeechEventType.FINAL_TRANSCRIPT,
    alternatives=[
        stt.SpeechData(
            text="transcribed text",
            language="en",
            confidence=0.95,  # Optional
        )
    ],
)
```

## Non-Streaming Recognition

Implement `_recognize_impl` for processing complete audio buffers:

```python
async def _recognize_impl(
    self,
    buffer: utils.AudioBuffer,
    *,
    language: Optional[str] = None,
) -> stt.SpeechEvent:
    # 1. Convert audio buffer to appropriate format
    audio_data = buffer.remix_and_resample(
        sample_rate=16000,
        num_channels=1
    ).data.tobytes()

    # 2. Send to your API
    result = await your_api_call(audio_data, language)

    # 3. Return speech event
    return stt.SpeechEvent(
        type=stt.SpeechEventType.FINAL_TRANSCRIPT,
        alternatives=[
            stt.SpeechData(
                text=result["text"],
                language=language or "en",
            )
        ],
    )
```

## Streaming Recognition

### SpeechStream Class
```python
class SpeechStream(stt.SpeechStream):
    def __init__(
        self,
        *,
        stt: STT,
        sample_rate: int,
        language: str,
    ):
        super().__init__(stt=stt, sample_rate=sample_rate)
        self._language = language
        # Your initialization

    async def _run(self):
        # Main streaming loop
        send_task = asyncio.create_task(self._send_task())
        receive_task = asyncio.create_task(self._receive_task())
        await asyncio.gather(send_task, receive_task)

    async def _send_task(self):
        # Send audio chunks to API
        async for frame in self._input_ch:
            audio_data = frame.remix_and_resample(
                self._sample_rate, 1
            ).data.tobytes()
            await self._send_to_api(audio_data)

    async def _receive_task(self):
        # Receive results from API
        async for result in self._api_results():
            event = stt.SpeechEvent(...)
            self._event_ch.send_nowait(event)

    async def aclose(self):
        # Cleanup
        await self._cleanup()
        await super().aclose()
```

## Audio Processing

### Resampling Audio
```python
# Resample to target sample rate with mono channel
processed = buffer.remix_and_resample(
    rate=16000,      # Target sample rate
    num_channels=1   # Mono
)

# Get raw bytes
audio_bytes = processed.data.tobytes()
```

### Audio Formats
Most STT APIs expect:
- **Sample rate**: 16kHz (16000 Hz)
- **Channels**: Mono (1 channel)
- **Format**: 16-bit PCM

## WebSocket Communication

### Connecting to API
```python
import aiohttp

session = aiohttp.ClientSession()
ws = await session.ws_connect(api_url)

# Send configuration
await ws.send_json({
    "type": "config",
    "language": language,
})

# Send audio
await ws.send_bytes(audio_data)

# Receive results
async for msg in ws:
    if msg.type == aiohttp.WSMsgType.TEXT:
        data = json.loads(msg.data)
        # Process result
```

## Error Handling

### API Errors
```python
try:
    result = await api_call()
except Exception as e:
    logger.error(f"STT API error: {e}")
    # Return empty result or raise
    return stt.SpeechEvent(
        type=stt.SpeechEventType.FINAL_TRANSCRIPT,
        alternatives=[stt.SpeechData(text="", language=language)],
    )
```

### Connection Management
```python
async def _cleanup(self):
    """Clean up connections."""
    if self._ws is not None:
        try:
            await self._ws.close()
        except:
            pass

    if self._session is not None:
        try:
            await self._session.close()
        except:
            pass
```

## Package Structure

```
livekit-plugins-yourname/
├── livekit/
│   └── plugins/
│       └── yourname/
│           ├── __init__.py      # Export STT class
│           ├── version.py       # Version info
│           └── stt.py           # Main implementation
├── pyproject.toml              # Package configuration
└── README.md                   # Documentation
```

## Dependencies

### Minimum Requirements
```toml
dependencies = [
    "livekit-agents>=0.8.0",
    "aiohttp>=3.9.0",
]
```

### Common Additional Deps
- `websockets` - If not using aiohttp
- `pydantic` - For configuration validation
- `python-dotenv` - For environment variables

## Testing

### Basic Test
```python
import pytest
from livekit.agents import utils
from livekit.plugins import yourname

@pytest.mark.asyncio
async def test_recognize():
    stt_instance = yourname.STT(api_url="ws://localhost:8000/ws/transcribe")

    # Create test audio buffer
    # ...

    result = await stt_instance.recognize(buffer, language="en")
    assert result.alternatives[0].text != ""
```

## Best Practices

1. **Session Reuse**: Reuse HTTP/WebSocket sessions across requests
2. **Error Recovery**: Implement retry logic for transient failures
3. **Logging**: Use structured logging for debugging
4. **Configuration**: Allow API URL and settings to be configurable
5. **Async/Await**: Always use async for I/O operations
6. **Cleanup**: Properly close connections in aclose()
7. **Type Hints**: Use type hints for better IDE support

## Example Plugins

Study these official LiveKit plugins:
- **Deepgram**: `livekit-plugins-deepgram` - WebSocket streaming
- **AssemblyAI**: `livekit-plugins-assemblyai` - REST + WebSocket
- **Google**: `livekit-plugins-google` - gRPC streaming

## Additional Resources

- LiveKit Agents Docs: https://docs.livekit.io/agents/
- STT API Reference: https://docs.livekit.io/reference/python/livekit/agents/stt/
- Example Plugins: https://github.com/livekit/agents/tree/main/livekit-plugins
