---
name: livekit-voice-agent
description: Build production-ready LiveKit voice agents with proper architecture, component selection, tool calling, multi-agent workflows, and deployment. Use when building real-time conversational AI applications, voice assistants, phone systems (IVR), customer service bots, or any voice-based AI agents using LiveKit. Includes patterns for tool calling, RAG, multi-agent handoffs, and production deployment configurations.
---

# LiveKit Voice Agent Builder

Build production-ready real-time voice AI agents using LiveKit's agent framework.

## Quick Start

### Create a new voice agent project

```bash
python scripts/init_agent.py my-voice-agent
cd my-voice-agent
cp .env.example .env.local
# Edit .env.local with your API keys
uv sync
uv run python src/agent.py download-files
uv run python src/agent.py console  # Test locally
```

### Component selection decision tree

1. **STT** (Speech-to-Text):
   - **Production**: Deepgram nova-3 (fast, multilingual)
   - **High accuracy**: AssemblyAI
   - **Offline**: Whisper local

2. **LLM** (Language Model):
   - **Fast & cheap**: OpenAI gpt-4.1-mini
   - **High quality**: OpenAI gpt-4o or Anthropic claude-3.5-sonnet
   - **Ultra-fast**: Groq llama-3.3-70b

3. **TTS** (Text-to-Speech):
   - **Production**: Cartesia sonic-2 (fast, natural)
   - **Premium quality**: ElevenLabs
   - **Simple**: OpenAI TTS

**Recommended production stack**: Deepgram + GPT-4.1-mini + Cartesia (~$4.40/hour, 500-800ms latency)

---

## Architecture Overview

LiveKit voice agents use a pipeline architecture:

**VAD → STT → LLM → TTS**

- **VAD**: Detects when user is speaking
- **STT**: Converts speech to text
- **LLM**: Processes text and generates responses
- **TTS**: Converts responses to speech

**Key features**:
- Streaming throughout pipeline (minimal latency)
- Interruption handling (natural conversations)
- Turn detection (conversation flow management)
- Tool calling (external API integration)
- Multi-agent workflows (handoffs between specialized agents)

**See**: `references/architecture.md` for detailed pipeline information

---

## Building Voice Agents

### Basic Agent Structure

```python
from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, function_tool, RunContext
from livekit.plugins import deepgram, openai, cartesia, silero, turn_detector

class MyAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="You are a helpful assistant. Be concise."
        )

    async def on_enter(self, session: AgentSession):
        await session.generate_reply()

    @function_tool
    async def my_tool(self, context: RunContext, param: str):
        """Tool description for LLM."""
        # Tool logic
        return result, "Voice response"

@agents.entrypoint
async def entrypoint(ctx: JobContext):
    await ctx.connect()

    agent = MyAgent()
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4.1-mini"),
        tts=cartesia.TTS(voice="sonic"),
        vad=silero.VAD.load(),
        turn_detection=turn_detector.MultilingualModel(languages=["en"]),
    )

    session.start(ctx.room)
    await session.wait_for_complete()
```

---

## Common Patterns

### Tool Calling (Function Calling)

Add external API integration:

```python
@function_tool
async def lookup_weather(self, context: RunContext, location: str):
    """Look up current weather.

    Args:
        location: City name
    """
    # Call external API
    data = await fetch_weather(location)

    # Return (result, voice_message)
    return data, f"The weather in {location} is {data['temp']} degrees."
```

**Pattern**: `@function_tool` decorator, type hints, docstring, tuple return

**See**: `references/patterns.md` section "Tool Calling" for advanced patterns
**Example**: `assets/examples/tool_calling_agent.py` for complete implementation

### Multi-Agent Workflows

Route between specialized agents:

```python
@function_tool
async def transfer_to_support(self, context: RunContext):
    """Transfer to technical support."""
    user_data = context.userdata
    user_data.prev_agent = context.session.current_agent
    return user_data.agents['support'], "Transferring to support."
```

**Pattern**: Return target agent from tool to trigger handoff

**See**: `references/patterns.md` section "Multi-Agent Workflows"
**Example**: `assets/examples/multi_agent_workflow.py` for customer service flow

### RAG (Retrieval Augmented Generation)

Integrate knowledge bases:

```python
@function_tool
async def search_docs(self, context: RunContext, query: str):
    """Search documentation."""
    results = self.vector_db.query(query)
    context_text = "\n".join(results['documents'][0])
    return results, f"Based on the docs: {context_text}"
```

**See**: `references/patterns.md` section "RAG" for embedding search patterns

### Other Patterns Available

- Background audio
- Push-to-talk (non-VAD)
- Structured output (emotion control)
- Phone integration (SIP/Twilio)
- Interrupt handling
- Speaker diarization

**See**: `references/patterns.md` for all pattern implementations

---

## Provider Selection

**Comprehensive provider comparison**: See `references/providers.md` for:
- Detailed provider capabilities
- Performance benchmarks
- Cost comparison
- Setup instructions
- Environment variable configuration

**Quick lookup**:
- **Latency targets**: STT ~0.2× RT, LLM 50+ tokens/sec, TTS RTF 0.1
- **Stack recommendations**: Production, premium, speed, budget, offline

---

## Deployment

### Docker Deployment

