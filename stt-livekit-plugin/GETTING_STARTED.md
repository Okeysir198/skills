# Getting Started with Self-Hosted STT for LiveKit

This guide will walk you through setting up and using the self-hosted STT solution for LiveKit voice agents.

## Table of Contents

1. [Installation](#installation)
2. [Running the STT API](#running-the-stt-api)
3. [Testing the API](#testing-the-api)
4. [Using the LiveKit Plugin](#using-the-livekit-plugin)
5. [Building a Voice Agent](#building-a-voice-agent)
6. [Configuration Tips](#configuration-tips)

## Installation

### Prerequisites

- Python 3.9 or higher
- Docker (optional, but recommended)
- LiveKit server (if building voice agents)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd stt-livekit-plugin
```

### Step 2: Choose Your Deployment Method

You have two options:

**Option A: Docker (Recommended)**
- Easier setup
- Isolated environment
- Better for production

**Option B: Manual Installation**
- Direct control
- Better for development
- Easier to debug

## Running the STT API

### Option A: Using Docker

1. **Start the API:**

```bash
docker-compose up -d
```

2. **Check the logs:**

```bash
docker-compose logs -f stt-api
```

3. **Verify it's running:**

```bash
curl http://localhost:8000/health
```

You should see:
```json
{"status": "ok", "model_loaded": true}
```

### Option B: Manual Installation

1. **Install dependencies:**

```bash
cd stt-api
pip install -r requirements.txt
```

2. **Run the API:**

```bash
python main.py
```

The API will start on `http://localhost:8000`.

3. **Verify it's running:**

```bash
curl http://localhost:8000/health
```

## Testing the API

### Test 1: Health Check

```bash
curl http://localhost:8000/
```

Expected output:
```json
{
  "status": "healthy",
  "model": "base",
  "device": "cpu",
  "compute_type": "int8"
}
```

### Test 2: Transcribe an Audio File

1. **Get a test audio file:**

You can download a sample or create one:
```bash
# Example: Download a sample audio file
wget https://www2.cs.uic.edu/~i101/SoundFiles/gettysburg.wav -O test.wav
```

2. **Transcribe:**

```bash
curl -X POST http://localhost:8000/transcribe \
  -F "file=@test.wav" \
  -F "language=en" | jq
```

You should see output like:
```json
{
  "text": "Four score and seven years ago...",
  "segments": [...],
  "language": "en",
  "language_probability": 0.99,
  "duration": 15.5
}
```

### Test 3: WebSocket Streaming (Advanced)

Install `wscat` for WebSocket testing:

```bash
npm install -g wscat
```

Test the WebSocket endpoint:

```bash
wscat -c ws://localhost:8000/ws/transcribe
```

## Using the LiveKit Plugin

### Step 1: Install the Plugin

```bash
cd livekit-plugin-custom-stt
pip install -e .
```

Or install dependencies manually:

```bash
pip install livekit-agents aiohttp websockets
```

### Step 2: Basic Usage Test

Create a test script `test_plugin.py`:

```python
import asyncio
from livekit.plugins import custom_stt

async def main():
    # Initialize STT
    stt = custom_stt.STT(api_url="http://localhost:8000")

    # Check connection
    print("STT plugin initialized successfully!")

    # Clean up
    await stt.aclose()

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
python test_plugin.py
```

### Step 3: Run the Basic Example

```bash
cd livekit-plugin-custom-stt/examples
python basic_usage.py
```

This will demonstrate both batch and streaming transcription.

## Building a Voice Agent

### Step 1: Set Up LiveKit Server

If you don't have a LiveKit server running:

```bash
# Using Docker
docker run --rm \
  -p 7880:7880 \
  -p 7881:7881 \
  -p 7882:7882/udp \
  -e LIVEKIT_KEYS="devkey: secret" \
  livekit/livekit-server \
  --dev
```

### Step 2: Configure Environment

Create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# LiveKit
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# STT API
STT_API_URL=http://localhost:8000
```

Load the environment:

```bash
export $(cat .env | xargs)
```

### Step 3: Create a Simple Voice Agent

Create `my_agent.py`:

```python
import asyncio
import logging
from livekit import agents
from livekit.plugins import custom_stt

logging.basicConfig(level=logging.INFO)

async def entrypoint(ctx: agents.JobContext):
    # Initialize STT
    stt = custom_stt.STT(
        api_url="http://localhost:8000",
        options=custom_stt.STTOptions(
            language="en",
            beam_size=3,
        ),
    )

    # Connect to room
    await ctx.connect()
    logging.info(f"Connected to room: {ctx.room.name}")

    # For a complete voice agent, you'd add:
    # - LLM (e.g., OpenAI, Anthropic)
    # - TTS (e.g., ElevenLabs, Google)
    # - Voice Assistant pipeline

    # Keep agent running
    await asyncio.Event().wait()

if __name__ == "__main__":
    worker_options = agents.WorkerOptions(
        entrypoint_fnc=entrypoint,
    )
    agents.cli.run_app(worker_options)
```

### Step 4: Run the Agent

```bash
python my_agent.py start
```

## Configuration Tips

### Choosing the Right Model

Start with `base` model and adjust based on your needs:

| Use Case | Model | Device | Notes |
|----------|-------|--------|-------|
| Development/Testing | `tiny` or `base` | CPU | Fast, good enough |
| Real-time voice agent | `base` or `small` | GPU | Balance speed/accuracy |
| Batch transcription | `medium` or `large-v3` | GPU | Best accuracy |
| Production (low latency) | `tiny` | GPU | Fastest |

### Optimizing for Real-Time

Edit `docker-compose.yml` or set environment variables:

```yaml
environment:
  - WHISPER_MODEL_SIZE=tiny  # or base
  - WHISPER_DEVICE=cuda      # if GPU available
  - WHISPER_COMPUTE_TYPE=float16
```

And in your plugin:

```python
options = custom_stt.STTOptions(
    beam_size=3,        # Lower = faster
    vad_filter=True,    # Skip silence
    sample_rate=16000,  # Standard
)
```

### Optimizing for Accuracy

```yaml
environment:
  - WHISPER_MODEL_SIZE=medium  # or large-v3
  - WHISPER_DEVICE=cuda
  - WHISPER_COMPUTE_TYPE=float16
```

```python
options = custom_stt.STTOptions(
    beam_size=5,        # Higher = better
    vad_filter=True,
    language="en",      # Specify if known
)
```

## Troubleshooting

### API won't start

**Error**: `ModuleNotFoundError: No module named 'faster_whisper'`

**Solution**:
```bash
cd stt-api
pip install -r requirements.txt
```

### Connection refused

**Error**: Connection to `http://localhost:8000` refused

**Solution**:
- Check if API is running: `docker-compose ps` or `ps aux | grep python`
- Check logs: `docker-compose logs stt-api`
- Verify port: `netstat -an | grep 8000`

### Transcription is slow

**Solutions**:
1. Use smaller model: `WHISPER_MODEL_SIZE=tiny`
2. Enable GPU: `WHISPER_DEVICE=cuda`
3. Reduce beam size: `beam_size=3`
4. Lower quality: `WHISPER_COMPUTE_TYPE=int8`

### Out of memory

**Solutions**:
1. Use smaller model: `tiny` or `base`
2. Use int8 precision: `WHISPER_COMPUTE_TYPE=int8`
3. Restart the service to clear cache

### Poor transcription quality

**Solutions**:
1. Use larger model: `medium` or `large-v3`
2. Increase beam size: `beam_size=10`
3. Specify correct language: `language="en"`
4. Check audio quality (sample rate, format)

## Next Steps

1. **Explore Examples**: Check out `livekit-plugin-custom-stt/examples/`
2. **Read Documentation**:
   - [STT API Documentation](stt-api/README.md)
   - [Plugin Documentation](livekit-plugin-custom-stt/README.md)
3. **Build Your Agent**: Integrate with LLM and TTS
4. **Deploy to Production**: Use Kubernetes or cloud services
5. **Monitor Performance**: Add logging and metrics

## Getting Help

- **Issues**: Check [GitHub Issues](https://github.com/yourusername/stt-livekit-plugin/issues)
- **Discussions**: Join [GitHub Discussions](https://github.com/yourusername/stt-livekit-plugin/discussions)
- **LiveKit**: Visit [LiveKit Documentation](https://docs.livekit.io/)
- **Community**: Join [LiveKit Slack](https://livekit.io/slack)

---

Happy building! 🚀
