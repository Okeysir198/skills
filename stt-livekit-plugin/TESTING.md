# Testing Guide

This guide explains how to test the STT LiveKit plugin implementation.

## Test Structure

The project includes comprehensive integration tests that verify:
1. ✅ **Real API communication** (no mocks)
2. ✅ **Real audio processing** (generated sine waves)
3. ✅ **Real LiveKit integration** (actual AudioBuffer/AudioFrame objects)
4. ✅ **Complete data flow** (API ↔ Plugin ↔ LiveKit)

## Quick Start

### 1. Start the STT API

**Option A: Docker (Recommended)**
```bash
docker-compose up -d
```

**Option B: Manual**
```bash
cd stt-api
pip install -r requirements.txt
python main.py
```

Verify it's running:
```bash
curl http://localhost:8000/health
```

### 2. Install Test Dependencies

```bash
cd tests
pip install -r requirements.txt

# Also install the plugin
cd ../livekit-plugin-custom-stt
pip install -e .
```

### 3. Run Tests

**Option A: Using pytest (Recommended)**
```bash
cd tests
pytest test_integration.py -v
```

**Option B: Run manually**
```bash
cd tests
python test_integration.py
```

## Test Cases

### 1. API Health Check (`test_api_health`)

**What it tests:**
- API is running and accessible
- Health endpoint returns correct status
- Model is loaded

**Expected result:**
```json
{"status": "ok", "model_loaded": true}
```

### 2. API Batch Transcription (`test_api_batch_transcription`)

**What it tests:**
- Direct HTTP POST to `/transcribe` endpoint
- WAV file upload and processing
- Response structure validation

**Test data:**
- Real generated audio (2 second sine wave at 440Hz)
- Proper WAV format with headers

**Expected result:**
```json
{
  "text": "...",
  "segments": [...],
  "language": "en",
  "duration": 2.0
}
```

### 3. Plugin Initialization (`test_plugin_initialization`)

**What it tests:**
- Plugin class instantiation
- Property values (model, provider)
- Capabilities configuration

**Expected result:**
- `model == "whisper"`
- `provider == "custom-stt"`
- `streaming == True`
- `interim_results == False`

### 4. Plugin Batch Transcription (`test_plugin_batch_transcription`)

**What it tests:**
- AudioBuffer creation from numpy array
- WAV conversion inside plugin
- Full transcription pipeline through plugin
- SpeechEvent response structure

**Test data:**
- Real audio data (2 seconds, 16kHz, mono)
- Proper AudioBuffer with metadata

**Expected result:**
```python
SpeechEvent(
    type=SpeechEventType.FINAL_TRANSCRIPT,
    alternatives=[
        SpeechData(text="...", language="en", confidence=-0.234)
    ]
)
```

### 5. WebSocket Connection (`test_websocket_connection`)

**What it tests:**
- Direct WebSocket connection to API
- Configuration message exchange
- Binary audio data transmission
- JSON response parsing

**Protocol flow:**
```
Client -> {"language": "en", "sample_rate": 16000, "task": "transcribe"}
Server -> {"type": "ready", "message": "Ready to receive audio"}
Client -> [binary PCM audio data]
Server -> {"type": "final", "text": "...", "start": 0.0, "end": 2.5}
```

### 6. Plugin Streaming (`test_plugin_streaming`)

**What it tests:**
- SpeechStream lifecycle management
- Frame-by-frame audio pushing
- Async iteration over events
- Proper task initialization via `__aiter__`
- Queue-based architecture

**Test data:**
- 3 seconds of audio split into 100ms frames
- Real AudioFrame objects with proper metadata
- Synchronized push and receive

**Expected flow:**
1. Create stream via `plugin.stream()`
2. Start iteration: `async for event in stream`
3. `__aiter__` triggers, starting `_run()` task
4. Push frames: `stream.push_frame(frame)`
5. Receive events: `SpeechEvent` objects
6. End stream: `await stream.end_input()`
7. Clean up: `await stream.aclose()`

## Running Individual Tests

```bash
# Test 1: Health check
pytest test_integration.py::test_api_health -v

# Test 2: Batch transcription
pytest test_integration.py::test_api_batch_transcription -v

# Test 3: Plugin initialization
pytest test_integration.py::test_plugin_initialization -v

# Test 4: Plugin batch transcription
pytest test_integration.py::test_plugin_batch_transcription -v

# Test 5: WebSocket connection
pytest test_integration.py::test_websocket_connection -v

# Test 6: Plugin streaming
pytest test_integration.py::test_plugin_streaming -v
```

## Understanding Test Output

### Successful Test

