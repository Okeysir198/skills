# Provider Comparison and Setup

## Speech-to-Text (STT) Providers

### Deepgram (Recommended)
**Best for**: Production use, multilingual applications

```python
from livekit.plugins import deepgram

stt = deepgram.STT(
    model="nova-3",
    language="multi",  # or "en", "es", etc.
)
```

**Pros**:
- Very fast (~0.2× real-time)
- Excellent multilingual support
- Good accuracy
- Streaming support
- Cost-effective

**Environment**: `DEEPGRAM_API_KEY`

---

### AssemblyAI
**Best for**: High accuracy requirements, complex audio

```python
from livekit.plugins import assemblyai

stt = assemblyai.STT(
    sample_rate=16000,
)
```

**Pros**:
- High accuracy
- Good noise handling
- Speaker diarization support
- Sentiment analysis features

**Cons**:
- Slightly higher latency than Deepgram

**Environment**: `ASSEMBLYAI_API_KEY`

---

### OpenAI Whisper
**Best for**: Offline deployment, cost control

```python
from livekit.plugins import openai

stt = openai.STT(model="whisper-1")
```

**Pros**:
- Can run locally (no API costs)
- Good multilingual support
- Robust to accents

**Cons**:
- Higher latency for cloud version
- Requires GPU for local deployment

**Environment**: `OPENAI_API_KEY` (for cloud) or local model files

---

## Large Language Model (LLM) Providers

### OpenAI GPT-4.1-mini (Recommended)
**Best for**: Fast, cost-effective production use

```python
from livekit.plugins import openai

llm = openai.LLM(
    model="gpt-4.1-mini",
    temperature=0.7,
)
```

**Pros**:
- Very fast token generation (50+ tokens/sec)
- Low cost
- Good quality for most use cases
- Function calling support

**Environment**: `OPENAI_API_KEY`

---

### OpenAI GPT-4o
**Best for**: Complex reasoning, higher quality needs

```python
llm = openai.LLM(
    model="gpt-4o",
    temperature=0.7,
)
```

**Pros**:
- Better reasoning capabilities
- Multimodal (vision) support
- Higher quality responses

**Cons**:
- More expensive
- Slightly slower than gpt-4.1-mini

---

### Anthropic Claude
**Best for**: Complex reasoning, long context, safety

```python
from livekit.plugins import anthropic

llm = anthropic.LLM(
    model="claude-3.5-sonnet",
    temperature=0.7,
)
```

**Pros**:
- Excellent reasoning
- Long context (200k tokens)
- Strong safety features
- Great for complex tasks

**Cons**:
- May be slower than OpenAI
- Higher cost

**Environment**: `ANTHROPIC_API_KEY`

---

### Groq
**Best for**: Ultra-low latency

```python
from livekit.plugins import groq

llm = groq.LLM(
    model="llama-3.3-70b-versatile",
    temperature=0.7,
)
```

**Pros**:
- Extremely fast inference (100+ tokens/sec)
- Low latency
- Cost-effective

**Cons**:
- Limited model selection
- May have lower quality than GPT-4

**Environment**: `GROQ_API_KEY`

---

## Text-to-Speech (TTS) Providers

### Cartesia (Recommended)
**Best for**: Fast, natural-sounding production voice

```python
from livekit.plugins import cartesia

tts = cartesia.TTS(
    model="sonic-2",
    voice="79a125e8-cd45-4c13-8a67-188112f4dd22",  # Default Sonic voice
    language="en",
)
```

**Pros**:
- Very fast (RTF < 0.1)
- Natural-sounding voices
- Low latency streaming
- Good emotional expression
- Cost-effective

**Common voices**:
- `79a125e8-cd45-4c13-8a67-188112f4dd22` - Sonic (versatile)
- `a0e99841-438c-4a64-b679-ae501e7d6091` - British Male
- `b7d50908-b17c-442d-ad8d-810c63997ed9` - British Female

**Environment**: `CARTESIA_API_KEY`

---

### ElevenLabs
**Best for**: Highest quality, expressive voices

```python
from livekit.plugins import elevenlabs

tts = elevenlabs.TTS(
    model_id="eleven_turbo_v2_5",
    voice_id="EXAVITQu4vr4xnSDxMaL",  # Sarah voice
)
```

**Pros**:
- Highest quality voices
- Very expressive
- Custom voice cloning
- Multiple languages

**Cons**:
- More expensive
- May be slower than Cartesia
- Requires more bandwidth

**Environment**: `ELEVENLABS_API_KEY`

---

### OpenAI TTS
**Best for**: Simple integration, good default

```python
from livekit.plugins import openai

tts = openai.TTS(
    model="tts-1",
    voice="alloy",
)
```

**Pros**:
- Easy setup (same API key as LLM)
- Good quality
- Multiple voices
- Reliable

**Cons**:
- Less natural than Cartesia/ElevenLabs
- Limited voice customization

**Voices**: alloy, echo, fable, onyx, nova, shimmer

**Environment**: `OPENAI_API_KEY`

---

## Voice Activity Detection (VAD)

### Silero VAD (Recommended)
**Best for**: All use cases

