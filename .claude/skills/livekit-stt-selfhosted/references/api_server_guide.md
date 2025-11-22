# Self-Hosted STT API Server Implementation Guide

Complete guide for building a production-ready self-hosted speech-to-text API using FastAPI and Hugging Face models.

## Architecture

### Components
1. **FastAPI** - Web framework with WebSocket support
2. **Whisper/HF Model** - Speech recognition model
3. **Audio Processing** - Handle streaming audio chunks
4. **WebSocket Protocol** - Real-time bidirectional communication

### Request Flow
```
Client → WebSocket Connection → Audio Chunks → Buffer → Model → Results → Client
```

## Core Implementation

### 1. FastAPI Setup

```python
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="STT API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Model Loading

Load model once at startup to avoid repeated loading:

```python
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import torch

@app.on_event("startup")
async def startup_event():
    global pipe

    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        "openai/whisper-large-v3",
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
        use_safetensors=True
    )
    model.to("cuda:0")

    processor = AutoProcessor.from_pretrained("openai/whisper-large-v3")

    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        max_new_tokens=128,
        chunk_length_s=30,
        batch_size=16,
        return_timestamps=True,
        torch_dtype=torch.float16,
        device="cuda:0",
    )
```

### 3. Audio Buffer Management

Accumulate audio chunks before processing:

```python
class AudioBuffer:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.buffer = []

    def add_chunk(self, chunk: bytes):
        self.buffer.append(chunk)

    def get_audio_array(self) -> np.ndarray:
        if not self.buffer:
            return None

        # Combine chunks
        audio_bytes = b''.join(self.buffer)

        # Convert to numpy (16-bit PCM)
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)

        # Normalize to [-1, 1]
        audio_array = audio_array.astype(np.float32) / 32768.0

        return audio_array

    def duration_seconds(self) -> float:
        total_bytes = sum(len(chunk) for chunk in self.buffer)
        total_samples = total_bytes // 2  # 16-bit = 2 bytes
        return total_samples / self.sample_rate

    def clear(self):
        self.buffer = []
```

### 4. WebSocket Endpoint

```python
@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    await websocket.accept()

    audio_buffer = AudioBuffer(sample_rate=16000)
    language = "en"

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message:
                # Audio chunk received
                audio_buffer.add_chunk(message["bytes"])

                # Process when buffer reaches threshold (e.g., 1 second)
                if audio_buffer.duration_seconds() >= 1.0:
                    audio_array = audio_buffer.get_audio_array()

                    # Transcribe
                    result = pipe(audio_array, generate_kwargs={"language": language})

                    # Send interim result
                    await websocket.send_json({
                        "type": "interim",
                        "text": result["text"]
                    })

                    audio_buffer.clear()

            elif "text" in message:
                # Control message
                data = json.loads(message["text"])

                if data.get("type") == "config":
                    language = data.get("language", "en")

                elif data.get("type") == "end":
                    # Process remaining audio
                    audio_array = audio_buffer.get_audio_array()
                    if audio_array is not None:
                        result = pipe(audio_array, generate_kwargs={"language": language})
                        await websocket.send_json({
                            "type": "final",
                            "text": result["text"],
                            "language": language
                        })
                    break

    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
```

## WebSocket Protocol

### Client → Server Messages

**Audio Chunks** (Binary)
```
Raw 16-bit PCM audio data at 16kHz
```

**Configuration** (JSON)
```json
{
  "type": "config",
  "language": "en",
  "detect_language": false
}
```

**End Signal** (JSON)
```json
{
  "type": "end"
}
```

### Server → Client Messages

**Interim Result** (JSON)
```json
{
  "type": "interim",
  "text": "partial transcription..."
}
```

**Final Result** (JSON)
```json
{
  "type": "final",
  "text": "complete transcription",
  "language": "en",
  "chunks": [...]
}
```

**Error** (JSON)
```json
{
  "type": "error",
  "message": "error description"
}
```

## Audio Processing

### Expected Format
- **Sample Rate**: 16kHz (16000 Hz)
- **Channels**: Mono (1 channel)
- **Bit Depth**: 16-bit
- **Encoding**: PCM (Linear)

### Converting Bytes to NumPy
```python
# Receive bytes
audio_bytes = message["bytes"]

# Convert to int16 array
audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)

# Normalize to float32 [-1, 1]
audio_float32 = audio_int16.astype(np.float32) / 32768.0
```

### Handling Different Formats
If receiving other formats (e.g., WAV, WebM):
```python
import io
from pydub import AudioSegment

