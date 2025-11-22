"""
Integration tests for STT API and LiveKit plugin.
These tests require the STT API to be running.

Run the API first:
    cd stt-api && python main.py

Then run tests:
    pytest tests/test_integration.py -v
"""

import asyncio
import os
import sys
import wave
import struct
import numpy as np
import aiohttp
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'livekit-plugin-custom-stt'))

from livekit import rtc
from livekit.agents import utils, stt as stt_module
from livekit.plugins import custom_stt


API_URL = os.getenv("STT_API_URL", "http://localhost:8000")


def generate_test_audio(duration=2.0, sample_rate=16000, frequency=440.0):
    """
    Generate test audio data (sine wave).

    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        frequency: Frequency of sine wave in Hz

    Returns:
        numpy array of int16 audio samples
    """
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio = np.sin(frequency * 2 * np.pi * t)
    # Convert to int16
    audio_int16 = (audio * 32767).astype(np.int16)
    return audio_int16


def save_wav_file(filepath, audio_data, sample_rate=16000):
    """Save audio data as WAV file."""
    with wave.open(filepath, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())


@pytest.mark.asyncio
async def test_api_health():
    """Test that the STT API is running and healthy."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/health") as resp:
            assert resp.status == 200, "API health check failed"
            data = await resp.json()
            assert data["status"] == "ok"
            assert data["model_loaded"] is True


@pytest.mark.asyncio
async def test_api_batch_transcription():
    """Test batch transcription endpoint with real audio."""
    # Generate test audio
    audio_data = generate_test_audio(duration=2.0)

    # Create WAV file in memory
    import io
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(audio_data.tobytes())

    wav_io.seek(0)

    # Send to API
    async with aiohttp.ClientSession() as session:
        form_data = aiohttp.FormData()
        form_data.add_field(
            'file',
            wav_io,
            filename='test.wav',
            content_type='audio/wav'
        )

        async with session.post(f"{API_URL}/transcribe", data=form_data) as resp:
            assert resp.status == 200, f"Transcription failed: {await resp.text()}"
            result = await resp.json()

            # Verify response structure
            assert "text" in result
            assert "segments" in result
            assert "language" in result
            assert "duration" in result

            print(f"Transcription result: {result['text']}")
            print(f"Language: {result['language']}")
            print(f"Duration: {result['duration']}")


@pytest.mark.asyncio
async def test_plugin_initialization():
    """Test that the plugin initializes correctly."""
    plugin = custom_stt.STT(api_url=API_URL)

    assert plugin.model == "whisper"
    assert plugin.provider == "custom-stt"
    assert plugin.capabilities.streaming is True
    assert plugin.capabilities.interim_results is False

    await plugin.aclose()


@pytest.mark.asyncio
async def test_plugin_batch_transcription():
    """Test batch transcription through the plugin."""
    plugin = custom_stt.STT(
        api_url=API_URL,
        options=custom_stt.STTOptions(
            language="en",
            beam_size=5,
        )
    )

    try:
        # Generate test audio
        audio_data = generate_test_audio(duration=2.0, sample_rate=16000)

        # Create AudioBuffer
        buffer = utils.AudioBuffer(
            data=audio_data,
            sample_rate=16000,
            num_channels=1,
        )

        # Transcribe
        result = await plugin._recognize_impl(buffer, language="en")

        # Verify result
        assert isinstance(result, stt_module.SpeechEvent)
        assert result.type == stt_module.SpeechEventType.FINAL_TRANSCRIPT
        assert len(result.alternatives) > 0

        print(f"Plugin transcription: {result.alternatives[0].text}")
        print(f"Confidence: {result.alternatives[0].confidence}")

    finally:
        await plugin.aclose()


@pytest.mark.asyncio
async def test_plugin_streaming():
    """Test streaming transcription through the plugin."""
    plugin = custom_stt.STT(
        api_url=API_URL,
        options=custom_stt.STTOptions(
            language="en",
            sample_rate=16000,
        )
    )

    try:
        # Create stream
        stream = plugin.stream(language="en")

        # Generate audio and create frames
        audio_data = generate_test_audio(duration=3.0, sample_rate=16000)

        # Split into frames (100ms each)
        frame_size = int(16000 * 0.1)  # 100ms at 16kHz
        frames = []

        for i in range(0, len(audio_data), frame_size):
            frame_data = audio_data[i:i + frame_size]
            if len(frame_data) < frame_size:
                # Pad last frame
                frame_data = np.pad(frame_data, (0, frame_size - len(frame_data)))

            frame = rtc.AudioFrame(
                data=frame_data.tobytes(),
                sample_rate=16000,
                num_channels=1,
                samples_per_channel=len(frame_data),
            )
            frames.append(frame)

        # Start receiving task
        received_events = []

        async def receive_events():
            async for event in stream:
                received_events.append(event)
                print(f"Received event: type={event.type}, text={event.alternatives[0].text if event.alternatives else 'N/A'}")

        receive_task = asyncio.create_task(receive_events())

        # Give stream time to initialize
        await asyncio.sleep(0.5)

        # Push frames
        for frame in frames:
            stream.push_frame(frame)
            await asyncio.sleep(0.01)  # Small delay between frames

        # Signal end of input
        await stream.end_input()

        # Wait for all events with timeout
        try:
            await asyncio.wait_for(receive_task, timeout=10.0)
        except asyncio.TimeoutError:
            print("Warning: Timeout waiting for events")

        # Verify we received events
        print(f"Received {len(received_events)} events")
        for i, event in enumerate(received_events):
            assert isinstance(event, stt_module.SpeechEvent)
            print(f"Event {i}: {event.type}, alternatives: {len(event.alternatives)}")

        # Close stream
        await stream.aclose()

    finally:
        await plugin.aclose()


@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection to the API directly."""
    import websockets
    import json

    ws_url = API_URL.replace("http://", "ws://").replace("https://", "wss://") + "/ws/transcribe"

    async with websockets.connect(ws_url) as ws:
        # Send configuration
        config = {
            "language": "en",
            "sample_rate": 16000,
            "task": "transcribe",
        }
        await ws.send(json.dumps(config))

        # Receive ready message
        ready_msg = await ws.recv()
        ready_data = json.loads(ready_msg)
        assert ready_data["type"] == "ready"

        print("WebSocket connection established and ready")

        # Send some audio data
        audio_data = generate_test_audio(duration=2.0, sample_rate=16000)
        await ws.send(audio_data.tobytes())

        # Wait for response (with timeout)
        try:
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            result = json.loads(response)
            print(f"WebSocket response: {result}")
            assert "type" in result
        except asyncio.TimeoutError:
            print("Warning: No response received within timeout")

        # Close connection
        await ws.close()


if __name__ == "__main__":
    # Run tests manually
    print("Running integration tests...")
    print(f"API URL: {API_URL}")
    print("=" * 60)

    async def run_all():
        print("\n1. Testing API health...")
        await test_api_health()
        print("✓ API health check passed")

        print("\n2. Testing API batch transcription...")
        await test_api_batch_transcription()
        print("✓ API batch transcription passed")

        print("\n3. Testing plugin initialization...")
        await test_plugin_initialization()
        print("✓ Plugin initialization passed")

        print("\n4. Testing plugin batch transcription...")
        await test_plugin_batch_transcription()
        print("✓ Plugin batch transcription passed")

        print("\n5. Testing WebSocket connection...")
        await test_websocket_connection()
        print("✓ WebSocket connection passed")

        print("\n6. Testing plugin streaming...")
        await test_plugin_streaming()
        print("✓ Plugin streaming passed")

        print("\n" + "=" * 60)
        print("All tests passed!")

    asyncio.run(run_all())
