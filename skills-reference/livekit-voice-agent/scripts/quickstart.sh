#!/bin/bash

# LiveKit Voice Agent - Quick Start Script
# This script sets up a new LiveKit voice agent project

set -e  # Exit on error

PROJECT_NAME="${1:-my-voice-agent}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$(dirname "$SCRIPT_DIR")/templates"

echo "🚀 LiveKit Voice Agent - Quick Start"
echo "===================================="
echo ""
echo "Creating project: $PROJECT_NAME"
echo ""

# Create project directory
mkdir -p "$PROJECT_NAME"
cd "$PROJECT_NAME"

# Create project structure
echo "📁 Creating project structure..."
mkdir -p src/{agents,models,tools}
mkdir -p tests/{test_agents,test_tools,test_integration}

# Copy template files
echo "📋 Copying templates..."

# Main entry point
cp "$TEMPLATE_DIR/main_entry_point.py" src/agent.py

# Agents
cp "$TEMPLATE_DIR/agents/intro_agent.py" src/agents/
cp "$TEMPLATE_DIR/agents/specialist_agent.py" src/agents/
cp "$TEMPLATE_DIR/agents/escalation_agent.py" src/agents/

# Models
cp "$TEMPLATE_DIR/models/shared_data.py" src/models/

# Configuration files
cp "$TEMPLATE_DIR/pyproject.toml" .
cp "$TEMPLATE_DIR/.env.example" .
cp "$TEMPLATE_DIR/Dockerfile" .
cp "$TEMPLATE_DIR/README_TEMPLATE.md" README.md

# Create __init__.py files
touch src/__init__.py
touch src/agents/__init__.py
touch src/models/__init__.py
touch src/tools/__init__.py
touch src/tools/custom_tools.py
touch tests/__init__.py

# Create empty custom tools file with example
cat > src/tools/custom_tools.py << 'EOF'
"""
Custom Tools

Add your business-specific function tools here.
"""

from typing import Annotated
from livekit.agents import RunContext
from livekit.agents.llm import function_tool, ToolError


# Example custom tool
@function_tool
async def example_tool(
    context: RunContext,
    parameter: Annotated[str, "Description of the parameter"],
) -> str:
    """
    Example custom tool.

    Replace this with your actual business logic.

    Args:
        parameter: Describe what this parameter does

    Returns:
        Result description
    """
    # Your implementation here
    return f"Processed: {parameter}"


# Add more tools as needed...
EOF

# Create example test
cat > tests/test_agents/test_intro_agent.py << 'EOF'
"""
Tests for IntroAgent
"""

import pytest
from livekit.agents import AgentSession
from livekit.plugins import openai

from agents.intro_agent import IntroAgent
from models.shared_data import ConversationData


@pytest.mark.asyncio
async def test_intro_agent_greets():
    """Test that intro agent greets the user"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = IntroAgent()
        await sess.start(agent)

        result = await sess.run(user_input="Hello")

        # Verify greeting
        result.expect.next_event().is_message(role="assistant")
        result.expect.contains_message("help")


@pytest.mark.asyncio
async def test_intro_agent_collects_name():
    """Test that intro agent collects user's name"""
    async with AgentSession(
        llm=openai.LLM(model="gpt-4o-mini"),
        userdata=ConversationData(),
    ) as sess:
        agent = IntroAgent()
        await sess.start(agent)

        await sess.run(user_input="Hi, my name is Alice")

        # Verify name was stored
        assert sess.userdata.user_name == "Alice"


# Add more tests...
EOF

# Create .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environment
.env
.env.local

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# uv
.uv/
uv.lock

# Logs
*.log
EOF

echo ""
echo "✅ Project structure created!"
echo ""
echo "📦 Installing dependencies..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "⚠️  uv not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Install dependencies
uv sync

echo ""
echo "✅ Dependencies installed!"
echo ""
echo "🔧 Next steps:"
echo ""
echo "1. Configure your environment:"
echo "   cd $PROJECT_NAME"
echo "   cp .env.example .env"
echo "   # Edit .env with your API keys"
echo ""
echo "2. Customize your agents:"
echo "   # Edit files in src/agents/"
echo "   # Add custom tools in src/tools/"
echo ""
echo "3. Run your agent:"
echo "   uv run python src/agent.py start"
echo ""
echo "4. Run tests:"
echo "   uv run pytest"
echo ""
echo "📚 Read README.md for detailed documentation"
echo ""
echo "🎉 Happy building!"