def convert_to_pcm(audio_bytes: bytes) -> np.ndarray:
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))

    # Convert to mono 16kHz
    audio = audio.set_channels(1)
    audio = audio.set_frame_rate(16000)

    # Get samples
    samples = np.array(audio.get_array_of_samples())

    # Normalize
    return samples.astype(np.float32) / 32768.0
```

## Performance Optimization

### 1. Model Optimization

**Use FP16 on GPU**
```python
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
```

**Enable Flash Attention** (if available)
```python
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    model_id,
    attn_implementation="flash_attention_2"  # Requires flash-attn
)
```

**Compile Model** (PyTorch 2.0+)
```python
model = torch.compile(model)
```

### 2. Batch Processing

Process multiple requests together:
```python
pipe = pipeline(..., batch_size=16)
```

### 3. Memory Management

**Keep Model in Memory**
```python
# Don't reload model for each request
# Load once in startup event
```

**Use Low CPU Memory**
```python
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    model_id,
    low_cpu_mem_usage=True
)
```

### 4. Concurrent Connections

Use async to handle multiple WebSocket connections:
```python
# FastAPI handles this automatically
# Each websocket_transcribe() runs in its own task
```

## Error Handling

### Model Errors
```python
try:
    result = pipe(audio_array)
except Exception as e:
    logger.error(f"Transcription error: {e}")
    await websocket.send_json({
        "type": "error",
        "message": str(e)
    })
```

### WebSocket Errors
```python
try:
    # WebSocket operations
    pass
except WebSocketDisconnect:
    logger.info("Client disconnected")
except Exception as e:
    logger.error(f"WebSocket error: {e}")
finally:
    try:
        await websocket.close()
    except:
        pass
```

## Configuration

### Environment Variables
```python
import os
from dotenv import load_dotenv

load_dotenv()

MODEL_ID = os.getenv("MODEL_ID", "openai/whisper-large-v3")
DEVICE = os.getenv("DEVICE", "cuda:0" if torch.cuda.is_available() else "cpu")
PORT = int(os.getenv("PORT", "8000"))
```

### .env File
```bash
MODEL_ID=openai/whisper-large-v3
DEVICE=cuda:0
PORT=8000
HOST=0.0.0.0
```

## Health Endpoints

```python
@app.get("/")
async def root():
    return {
        "status": "ok",
        "model": MODEL_ID,
        "device": DEVICE
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy" if pipe is not None else "initializing",
        "model_loaded": pipe is not None
    }
```

## Running the Server

### Development
```bash
python main.py
```

Or:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Production
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Or with Gunicorn:
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## Testing

### WebSocket Test Client
```python
import asyncio
import websockets
import json

async def test_transcribe():
    uri = "ws://localhost:8000/ws/transcribe"

    async with websockets.connect(uri) as ws:
        # Send config
        await ws.send(json.dumps({
            "type": "config",
            "language": "en"
        }))

        # Send audio (example: read from file)
        with open("audio.pcm", "rb") as f:
            chunk_size = 32000  # 1 second at 16kHz
            while chunk := f.read(chunk_size):
                await ws.send(chunk)

                # Check for interim results
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=0.1)
                    print(json.loads(response))
                except asyncio.TimeoutError:
                    pass

        # Send end signal
        await ws.send(json.dumps({"type": "end"}))

        # Get final result
        response = await ws.recv()
        print(json.loads(response))

asyncio.run(test_transcribe())
```

## Common Issues

### Issue: "out of memory" on GPU
**Solution**: Use smaller model or reduce batch_size

### Issue: Slow transcription
**Solution**:
- Use GPU
- Use smaller model
- Optimize batch processing
- Use FP16

### Issue: Poor quality results
**Solution**:
- Use larger model
- Ensure correct audio format (16kHz, mono, 16-bit PCM)
- Add more context (longer chunks)

### Issue: WebSocket disconnect
**Solution**:
- Implement reconnection logic
- Add keepalive messages
- Check firewall/proxy settings

## Advanced Features

### Language Auto-Detection
```python
result = pipe(audio_array, generate_kwargs={"language": None})
detected_language = result.get("language", "unknown")
```

### Word-Level Timestamps
```python
pipe = pipeline(..., return_timestamps="word")
result = pipe(audio_array)
# result["chunks"] contains word-level info
```

### Speaker Diarization
Requires additional libraries like pyannote.audio:
```python
from pyannote.audio import Pipeline

diarization = Pipeline.from_pretrained("pyannote/speaker-diarization")
diarization_result = diarization(audio_file)
```

## Resources

- FastAPI Docs: https://fastapi.tiangolo.com/
- Hugging Face Transformers: https://huggingface.co/docs/transformers
- Whisper Documentation: https://github.com/openai/whisper
- WebSocket Protocol: https://websockets.readthedocs.io/
