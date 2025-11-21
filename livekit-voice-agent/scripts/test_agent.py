#!/usr/bin/env python3
"""
Test a LiveKit voice agent locally in console mode.

Usage:
    python test_agent.py [path/to/agent.py]
"""

import sys
import subprocess
import os
from pathlib import Path


def test_agent(agent_path: str = "src/agent.py"):
    """Test the agent in console mode."""
    agent_file = Path(agent_path)

    if not agent_file.exists():
        print(f"❌ Error: Agent file not found: {agent_path}")
        print("   Expected location: src/agent.py")
        sys.exit(1)

    # Check for .env.local
    env_file = Path(".env.local")
    if not env_file.exists():
        print("⚠️  Warning: .env.local not found")
        print("   Copy .env.example to .env.local and configure your API keys")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(0)

    print("🚀 Starting agent in console mode...")
    print("   You can speak or type your messages")
    print("   Press Ctrl+C to exit\n")

    try:
        # Run the agent in console mode
        subprocess.run(
            [sys.executable, str(agent_file), "console"],
            check=True
        )
    except KeyboardInterrupt:
        print("\n\n✅ Agent testing stopped")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running agent: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) > 1:
        agent_path = sys.argv[1]
    else:
        agent_path = "src/agent.py"

    test_agent(agent_path)


if __name__ == "__main__":
    main()
