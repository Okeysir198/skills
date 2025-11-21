"""
LiveKit voice agent example using custom STT plugin.

This example demonstrates how to use the custom STT plugin
in a complete LiveKit voice assistant.
"""

import logging
import os
from livekit import agents, rtc
from livekit.plugins import custom_stt

# You'll need to install and import your preferred LLM and TTS plugins
# For example:
# from livekit.plugins import openai, elevenlabs

logger = logging.getLogger("voice-agent")
logger.setLevel(logging.INFO)


async def entrypoint(ctx: agents.JobContext):
    """
    Voice agent entrypoint.

    This function is called when a participant joins the room.
    """
    logger.info(f"Starting voice agent for room: {ctx.room.name}")

    # Initialize STT plugin
    stt_plugin = custom_stt.STT(
        api_url=os.getenv("STT_API_URL", "http://localhost:8000"),
        options=custom_stt.STTOptions(
            language="en",  # Set to None for auto-detection
            task="transcribe",
            beam_size=3,  # Lower for faster real-time performance
            vad_filter=True,  # Filter out silence
            sample_rate=16000,
        ),
    )

    # Initialize LLM (example - replace with your actual LLM)
    # llm = openai.LLM(model="gpt-4")

    # Initialize TTS (example - replace with your actual TTS)
    # tts = elevenlabs.TTS()

    # For this example, we'll use placeholder values
    # Replace these with your actual LLM and TTS plugins
    llm = None  # TODO: Initialize your LLM plugin
    tts = None  # TODO: Initialize your TTS plugin

    if llm is None or tts is None:
        logger.error("LLM and TTS plugins are required. Please configure them.")
        logger.info(
            "Example: pip install livekit-plugins-openai livekit-plugins-elevenlabs"
        )
        return

    # Connect to the room
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")

    # Create voice assistant
    assistant = agents.VoiceAssistant(
        vad=agents.silero.VAD.load(),  # Voice Activity Detection
        stt=stt_plugin,  # Our custom STT plugin
        llm=llm,  # Your LLM
        tts=tts,  # Your TTS
        chat_ctx=agents.ChatContext(
            messages=[
                agents.ChatMessage(
                    role="system",
                    content=(
                        "You are a helpful voice assistant. "
                        "Keep your responses concise and natural for voice interaction."
                    ),
                )
            ]
        ),
    )

    # Start the assistant
    assistant.start(ctx.room)
    logger.info("Voice assistant started")

    # Handle room events
    @ctx.room.on("participant_connected")
    def on_participant_connected(participant: rtc.Participant):
        logger.info(f"Participant connected: {participant.identity}")

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant: rtc.Participant):
        logger.info(f"Participant disconnected: {participant.identity}")

    # Keep the agent running
    await asyncio.Event().wait()


async def main():
    """Main entry point for the voice agent."""
    # Configure worker options
    worker_options = agents.WorkerOptions(
        entrypoint_fnc=entrypoint,
        # Configure with your LiveKit server
        ws_url=os.getenv("LIVEKIT_URL", "ws://localhost:7880"),
        api_key=os.getenv("LIVEKIT_API_KEY"),
        api_secret=os.getenv("LIVEKIT_API_SECRET"),
    )

    # Run the worker
    logger.info("Starting LiveKit worker...")
    await agents.Worker(worker_options).run()


if __name__ == "__main__":
    import asyncio

    # Check environment variables
    required_vars = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.info("Please set the following environment variables:")
        logger.info("  LIVEKIT_URL - Your LiveKit server URL")
        logger.info("  LIVEKIT_API_KEY - Your LiveKit API key")
        logger.info("  LIVEKIT_API_SECRET - Your LiveKit API secret")
        logger.info("  STT_API_URL - URL of your STT API (default: http://localhost:8000)")
        exit(1)

    # Run the agent
    asyncio.run(main())
