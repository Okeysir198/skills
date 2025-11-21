"""
Basic usage example for the custom STT plugin.

This example shows how to:
1. Initialize the STT plugin
2. Transcribe an audio file (batch mode)
3. Use streaming mode for real-time transcription
"""

import asyncio
import os
from livekit import agents, rtc
from livekit.plugins import custom_stt


async def transcribe_file_example():
    """Example of batch transcription."""
    print("=== Batch Transcription Example ===")

    # Initialize STT plugin
    stt_plugin = custom_stt.STT(
        api_url=os.getenv("STT_API_URL", "http://localhost:8000"),
        options=custom_stt.STTOptions(
            language="en",  # or None for auto-detection
            task="transcribe",
            beam_size=5,
            vad_filter=True,
        ),
    )

    # Load audio file
    # Note: Replace with your actual audio file
    audio_path = "test_audio.wav"

    if os.path.exists(audio_path):
        print(f"Transcribing {audio_path}...")

        # Read audio file
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        # Create audio buffer
        import numpy as np
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        buffer = agents.utils.AudioBuffer(
            data=audio_array,
            sample_rate=16000,
            num_channels=1,
        )

        # Transcribe
        result = await stt_plugin.recognize(buffer, language="en")

        # Print results
        if result.alternatives:
            print(f"Transcription: {result.alternatives[0].text}")
            print(f"Language: {result.alternatives[0].language}")
            print(f"Confidence: {result.alternatives[0].confidence:.2f}")
        else:
            print("No transcription results")
    else:
        print(f"Audio file not found: {audio_path}")
        print("Please provide a test audio file or modify the path")

    # Clean up
    await stt_plugin.aclose()


async def streaming_example():
    """Example of streaming transcription."""
    print("\n=== Streaming Transcription Example ===")

    # Initialize STT plugin
    stt_plugin = custom_stt.STT(
        api_url=os.getenv("STT_API_URL", "http://localhost:8000"),
        options=custom_stt.STTOptions(
            language="en",
            sample_rate=16000,
        ),
    )

    # Create streaming session
    stream = stt_plugin.stream(language="en")

    print("Streaming session created")
    print("In a real application, you would:")
    print("1. Get audio frames from a microphone or LiveKit room")
    print("2. Push them to the stream with stream.push_frame(frame)")
    print("3. Receive transcription events asynchronously")

    # Simulate pushing some audio frames
    # In a real app, these would come from rtc.AudioSource or room
    print("\nSimulating audio frames...")

    # Example: Create dummy audio frame
    import numpy as np

    # Generate 1 second of silence (for demonstration)
    sample_rate = 16000
    duration = 1.0
    samples = np.zeros(int(sample_rate * duration), dtype=np.int16)

    frame = rtc.AudioFrame(
        data=samples.tobytes(),
        sample_rate=sample_rate,
        num_channels=1,
        samples_per_channel=len(samples),
    )

    # Push frame
    stream.push_frame(frame)
    print("Pushed 1 second of audio")

    # In a real application, you would iterate over events:
    # async for event in stream:
    #     if event.type == agents.stt.SpeechEventType.FINAL_TRANSCRIPT:
    #         print(f"Transcription: {event.alternatives[0].text}")

    # For this demo, just close the stream
    await stream.end_input()
    await stream.aclose()

    print("Streaming session closed")

    # Clean up
    await stt_plugin.aclose()


async def main():
    """Run all examples."""
    print("Custom STT Plugin - Basic Usage Examples")
    print("=" * 50)

    # Check if API is running
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            api_url = os.getenv("STT_API_URL", "http://localhost:8000")
            async with session.get(f"{api_url}/health") as resp:
                if resp.status == 200:
                    health = await resp.json()
                    print(f"✓ STT API is running at {api_url}")
                    print(f"  Status: {health}")
                else:
                    print(f"✗ STT API returned status {resp.status}")
                    return
    except Exception as e:
        print(f"✗ Cannot connect to STT API: {e}")
        print(f"  Make sure the API is running at {os.getenv('STT_API_URL', 'http://localhost:8000')}")
        return

    print()

    # Run examples
    try:
        await transcribe_file_example()
        await streaming_example()
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
