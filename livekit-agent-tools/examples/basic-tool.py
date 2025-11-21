"""
Basic Tool Example

Demonstrates simple tool implementation with the @function_tool decorator.
Perfect for quick operations that don't require external calls or complex state.
"""

import logging
from pathlib import Path

from dotenv import load_dotenv
from livekit.agents import Agent, JobContext, WorkerOptions, cli
from livekit.agents.llm import function_tool
from livekit.agents.voice import AgentSession
from livekit.plugins import silero

logger = logging.getLogger("basic-tool-example")
logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')


class BasicToolAgent(Agent):
    """Agent demonstrating basic tool patterns."""

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful assistant with basic capabilities.
            You can perform calculations, check the time, and provide information.
            Be concise and friendly in your responses.""",
            llm="openai/gpt-4o-mini",
            vad=silero.VAD.load()
        )

    @function_tool
    async def calculate(self, expression: str) -> str:
        """Perform a mathematical calculation.

        Use this when the user asks you to calculate, compute, or solve a math problem.

        Args:
            expression: Mathematical expression to evaluate (e.g., "2 + 2", "10 * 5")
        """
        try:
            # Safely evaluate mathematical expressions
            # WARNING: In production, use a proper math parser, not eval()
            result = eval(expression, {"__builtins__": {}}, {})
            return f"The result of {expression} is {result}"
        except Exception as e:
            return f"I couldn't calculate '{expression}'. Please check the expression and try again."

    @function_tool
    async def get_current_time(self) -> str:
        """Get the current date and time.

        Use this when the user asks what time it is or what the date is.
        """
        from datetime import datetime
        now = datetime.now()
        return f"The current date and time is {now.strftime('%B %d, %Y at %I:%M %p')}"

    @function_tool
    async def convert_temperature(
        self,
        value: float,
        from_unit: str,
        to_unit: str
    ) -> str:
        """Convert temperature between Celsius and Fahrenheit.

        Args:
            value: Temperature value to convert
            from_unit: Source unit ("celsius" or "fahrenheit")
            to_unit: Target unit ("celsius" or "fahrenheit")
        """
        from_unit = from_unit.lower()
        to_unit = to_unit.lower()

        if from_unit == to_unit:
            return f"{value}° {from_unit.title()} is {value}° {to_unit.title()}"

        if from_unit == "celsius" and to_unit == "fahrenheit":
            result = (value * 9/5) + 32
            return f"{value}° Celsius is {result:.1f}° Fahrenheit"
        elif from_unit == "fahrenheit" and to_unit == "celsius":
            result = (value - 32) * 5/9
            return f"{value}° Fahrenheit is {result:.1f}° Celsius"
        else:
            return f"I can only convert between Celsius and Fahrenheit. You provided: {from_unit} to {to_unit}"

    @function_tool
    async def count_words(self, text: str) -> str:
        """Count the number of words in a text.

        Args:
            text: The text to count words in
        """
        word_count = len(text.split())
        char_count = len(text)
        return f"That text has {word_count} words and {char_count} characters"

    async def on_enter(self):
        """Called when the agent enters the session."""
        self.session.generate_reply()


async def entrypoint(ctx: JobContext):
    """Entry point for the agent."""
    session = AgentSession()
    await session.start(agent=BasicToolAgent(), room=ctx.room)


if __name__ == "__main__":
    # Run the agent
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