**Basic Dockerfile** (included in init_agent.py template):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN pip install uv
COPY pyproject.toml .
RUN uv sync --frozen
COPY src/ ./src/
RUN uv run python src/agent.py download-files
CMD ["uv", "run", "python", "src/agent.py", "start"]
```

### Deployment Options

1. **LiveKit Cloud** (recommended): Fully managed, auto-scaling
   ```bash
   lk cloud deploy
   ```

2. **Kubernetes**: Self-managed clusters
   - 4 cores, 8GB RAM per worker
   - 10-25 concurrent sessions per worker
   - See `references/deployment.md` for manifests

3. **Render/Railway**: Simple cloud deployment

4. **AWS ECS/Fargate**: Container orchestration

**See**: `references/deployment.md` for:
- Complete deployment configurations
- Environment variable management
- Graceful shutdown patterns
- Health checks
- Monitoring and logging
- Performance optimization
- Cost optimization strategies

### Infrastructure Requirements

- **Compute**: 4 cores, 8GB RAM per worker
- **Capacity**: 10-25 concurrent sessions per worker
- **Network**: Outbound WebSocket only (no inbound ports)
- **Storage**: 10GB ephemeral
- **Grace period**: 600s for long conversations

---

## Development Workflow

### Local Testing

```bash
# Console mode (text/voice in terminal)
python src/agent.py console

# Dev mode (with auto-reload)
python src/agent.py dev

# Production mode
python src/agent.py start
```

### Common Commands

```bash
# Download models
python src/agent.py download-files

# Run tests
pytest tests/

# Build Docker image
docker build -t my-agent .

# Generate LiveKit config
lk cloud auth
lk app env -w -d .env.local
```

---

## Decision Trees

### When to Use Which Pattern?

**Single task, no external data** → Basic agent with instructions

**Need external APIs or data** → Add tool calling

**Multiple specialized tasks** → Multi-agent workflow

**Large knowledge base** → RAG pattern with vector database

**Complex conversation flow** → Multi-agent with task groups

**Phone system integration** → Phone pattern + SIP configuration

### Troubleshooting Decision Tree

**High latency** → Check `references/deployment.md` "Performance Optimization"

**Interruptions not working** → Review `references/patterns.md` "Interrupt Handling"

**Tools not being called** → Check tool descriptions and instructions

**Connection issues** → Verify `LIVEKIT_URL`, `API_KEY`, `API_SECRET`

**Model download errors** → Run `download-files` at build time, not runtime

---

## Resources

### Scripts

- **init_agent.py**: Bootstrap new voice agent project with all boilerplate
- **test_agent.py**: Test agent locally in console mode

### References

- **architecture.md**: Pipeline details, turn detection, interruption handling, metrics
- **providers.md**: Complete STT/LLM/TTS provider comparison, costs, performance
- **patterns.md**: Tool calling, RAG, multi-agent, phone integration, all patterns
- **deployment.md**: Docker, Kubernetes, LiveKit Cloud, monitoring, optimization

### Examples

- **tool_calling_agent.py**: Weather lookup, product search, preferences
- **multi_agent_workflow.py**: Customer service with greeter, support, sales, billing agents

---

## Best Practices

1. **Keep instructions concise**: Shorter prompts = faster LLM, lower cost
2. **Use streaming everywhere**: STT, LLM, TTS all streaming for minimal latency
3. **Download models at build time**: Not runtime (add to Dockerfile)
4. **Choose fast models**: gpt-4.1-mini over gpt-4o, nova-3 STT, sonic-2 TTS
5. **Enable preemptive synthesis**: Faster responses (50-200ms improvement)
6. **Use connection pooling**: Reuse HTTP clients for external APIs
7. **Monitor metrics**: Track STT duration, LLM tokens, TTS characters
8. **Graceful shutdown**: Allow 600s for active conversations to complete
9. **Regional deployment**: Deploy close to users for lower network latency
10. **Test in console mode**: Use `python agent.py console` for rapid iteration

---

## Common Workflows

### Build a customer service voice agent

1. Run `python scripts/init_agent.py customer-service`
2. Load `references/patterns.md` → "Multi-Agent Workflows"
3. Use `assets/examples/multi_agent_workflow.py` as template
4. Customize agents: greeter, support, billing
5. Add tools for ticketing system, account lookup
6. Load `references/deployment.md` for production deployment
7. Deploy to LiveKit Cloud or Kubernetes

### Build a voice agent with external API access

1. Run `python scripts/init_agent.py api-agent`
2. Load `references/patterns.md` → "Tool Calling"
3. Use `assets/examples/tool_calling_agent.py` as template
4. Add `@function_tool` methods for each API
5. Test with `python src/agent.py console`
6. Deploy when ready

### Build a knowledge base voice agent

1. Run `python scripts/init_agent.py kb-agent`
2. Load `references/patterns.md` → "RAG"
3. Integrate vector database (ChromaDB, Pinecone, etc.)
4. Create `search_knowledge_base` tool
5. Load documents into vector DB
6. Test and deploy

### Optimize latency for production

1. Load `references/providers.md` → "Ultra-Low Latency" stack
2. Switch to: Deepgram + Groq + Cartesia
3. Enable `preemptive_synthesis=True`
4. Load `references/deployment.md` → "Performance Optimization"
5. Deploy regionally close to users
6. Monitor metrics and tune

---

## When to Load Reference Files

Load references on-demand based on user needs:

- **architecture.md**: When user asks about pipeline, VAD, turn detection, context management
- **providers.md**: When choosing STT/LLM/TTS, comparing costs, or optimizing performance
- **patterns.md**: When implementing specific features (tools, RAG, multi-agent, phone)
- **deployment.md**: When deploying to production, scaling, monitoring, or troubleshooting

---

## Quick Reference

**Initialize project**: `python scripts/init_agent.py <name>`
**Test locally**: `python src/agent.py console`
**Deploy**: `lk cloud deploy` or Docker
**Add tools**: `@function_tool` decorator
**Multi-agent**: Return agent from tool
**Production stack**: Deepgram + GPT-4.1-mini + Cartesia
**Performance**: 500-800ms end-to-end, 50+ tokens/sec LLM
**Capacity**: 10-25 sessions per worker (4 cores, 8GB)
**Cost**: ~$4.40/hour for production stack
