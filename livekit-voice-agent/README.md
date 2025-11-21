# LiveKit Voice Agent Skill

A comprehensive skill for building production-ready LiveKit voice AI agents with multi-agent workflows and intelligent handoffs.

## What This Skill Provides

This skill helps Claude Code users build sophisticated voice AI agents using the LiveKit Agents framework. It includes:

- **Complete Implementation Guide**: Step-by-step process from research to deployment
- **Working Templates**: Production-ready code for agents, tools, and configuration
- **Best Practices**: Proven patterns from real-world LiveKit deployments
- **Testing Framework**: Complete testing guide with examples
- **Multi-Agent Patterns**: Linear pipeline, hub-and-spoke, escalation, and bidirectional handoffs
- **Quick Start Script**: Get a working agent in minutes

## When to Use This Skill

Use this skill when building:
- Real-time voice AI agents
- Multi-agent conversational systems
- Customer support automation with escalation
- Voice-based ordering or booking systems
- Any application requiring intelligent agent handoffs

## Skill Contents

```
livekit-voice-agent/
├── SKILL.md                        # Main skill instructions
├── README.md                       # This file
├── reference/
│   ├── agent_best_practices.md    # Production patterns and anti-patterns
│   ├── multi_agent_patterns.md    # Common multi-agent architectures
│   └── testing_guide.md           # Comprehensive testing guide
├── templates/
│   ├── main_entry_point.py        # Agent server entry point
│   ├── agents/                    # Agent class templates
│   │   ├── intro_agent.py
│   │   ├── specialist_agent.py
│   │   └── escalation_agent.py
│   ├── models/
│   │   └── shared_data.py         # Shared context dataclasses
│   ├── pyproject.toml             # Dependencies configuration
│   ├── .env.example               # Environment variables
│   ├── Dockerfile                 # Container definition
│   └── README_TEMPLATE.md         # Project README template
└── scripts/
    └── quickstart.sh              # Quick project setup
```

## Quick Start

To use this skill with Claude Code:

1. **Start a conversation** about building a LiveKit voice agent
2. **Claude will load this skill** and guide you through:
   - Researching LiveKit documentation
   - Planning your agent workflow
   - Implementing agents and handoffs
   - Adding custom tools
   - Testing and deployment

3. **Or use the quick start script**:
   ```bash
   cd /path/to/your/projects
   /path/to/skills/livekit-voice-agent/scripts/quickstart.sh my-voice-agent
   ```

## Features

### Multi-Agent Architecture

Build systems where specialized agents hand off conversations:

```
IntroAgent → SpecialistAgent → EscalationAgent → Human Operator
```

- **Linear Pipeline**: Sequential workflows (ordering, onboarding)
- **Hub & Spoke**: Central router to specialists (support, sales)
- **Escalation**: Progressive assistance (tier 1, tier 2, human)
- **Bidirectional**: Temporary consultations with return

### Context Preservation

Maintain conversation state across handoffs:
- User information
- Conversation history
- Issue details
- Resolution status

### Production Ready

- Docker deployment
- Pytest testing framework
- Structured logging
- Metrics collection
- Error handling

### Extensible

- Easy to add new agents
- Simple tool creation
- Customizable instructions
- Flexible model selection

## Architecture

### Core Components

1. **AgentSession**: Orchestrates conversation, manages shared services (VAD, STT, LLM, TTS)
2. **Agent Classes**: Individual agents with specific instructions and tools
3. **Handoff Mechanism**: Function tools that return new agent instances
4. **Shared Context**: UserData dataclass persisting information across handoffs

### Workflow Example

```python
# Intro agent greets and routes
class IntroAgent(Agent):
    @function_tool
    async def transfer_to_specialist(self, context, category):
        context.userdata.category = category
        return SpecialistAgent(category), "Connecting to specialist..."

# Specialist handles domain-specific tasks
class SpecialistAgent(Agent):
    @function_tool
    async def escalate_to_human(self, context, reason):
        return EscalationAgent(), "Connecting to operator..."
```

## Prerequisites

- Python 3.9+ (< 3.14)
- LiveKit account or self-hosted server
- API keys for:
  - OpenAI (LLM & TTS)
  - Deepgram (STT)

## Tech Stack

- **Framework**: LiveKit Agents (1.3.3+)
- **LLM**: OpenAI GPT-4o/GPT-4o-mini
- **STT**: Deepgram Nova-2
- **TTS**: OpenAI TTS
- **VAD**: Silero
- **Package Manager**: uv
- **Testing**: pytest + pytest-asyncio

## Documentation

### Main Guide
- Read `SKILL.md` for complete implementation instructions

### Reference Docs
- `reference/agent_best_practices.md` - Production patterns
- `reference/multi_agent_patterns.md` - Architecture patterns
- `reference/testing_guide.md` - Testing guide

### Templates
- `templates/main_entry_point.py` - Server setup
- `templates/agents/` - Agent implementations
- `templates/models/` - Data models

## Examples

The skill includes complete working examples:

### Customer Support Flow
```
Greeting → Triage → Technical Support → Escalation
```

### Restaurant Ordering
```
Welcome → Menu → Order Taking → Payment → Confirmation
```

### Sales Pipeline
```
Intro → Qualification → Demo Scheduling → Account Executive
```

## Contributing

This skill is designed to be extended. To add new patterns or examples:

1. Add reference documentation to `reference/`
2. Create templates in `templates/`
3. Update `SKILL.md` with references
4. Test thoroughly

## Resources

- [LiveKit Documentation](https://docs.livekit.io/)
- [LiveKit Agents Guide](https://docs.livekit.io/agents/)
- [Agent Examples](https://github.com/livekit/agents/tree/main/examples)
- [LiveKit Playground](https://agents-playground.livekit.io/)

## License

MIT

## Version

1.0.0 - Initial release with comprehensive multi-agent support

---

**Created for Claude Code** to help developers build sophisticated voice AI agents with LiveKit.