```
tests/test_integration.py::test_api_health PASSED                    [16%]
tests/test_integration.py::test_api_batch_transcription PASSED       [33%]
Transcription result:
Language: en
Duration: 2.0
tests/test_integration.py::test_plugin_initialization PASSED         [50%]
tests/test_integration.py::test_plugin_batch_transcription PASSED    [66%]
Plugin transcription:
Confidence: -0.234
tests/test_integration.py::test_websocket_connection PASSED          [83%]
WebSocket connection established and ready
tests/test_integration.py::test_plugin_streaming PASSED              [100%]
Received event: type=FINAL_TRANSCRIPT, text=
Received 1 events

======================== 6 passed in 12.34s ========================
```

### Common Issues

**1. Connection Refused**
```
aiohttp.client_exceptions.ClientConnectorError: Cannot connect to host localhost:8000
```

**Solution**: Start the STT API
```bash
docker-compose up -d
# or
cd stt-api && python main.py
```

**2. Module Not Found**
```
ModuleNotFoundError: No module named 'livekit'
```

**Solution**: Install dependencies
```bash
cd livekit-plugin-custom-stt
pip install -e .
```

**3. Timeout Errors**
```
asyncio.TimeoutError: Timeout waiting for events
```

**Solution**:
- Use smaller model (`WHISPER_MODEL_SIZE=tiny`)
- Increase timeout in test
- Check API logs: `docker-compose logs -f stt-api`

## Test Data Generation

All tests use **real generated audio**, not mocked data:

```python
def generate_test_audio(duration=2.0, sample_rate=16000, frequency=440.0):
    """Generate real sine wave audio."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio = np.sin(frequency * 2 * np.pi * t)
    audio_int16 = (audio * 32767).astype(np.int16)
    return audio_int16
```

This generates:
- **Format**: PCM int16
- **Sample rate**: 16000 Hz
- **Channels**: Mono (1)
- **Content**: 440Hz sine wave (musical note A4)

## Adding Real Speech Tests

For testing with actual speech audio:

```python
@pytest.mark.asyncio
async def test_with_real_speech():
    """Test with real speech audio file."""
    plugin = custom_stt.STT(api_url=API_URL)

    # Load real audio file
    import wave
    with wave.open("path/to/speech.wav", "rb") as wav:
        audio_data = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16)
        buffer = utils.AudioBuffer(
            data=audio_data,
            sample_rate=wav.getframerate(),
            num_channels=wav.getnchannels(),
        )

    result = await plugin._recognize_impl(buffer)
    print(f"Transcription: {result.alternatives[0].text}")

    await plugin.aclose()
```

Download test audio:
```bash
cd tests
wget https://www2.cs.uic.edu/~i101/SoundFiles/gettysburg.wav
```

## Continuous Integration

To run tests in CI/CD:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Start STT API
        run: |
          cd stt-api
          pip install -r requirements.txt
          python main.py &
          sleep 10  # Wait for API to start

      - name: Run tests
        run: |
          cd tests
          pip install -r requirements.txt
          cd ../livekit-plugin-custom-stt
          pip install -e .
          cd ../tests
          pytest test_integration.py -v
```

## Performance Testing

To test performance and latency:

```python
import time

async def test_latency():
    plugin = custom_stt.STT(api_url=API_URL)
    audio_data = generate_test_audio(duration=5.0)
    buffer = utils.AudioBuffer(data=audio_data, sample_rate=16000, num_channels=1)

    start = time.time()
    result = await plugin._recognize_impl(buffer)
    latency = time.time() - start

    print(f"Transcription latency: {latency:.2f}s for {5.0}s audio")
    print(f"Real-time factor: {latency / 5.0:.2f}x")

    await plugin.aclose()
```

## Debugging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or for specific modules:

```python
logging.getLogger("livekit.plugins.custom_stt").setLevel(logging.DEBUG)
logging.getLogger("websockets").setLevel(logging.DEBUG)
```

Check API logs:

```bash
# Docker
docker-compose logs -f stt-api

# Manual
# Logs printed to console
```

## Test Coverage

To measure code coverage:

```bash
pip install pytest-cov
pytest test_integration.py --cov=livekit.plugins.custom_stt --cov-report=html
open htmlcov/index.html
```

## Summary

✅ **All tests use real data and real connections**
✅ **No mocked functions or stubbed responses**
✅ **Tests verify complete integration pipeline**
✅ **Audio processing is real (numpy arrays → AudioBuffer → WAV)**
✅ **Network communication is real (aiohttp, websockets)**
✅ **LiveKit objects are real (AudioFrame, SpeechEvent)**

The tests comprehensively verify that the STT API and LiveKit plugin work together correctly in a real-world scenario.
