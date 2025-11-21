# LiveKit Voice Agent

A production-ready voice AI agent built with LiveKit Agents framework, featuring multi-agent workflows and intelligent handoffs.

## Features

- **Multi-Agent Architecture**: Seamlessly handoff conversations between specialized agents
- **Context Preservation**: Maintain conversation state across agent transitions
- **Production Ready**: Built-in testing, Docker deployment, and monitoring
- **Extensible**: Easy to add new agents and custom tools
- **Type Safe**: Full type hints and structured data models

## Architecture

```
IntroAgent → SpecialistAgent → EscalationAgent
              (Routes by category)  (Human handoff)
```

## Prerequisites

- Python 3.9 or later (< 3.14)
- LiveKit account or self-hosted server
- API keys for:
  - OpenAI (LLM and TTS)
  - Deepgram (STT)

## Quick Start

### 1. Install Dependencies

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required environment variables:
- `LIVEKIT_URL`: Your LiveKit server WebSocket URL
- `LIVEKIT_API_KEY`: LiveKit API key
- `LIVEKIT_API_SECRET`: LiveKit API secret
- `OPENAI_API_KEY`: OpenAI API key
- `DEEPGRAM_API_KEY`: Deepgram API key

### 3. Run the Agent

```bash
# Start the agent
uv run python src/agent.py start
```

The agent will:
1. Connect to your LiveKit server
2. Wait for users to join rooms
3. Automatically start conversations when users join

### 4. Test the Agent

Join a LiveKit room using:
- [LiveKit Playground](https://agents-playground.livekit.io/)
- Your own frontend application
- LiveKit CLI: `livekit-cli join-room`

## Project Structure

```
.
├── src/
│   ├── agent.py              # Main entry point
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── intro_agent.py    # Initial greeting & routing
│   │   ├── specialist_agent.py # Domain-specific handling
│   │   └── escalation_agent.py # Human handoff
│   ├── models/
│   │   └── shared_data.py    # Shared context dataclasses
│   └── tools/
│       └── custom_tools.py   # Business-specific tools
├── tests/
│   ├── test_agents/
│   ├── test_tools/
│   └── test_integration/
├── pyproject.toml            # Dependencies
├── .env.example              # Environment template
├── Dockerfile                # Container definition
└── README.md
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_agents/test_intro_agent.py
```

### Adding a New Agent

1. Create agent file in `src/agents/`:

```python
from livekit.agents import Agent
from models.shared_data import ConversationData

class MyNewAgent(Agent):
    def __init__(self, chat_ctx=None):
        super().__init__(
            instructions="Your instructions here...",
            chat_ctx=chat_ctx,
        )

    # Add function tools...
```

2. Import and use in handoff logic:

```python
from agents.my_new_agent import MyNewAgent

@function_tool
async def transfer_to_new_agent(self, context):
    agent = MyNewAgent(chat_ctx=self.chat_ctx)
    return agent, "Transferring..."
```

### Adding Custom Tools

Create function tools for your business logic:

```python
from livekit.agents.llm import function_tool, ToolError
from typing import Annotated

@function_tool
async def my_custom_tool(
    context: RunContext,
    param: Annotated[str, "Parameter description"],
) -> str:
    """Tool description that the LLM sees"""
    try:
        # Your logic here
        result = await your_api_call(param)
        return f"Result: {result}"
    except Exception as e:
        raise ToolError(f"Helpful error message: {e}")
```

## Deployment

### Docker

```bash
# Build image
docker build -t voice-agent .

# Run container
docker run -d \
  --env-file .env \
  --name voice-agent \
  voice-agent
```

### Docker Compose

```yaml
version: '3.8'
services:
  voice-agent:
    build: .
    env_file: .env
    restart: unless-stopped
    environment:
      - LOG_LEVEL=INFO
```

### Kubernetes

See `k8s/` directory for Kubernetes manifests (create as needed).

## Configuration

### Model Selection

Edit `src/agent.py` to change models:

```python
session = AgentSession[ConversationData](
    vad=vad,
    stt=deepgram.STT(model="nova-2-general"),
    llm=openai.LLM(model="gpt-4o-mini"),  # or "gpt-4o"
    tts=openai.TTS(voice="alloy"),  # or echo, fable, onyx, nova, shimmer
    userdata=ConversationData(),
)
```

### Agent Instructions

Customize agent behavior by editing instructions in each agent class:

```python
class IntroAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
            Your custom instructions here...
            """
        )
```

## Monitoring

### Logging

Logs are output to stdout. Configure level in `.env`:

```
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Metrics

Track agent performance:
- Time to first word
- Tool call success rates
- Handoff success rates
- Session durations

Example metrics collection in `src/agent.py`:

```python
from livekit.agents import metrics

collector = metrics.UsageCollector()
session = AgentSession(..., usage_collector=collector)

# Log metrics on completion
logger.info(f"Session usage: {collector.get_summary()}")
```

## Troubleshooting

### Agent Not Starting

- Verify environment variables are set correctly
- Check LiveKit server URL is reachable (WebSocket)
- Ensure API keys are valid

### Poor Voice Quality

- Check network connectivity
- Try different STT/TTS providers
- Adjust VAD sensitivity if needed

### Tools Not Being Called

- Improve tool descriptions in docstrings
- Add more examples in parameter annotations
- Verify tool registration

### Context Lost After Handoff

- Ensure `context.userdata` is updated before handoff
- Pass `chat_ctx=self.chat_ctx` to new agents
- Verify shared data class structure

## Resources

- [LiveKit Documentation](https://docs.livekit.io/)
- [LiveKit Agents Guide](https://docs.livekit.io/agents/)
- [Python SDK Reference](https://docs.livekit.io/reference/python/)
- [Example Projects](https://github.com/livekit-examples)

## License

MIT

## Support

For issues or questions:
- Check [LiveKit Documentation](https://docs.livekit.io/)
- Join [LiveKit Discord](https://livekit.io/discord)
- Open an issue on GitHub
