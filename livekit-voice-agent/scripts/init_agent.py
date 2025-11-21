#!/usr/bin/env python3
"""
Initialize a new LiveKit voice agent project.

Usage:
    python init_agent.py <project-name> [--path /path/to/output]
"""

import os
import sys
import argparse
from pathlib import Path


def create_directory(path: Path, description: str):
    """Create a directory with error handling."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created {description}: {path}")
    except Exception as e:
        print(f"❌ Error creating {description}: {e}")
        sys.exit(1)


def write_file(path: Path, content: str, description: str):
    """Write content to a file with error handling."""
    try:
        path.write_text(content)
        print(f"✅ Created {description}: {path}")
    except Exception as e:
        print(f"❌ Error creating {description}: {e}")
        sys.exit(1)


def init_agent_project(project_name: str, output_path: str):
    """Initialize a new LiveKit voice agent project."""
    # Validate project name
    if not project_name.replace("-", "").replace("_", "").isalnum():
        print("❌ Error: Project name must contain only letters, numbers, hyphens, and underscores")
        sys.exit(1)

    # Create project directory
    project_path = Path(output_path) / project_name
    if project_path.exists():
        print(f"❌ Error: Directory {project_path} already exists")
        sys.exit(1)

    print(f"🚀 Initializing LiveKit voice agent: {project_name}")
    print(f"   Location: {project_path}\n")

    # Create directories
    create_directory(project_path, "project directory")
    create_directory(project_path / "src", "src directory")
    create_directory(project_path / "tests", "tests directory")

    # Create pyproject.toml
    pyproject_content = f'''[project]
name = "{project_name}"
version = "0.1.0"
description = "LiveKit voice agent"
requires-python = ">=3.11"
dependencies = [
    "livekit>=0.17.0",
    "livekit-agents>=0.10.0",
    "livekit-plugins-deepgram>=0.8.0",
    "livekit-plugins-openai>=0.8.0",
    "livekit-plugins-cartesia>=0.3.0",
    "livekit-plugins-silero>=0.8.0",
    "python-dotenv>=1.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
'''
    write_file(project_path / "pyproject.toml", pyproject_content, "pyproject.toml")

    # Create .env.example
    env_example_content = '''# LiveKit connection
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# STT Provider (choose one)
DEEPGRAM_API_KEY=your-deepgram-api-key

# LLM Provider (choose one)
OPENAI_API_KEY=your-openai-api-key

# TTS Provider (choose one)
CARTESIA_API_KEY=your-cartesia-api-key

# Optional: Logging level
LOG_LEVEL=INFO
'''
    write_file(project_path / ".env.example", env_example_content, ".env.example")

    # Create .gitignore
    gitignore_content = '''.env
.env.local
__pycache__/
*.pyc
.pytest_cache/
.venv/
dist/
*.egg-info/
.DS_Store
'''
    write_file(project_path / ".gitignore", gitignore_content, ".gitignore")

    # Create src/agent.py
    agent_content = '''"""
