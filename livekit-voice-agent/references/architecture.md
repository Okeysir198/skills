# LiveKit Voice Agent Architecture

## Overview

LiveKit voice agents are built on a pipeline architecture that orchestrates multiple AI components to create natural, low-latency conversational experiences.

## Core Pipeline: VAD → STT → LLM → TTS

### Voice Activity Detection (VAD)
Detects when the user is speaking to trigger transcription and identify speech boundaries.

**Recommended**: Silero VAD
- Fast and accurate
- Low latency
- Works across languages

```python
from livekit.plugins import silero

vad = silero.VAD.load()
```

### Speech-to-Text (STT)
Converts user speech into text for the LLM to process.

**Performance target**: ~0.2× real-time (5 seconds of audio transcribed in 1 second)

**Common providers**:
- `deepgram/nova-3` - Fast, multilingual, good for production
- `assemblyai` - High accuracy, good for complex audio
- `openai/whisper` - Good offline option

```python
from livekit.plugins import deepgram

stt = deepgram.STT(model="nova-3", language="multi")
```

### Large Language Model (LLM)
Processes transcribed text and generates intelligent responses based on agent instructions and context.

**Performance target**: 50+ tokens/sec for responsive conversations

**Common providers**:
- `openai/gpt-4.1-mini` - Fast, cost-effective
- `openai/gpt-4o` - More capable, higher quality
- `anthropic/claude-3.5-sonnet` - Excellent reasoning
- `groq` - Ultra-fast inference

```python
from livekit.plugins import openai

llm = openai.LLM(model="gpt-4.1-mini")
```

### Text-to-Speech (TTS)
Converts LLM responses into natural-sounding speech.

**Performance target**: RTF 0.1 or better (10 seconds of speech generated in 1 second)

**Common providers**:
- `cartesia/sonic-2` - Fast, natural voices
- `elevenlabs` - High quality, expressive
- `openai` - Good default option

```python
from livekit.plugins import cartesia

tts = cartesia.TTS(voice="79a125e8-cd45-4c13-8a67-188112f4dd22")  # Sonic voice
```

## Agent Session Architecture

### Entry Point Pattern

Every LiveKit agent follows this structure:

```python
from livekit import agents

@agents.entrypoint
async def entrypoint(ctx: agents.JobContext):
    # Called when a participant joins the room
    await ctx.connect()

    # Initialize agent with components
    agent = MyAgent()
    session = agents.AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=vad,
        # ... configuration
    )

    # Start the session
    await session.start(room=ctx.room, agent=agent)
    await session.wait_for_complete()
```

### Agent Class Structure

```python
from livekit import agents

class MyAgent(agents.Agent):
    def __init__(self):
        super().__init__(
            instructions="Your personality and rules here",
            # ... configuration
        )

    async def on_enter(self, session: agents.AgentSession):
        # Called when agent takes control of the session
        await session.generate_reply()
```

## Turn Detection

Manages conversation flow by detecting when the user has finished speaking and it's the agent's turn to respond.

**Types**:
1. **End-of-speech detection** - Simpler, waits for silence
2. **Multilingual turn detection** - Advanced, understands language patterns

```python
from livekit.plugins import turn_detector

turn_detection = turn_detector.MultilingualModel(
    languages=["en", "es", "fr"]  # Specify languages
)
```

## Interruption Handling

Allows users to interrupt the agent while it's speaking, creating more natural conversations.

**Configuration**:
```python
session = agents.AgentSession(
    # ... components
    allow_interruptions=True,
    # Minimum speech duration before considering interruption
    min_interruption_duration=1.0,
)
```

**False interruption handling**:
```python
session = agents.AgentSession(
    # ... components
    false_interruption_timeout=1.0,  # Wait 1s before stopping
)
```

## Preemptive Generation

Start generating LLM response before user finishes speaking to reduce latency.

```python
session = agents.AgentSession(
    # ... components
    preemptive_synthesis=True,
)
```

**Trade-offs**:
- **Pro**: Faster responses (50-200ms improvement)
- **Con**: May generate unused responses if user changes direction

## Context Management

### Chat History
Conversation history is automatically maintained and passed to the LLM.

**Best practices**:
- Keep history concise (limit to last N messages for long conversations)
- Store important context in agent instructions rather than history
- Use system messages for persistent context

### User Data
Share state across agents and tools using `context.userdata`:

```python
@dataclass
class UserData:
    name: str = ""
    phone: str = ""
    preferences: dict = field(default_factory=dict)

# In entrypoint
ctx.userdata = UserData()

# In tools or agents
user_data = context.userdata
user_data.name = "Alice"
```

## Metrics and Observability

Track agent performance and usage:

```python
from livekit.agents.metrics import UsageCollector

usage_collector = UsageCollector()

session = agents.AgentSession(
    # ... components
    metrics_collector=usage_collector,
)

# Access metrics after session
print(f"STT duration: {usage_collector.stt.audio_duration}s")
print(f"LLM tokens: {usage_collector.llm.total_tokens}")
print(f"TTS characters: {usage_collector.tts.characters}")
```

## Speech-to-Speech Alternative

For ultra-low latency, use direct speech-to-speech models (bypassing STT/LLM/TTS pipeline):

**Response time**: 200-300ms (approaching human speeds)

**Trade-offs**:
- **Pro**: Much lower latency
- **Con**: Less flexibility, fewer model choices, harder to debug

This is still experimental - stick with the pipeline approach for most use cases.

## Performance Optimization Tips

1. **Use streaming everywhere**: STT, LLM, and TTS should all stream for minimal latency
2. **Choose fast models**: gpt-4.1-mini over gpt-4o, nova-3 STT, sonic-2 TTS
3. **Enable preemptive synthesis**: For better response times
4. **Optimize prompts**: Shorter instructions = faster LLM responses
5. **Use turn detection**: Better than simple silence detection
6. **Regional deployment**: Deploy close to your users for lower network latency
7. **Monitor metrics**: Track actual performance and optimize bottlenecks
