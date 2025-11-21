# Integration Tests

This directory contains real integration tests for the STT API and LiveKit plugin.

## Prerequisites

1. **Start the STT API:**

```bash
cd ../stt-api
python main.py
```

Or using Docker:

```bash
cd ..
docker-compose up -d
```

2. **Install test dependencies:**

```bash
pip install -r requirements.txt
```

3. **Install the plugin:**

```bash
cd ../livekit-plugin-custom-stt
pip install -e .
```

## Running Tests

### Run all tests:

```bash
pytest test_integration.py -v
```

### Run specific test:

```bash
pytest test_integration.py::test_api_health -v
pytest test_integration.py::test_plugin_streaming -v
```

### Run tests manually (without pytest):

```bash
python test_integration.py
```

## Test Coverage

### 1. **test_api_health**
- Verifies the STT API is running
- Checks health endpoint returns correct status

### 2. **test_api_batch_transcription**
- Tests batch transcription endpoint directly
- Uses real generated audio (sine wave)
- Verifies response structure and content

### 3. **test_plugin_initialization**
- Tests plugin initialization
- Verifies properties and capabilities

### 4. **test_plugin_batch_transcription**
- Tests batch transcription through the plugin
- Creates AudioBuffer from generated audio
- Verifies SpeechEvent response

### 5. **test_plugin_streaming**
- Tests real-time streaming transcription
- Creates audio frames and pushes them
- Verifies events are received correctly

### 6. **test_websocket_connection**
- Tests WebSocket connection directly
- Sends configuration and audio data
- Verifies bidirectional communication

## Test Data

All tests use **real generated audio** (sine waves at 440Hz):
- No mocked data
- No mocked functions
- Real AudioBuffer and AudioFrame objects
- Actual network communication

## Environment Variables

- `STT_API_URL`: URL of the STT API (default: `http://localhost:8000`)

Example:
```bash
STT_API_URL=http://192.168.1.100:8000 pytest test_integration.py -v
```

## Troubleshooting

### API Connection Errors

```
Error: Connection refused
```

**Solution**: Make sure the STT API is running:
```bash
curl http://localhost:8000/health
```

### Import Errors

```
ModuleNotFoundError: No module named 'livekit'
```

**Solution**: Install the plugin and dependencies:
```bash
cd ../livekit-plugin-custom-stt
pip install -e .
pip install -r ../tests/requirements.txt
```

### Timeout Errors

```
asyncio.TimeoutError
```

**Solution**:
- Use a smaller model (`tiny` or `base`) for faster processing
- Increase timeout in tests
- Check API logs for errors

## Expected Output

```
Running integration tests...
API URL: http://localhost:8000
============================================================

1. Testing API health...
✓ API health check passed

2. Testing API batch transcription...
Transcription result: [transcription of sine wave]
Language: en
Duration: 2.0
✓ API batch transcription passed

3. Testing plugin initialization...
✓ Plugin initialization passed

4. Testing plugin batch transcription...
Plugin transcription: [transcription]
Confidence: -0.234
✓ Plugin batch transcription passed

5. Testing WebSocket connection...
WebSocket connection established and ready
✓ WebSocket connection passed

6. Testing plugin streaming...
Received event: type=FINAL_TRANSCRIPT, text=[transcription]
Received 1 events
✓ Plugin streaming passed

============================================================
All tests passed!
```

## Notes

- **Audio Quality**: Tests use simple sine waves which may not transcribe to meaningful text
- **Model Behavior**: Whisper may produce silence or attempt to transcribe the tone
- **Integration**: Tests verify the full pipeline works, not transcription accuracy
- **Real Data**: For accuracy tests, use real speech audio files

## Adding Real Speech Tests

To test with actual speech audio:

```python
def test_real_speech():
    """Test with real speech audio file."""
    with open("path/to/speech.wav", "rb") as f:
        # Use the audio file for testing
        ...
```

Download test audio:
```bash
wget https://www2.cs.uic.edu/~i101/SoundFiles/gettysburg.wav -O tests/test_audio.wav
```