LiveKit voice agent implementation.
"""

import asyncio
import logging
import sys
from dataclasses import dataclass
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, function_tool, RunContext
from livekit.plugins import deepgram, openai, cartesia, silero, turn_detector

# Load environment variables
load_dotenv(dotenv_path=".env.local")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class UserData:
    """Shared data across the session."""
    name: str = ""
    preferences: dict = None

    def __post_init__(self):
        if self.preferences is None:
            self.preferences = {}


class VoiceAgent(Agent):
    """Main voice agent class."""

    def __init__(self):
        super().__init__(
            instructions="""You are a helpful voice assistant.
            Be concise and conversational. Keep responses under 2-3 sentences unless asked for details.
            Use natural language without markdown formatting."""
        )

    async def on_enter(self, session: AgentSession):
        """Called when agent takes control."""
        logger.info("Agent entered session")
        await session.generate_reply()

    @function_tool
    async def example_tool(
        self,
        context: RunContext,
        query: str
    ):
        """An example tool that demonstrates function calling.

        Args:
            query: The search query
        """
        logger.info(f"Tool called with query: {query}")

        # Your tool logic here
        result = {"status": "success", "query": query}

        return result, f"I processed your query: {query}"


@agents.entrypoint
async def entrypoint(ctx: JobContext):
    """Agent entrypoint - called when a participant joins."""
    logger.info(f"Starting agent for room: {ctx.room.name}")

    # Connect to the room
    await ctx.connect()

    # Initialize user data
    ctx.userdata = UserData()

    # Create agent
    agent = VoiceAgent()

    # Initialize components
    logger.info("Initializing STT, LLM, TTS, VAD...")

    stt = deepgram.STT(
        model="nova-3",
        language="multi",
    )

    llm = openai.LLM(
        model="gpt-4.1-mini",
        temperature=0.7,
    )

    tts = cartesia.TTS(
        model="sonic-2",
        voice="79a125e8-cd45-4c13-8a67-188112f4dd22",  # Default Sonic voice
    )

    vad = silero.VAD.load()

    turn_detection = turn_detector.MultilingualModel(
        languages=["en"]
    )

    # Create agent session
    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=vad,
        turn_detection=turn_detection,
        allow_interruptions=True,
        min_interruption_duration=0.8,
        preemptive_synthesis=True,
    )

    # Start the session
    logger.info("Starting agent session")
    await session.start(room=ctx.room, agent=agent)

    # Wait for session to complete
    await session.wait_for_complete()

    logger.info("Session completed")


def download_models():
    """Download required models."""
    logger.info("Downloading Silero VAD...")
    silero.VAD.load()

    logger.info("Downloading turn detector model...")
    turn_detector.MultilingualModel.load(languages=["en"])

    logger.info("✅ Models downloaded successfully!")


if __name__ == "__main__":
    # Handle download command
    if len(sys.argv) > 1 and sys.argv[1] == "download-files":
        download_models()
        sys.exit(0)

    # Run the agent
    from livekit.agents import cli

    cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
'''
    write_file(project_path / "src" / "agent.py", agent_content, "src/agent.py")

    # Create Dockerfile
    dockerfile_content = '''FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    libssl-dev \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml .

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY src/ ./src/

# Download required models at build time
RUN uv run python src/agent.py download-files

# Expose health check port
EXPOSE 8081

# Run the agent
CMD ["uv", "run", "python", "src/agent.py", "start"]
'''
    write_file(project_path / "Dockerfile", dockerfile_content, "Dockerfile")

    # Create README.md
    readme_content = f'''# {project_name}

A LiveKit voice agent built with Python.

## Setup

### 1. Install dependencies

```bash
pip install uv
uv sync
```

### 2. Configure environment

```bash
# Copy example environment file
cp .env.example .env.local

# Edit .env.local with your API keys
# Get LiveKit credentials with: lk cloud auth && lk app env -w -d .env.local
```

### 3. Download models

```bash
uv run python src/agent.py download-files
```

## Development

### Test locally (console mode)

```bash
uv run python src/agent.py console
```

### Run development server

```bash
uv run python src/agent.py dev
```

### Run production worker

```bash
uv run python src/agent.py start
```

## Deployment

### Docker

```bash
# Build image
docker build -t {project_name}:latest .

# Run container
docker run --env-file .env.local {project_name}:latest
```

### LiveKit Cloud

```bash
lk cloud deploy
```

## Project Structure

```
{project_name}/
├── src/
│   └── agent.py          # Main agent implementation
├── tests/                # Test files
├── .env.example          # Example environment variables
├── pyproject.toml        # Dependencies
├── Dockerfile            # Container definition
└── README.md             # This file
```

## Customization

1. **Modify agent instructions**: Edit the `instructions` in `VoiceAgent.__init__()`
2. **Add tools**: Create new methods with `@function_tool` decorator
3. **Change providers**: Swap STT/LLM/TTS in the `entrypoint()` function
4. **Adjust parameters**: Tune `temperature`, `min_interruption_duration`, etc.

## Resources

- [LiveKit Agents Documentation](https://docs.livekit.io/agents/)
- [LiveKit Python SDK](https://docs.livekit.io/reference/python/)
- [Example Agents](https://github.com/livekit/agents/tree/main/examples)
'''
    write_file(project_path / "README.md", readme_content, "README.md")

    # Create a basic test file
    test_content = '''"""
Tests for the voice agent.
"""

import pytest
from src.agent import VoiceAgent, UserData


def test_agent_initialization():
    """Test agent can be initialized."""
    agent = VoiceAgent()
    assert agent is not None
    assert "helpful" in agent.instructions.lower()


def test_user_data():
    """Test user data structure."""
    user_data = UserData()
    assert user_data.name == ""
    assert isinstance(user_data.preferences, dict)


@pytest.mark.asyncio
async def test_example_tool():
    """Test example tool execution."""
    agent = VoiceAgent()
    from unittest.mock import Mock

    mock_context = Mock()
    result, message = await agent.example_tool(mock_context, "test query")

    assert result["status"] == "success"
    assert "test query" in message
'''
    write_file(project_path / "tests" / "test_agent.py", test_content, "tests/test_agent.py")

    # Done!
    print(f"\n✅ Project '{project_name}' created successfully!\n")
    print("Next steps:")
    print(f"  1. cd {project_name}")
    print("  2. cp .env.example .env.local")
    print("  3. Edit .env.local with your API keys")
    print("  4. uv sync")
    print("  5. uv run python src/agent.py download-files")
    print("  6. uv run python src/agent.py console  # Test locally")


def main():
    parser = argparse.ArgumentParser(description="Initialize a new LiveKit voice agent project")
    parser.add_argument("project_name", help="Name of the project")
    parser.add_argument("--path", default=".", help="Output directory path (default: current directory)")

    args = parser.parse_args()

    init_agent_project(args.project_name, args.path)


if __name__ == "__main__":
    main()