```python
from livekit.plugins import silero

vad = silero.VAD.load(
    min_speech_duration=0.1,
    min_silence_duration=0.5,
)
```

**Pros**:
- Fast and accurate
- Works across languages
- Low resource usage
- Open source

**No API key required** - runs locally

---

## Turn Detection

### Multilingual Turn Detector (Recommended)
**Best for**: Natural conversation flow

```python
from livekit.plugins import turn_detector

turn_detection = turn_detector.MultilingualModel(
    languages=["en"],  # Add more as needed: ["en", "es", "fr"]
)
```

**Pros**:
- Better conversation flow
- Understands language patterns
- Reduces awkward pauses
- Multilingual support

**Note**: Requires model download (automatic on first use)

---

## Provider Selection Decision Tree

### For Production Voice Agent

**Recommended Stack**:
```python
STT:  deepgram.STT(model="nova-3")
LLM:  openai.LLM(model="gpt-4.1-mini")
TTS:  cartesia.TTS(voice="sonic")
VAD:  silero.VAD.load()
Turn: turn_detector.MultilingualModel(languages=["en"])
```

**Total latency**: ~500-800ms end-to-end

---

### For High Quality

**Premium Stack**:
```python
STT:  assemblyai.STT()
LLM:  openai.LLM(model="gpt-4o")
TTS:  elevenlabs.TTS(model_id="eleven_turbo_v2_5")
VAD:  silero.VAD.load()
Turn: turn_detector.MultilingualModel()
```

---

### For Ultra-Low Latency

**Speed Stack**:
```python
STT:  deepgram.STT(model="nova-3")
LLM:  groq.LLM(model="llama-3.3-70b-versatile")
TTS:  cartesia.TTS(voice="sonic")
VAD:  silero.VAD.load()
Turn: turn_detector.MultilingualModel()
```

**Total latency**: ~300-500ms end-to-end

---

### For Cost Optimization

**Budget Stack**:
```python
STT:  deepgram.STT(model="nova-3")
LLM:  openai.LLM(model="gpt-4.1-mini")
TTS:  openai.TTS(voice="alloy")
VAD:  silero.VAD.load()
Turn: None  # Use simple end-of-speech detection
```

---

### For Offline/Self-Hosted

**Local Stack**:
```python
STT:  openai.STT(model="whisper-1")  # Run locally
LLM:  # Use Ollama or local LLM
TTS:  # Use Coqui TTS or similar
VAD:  silero.VAD.load()
```

**Note**: Requires significant compute (GPU recommended)

---

## Environment Variables Setup

Create `.env.local` file:

```bash
# Required for most setups
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# STT Providers (choose one)
DEEPGRAM_API_KEY=your-deepgram-key
# ASSEMBLYAI_API_KEY=your-assemblyai-key

# LLM Providers (choose one)
OPENAI_API_KEY=your-openai-key
# ANTHROPIC_API_KEY=your-anthropic-key
# GROQ_API_KEY=your-groq-key

# TTS Providers (choose one)
CARTESIA_API_KEY=your-cartesia-key
# ELEVENLABS_API_KEY=your-elevenlabs-key
```

**Auto-generate using LiveKit CLI**:
```bash
lk cloud auth
lk app env -w -d .env.local
```

---

## Cost Comparison (Approximate)

### Per Hour of Conversation

| Provider | STT | LLM (per 1k tokens) | TTS |
|----------|-----|---------------------|-----|
| Deepgram | $0.015/min | - | - |
| AssemblyAI | $0.015/min | - | - |
| OpenAI | $0.006/min (Whisper) | $0.10 (gpt-4.1-mini) | $0.015/1k chars |
| Anthropic | - | $3.00 (claude-3.5-sonnet) | - |
| Groq | - | $0.05-0.10 | - |
| Cartesia | - | - | $0.025/min |
| ElevenLabs | - | - | $0.30/min |

**Typical 1-hour conversation costs** (recommended stack):
- STT (Deepgram): ~$0.90
- LLM (GPT-4.1-mini, ~20k tokens): ~$2.00
- TTS (Cartesia): ~$1.50
- **Total: ~$4.40/hour**

---

## Performance Benchmarks

### Latency Targets

| Component | Target | Good | Excellent |
|-----------|--------|------|-----------|
| STT | 0.2× RT | < 0.3× RT | < 0.15× RT |
| LLM TTFT | 500ms | < 400ms | < 250ms |
| LLM Tokens/sec | 50+ | 70+ | 100+ |
| TTS RTF | 0.1 | < 0.08 | < 0.05 |
| End-to-end | 800ms | < 600ms | < 400ms |

### Provider Performance (Real-world)

Based on production data:

**STT Latency**:
- Deepgram Nova-3: ~0.18× RT
- AssemblyAI: ~0.22× RT
- Whisper (cloud): ~0.35× RT

**LLM Speed**:
- Groq: 100-150 tokens/sec
- GPT-4.1-mini: 60-80 tokens/sec
- GPT-4o: 40-60 tokens/sec
- Claude 3.5 Sonnet: 35-50 tokens/sec

**TTS Latency**:
- Cartesia Sonic-2: RTF 0.06
- OpenAI TTS: RTF 0.08
- ElevenLabs Turbo: RTF 0.10
