"""
LiveKit Voice Agent - Main Entry Point

This is the main entry point for your LiveKit voice agent application.
It sets up the agent server, prewarming, and session management.
"""

import logging
from dotenv import load_dotenv

from livekit.agents import (
    AgentSession,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
)
from livekit.plugins import openai, deepgram, silero

# Import your agents
from agents.intro_agent import IntroAgent
from models.shared_data import ConversationData

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("voice-agent")


def prewarm(proc: JobProcess):
    """
    Prewarm function: Load static resources before sessions start.

    This function is called once per worker process to load expensive
    resources that can be reused across multiple agent sessions.

    Best practices:
    - Load VAD models (expensive, reusable)
    - Load ML models or embeddings
    - Initialize connection pools
    - Load static configuration

    Do NOT:
    - Load user-specific data (no user context yet)
    - Make network calls for dynamic data
    - Initialize per-session resources
    """
    logger.info("Prewarming worker process...")

    # Load VAD model (Voice Activity Detection)
    # This is expensive but reusable across all sessions
    proc.userdata["vad"] = silero.VAD.load()

    logger.info("Prewarm complete")


async def entrypoint(ctx: JobContext):
    """
    Main entry point for agent sessions.

    This function is called for each new user session. It sets up the
    AgentSession with shared services and starts with the initial agent.

    Best practices:
    - Connect to room ASAP (await ctx.connect() early)
    - Use prewarmed resources from ctx.proc.userdata
    - Load user-specific data after connect()
    - Handle errors gracefully
    """
    logger.info(f"Starting agent session for room: {ctx.room.name}")

    # Get prewarmed VAD from process userdata
    vad = ctx.proc.userdata["vad"]

    # Initialize AgentSession with shared services
    # These services are available to all agents unless overridden
    session = AgentSession[ConversationData](
        vad=vad,  # Voice Activity Detection

        # Speech-to-Text: Converts user speech to text
        stt=deepgram.STT(
            model="nova-2-general",  # Use nova-2 for better accuracy
        ),

        # Large Language Model: Powers agent reasoning
        llm=openai.LLM(
            model="gpt-4o-mini",  # Fast and cost-effective
            # model="gpt-4o",  # Use for more complex reasoning
        ),

        # Text-to-Speech: Converts agent text to speech
        tts=openai.TTS(
            voice="alloy",  # Options: alloy, echo, fable, onyx, nova, shimmer
        ),

        # Shared context: Persists across all agent handoffs
        userdata=ConversationData(),
    )

    # Connect to the LiveKit room
    # IMPORTANT: Do this BEFORE expensive operations
    await ctx.connect()

    # Optional: Load user-specific data from room metadata
    # user_id = ctx.room.metadata.get("user_id")
    # if user_id:
    #     user_profile = await load_user_profile(user_id)
    #     session.userdata.user_email = user_profile.email

    # Start with the initial agent
    intro_agent = IntroAgent()

    # Run the session
    # This handles the entire conversation and all agent handoffs
    try:
        await session.start(agent=intro_agent, room=ctx.room)
    except Exception as e:
        logger.error(f"Session error: {e}", exc_info=True)
        raise


# Main execution
if __name__ == "__main__":
    # Run the agent server
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
