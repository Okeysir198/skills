"""
LiveKit Agent Template

A ready-to-use template for creating LiveKit voice agents with function tools.
Customize the instructions, tools, and behavior for your specific use case.
"""

import logging
from pathlib import Path

from dotenv import load_dotenv
from livekit.agents import Agent, JobContext, WorkerOptions, cli
from livekit.agents.llm import function_tool
from livekit.agents.voice import AgentSession, RunContext
from livekit.plugins import silero

# Configure logging
logger = logging.getLogger("my-agent")
logger.setLevel(logging.INFO)

# Load environment variables from .env file
# Create a .env file with: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, OPENAI_API_KEY
load_dotenv(dotenv_path=Path(__file__).parent / '.env')


class MyAgent(Agent):
    """Your custom agent - update the docstring to describe what it does."""

    def __init__(self) -> None:
        super().__init__(
            # Customize these instructions for your agent's personality and capabilities
            instructions="""You are a helpful voice assistant.
            Be concise and conversational since you're speaking, not writing.
            Use your available tools to help the user accomplish their goals.""",

            # Choose your LLM model
            # Options: "openai/gpt-4o-mini", "openai/gpt-4o", "anthropic/claude-3-5-sonnet-20241022"
            llm="openai/gpt-4o-mini",

            # Voice Activity Detection
            vad=silero.VAD.load(),

            # Optional: Customize TTS (text-to-speech)
            # tts="openai/tts-1",

            # Optional: Customize STT (speech-to-text)
            # stt="deepgram/nova-2"
        )

    # Add your custom tools below using the @function_tool decorator

    @function_tool
    async def example_tool(self, parameter: str) -> str:
        """Brief description of what this tool does.

        Provide guidance on when the LLM should use this tool.
        Be specific about what it does and what it returns.

        Args:
            parameter: Description of what this parameter is for
        """
        # Implement your tool logic here
        logger.info(f"example_tool called with: {parameter}")

        # Return a string that the LLM can use to respond to the user
        return f"Tool executed with parameter: {parameter}"

    @function_tool
    async def another_tool(
        self,
        required_param: str,
        optional_param: str | None = None,
        context: RunContext = None
    ) -> str:
        """Another example tool with optional parameters and RunContext.

        Args:
            required_param: This parameter is required
            optional_param: This parameter is optional
            context: Runtime context (automatically provided, gives access to userdata)
        """
        logger.info(f"another_tool called with: {required_param}, {optional_param}")

        # Access user data if needed
        if context and "user_name" in context.userdata:
            user_name = context.userdata["user_name"]
            return f"Hello {user_name}, processing {required_param}"

        return f"Processing {required_param}"

    # Lifecycle hooks (optional)

    async def on_enter(self):
        """Called when the agent enters the conversation."""
        logger.info("Agent entered session")

        # Initialize any session state
        # self.session.userdata["session_start"] = datetime.now()

        # Generate initial greeting
        self.session.generate_reply()

    async def on_exit(self):
        """Called when the agent exits the conversation."""
        logger.info("Agent exiting session")

        # Clean up resources if needed
        pass


async def entrypoint(ctx: JobContext):
    """
    Entry point for the LiveKit agent.

    This function is called when a participant joins a room.
    It creates an agent session and starts the agent.
    """
    logger.info(f"Starting agent for room: {ctx.room.name}")

    # Create agent session
    session = AgentSession()

    # Start the agent
    await session.start(agent=MyAgent(), room=ctx.room)

    logger.info("Agent session started")


if __name__ == "__main__":
    # Run the agent using LiveKit CLI
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
