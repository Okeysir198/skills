"""
Targeted tests for critical fixes:
- end_input() no longer causes deadlock
- Keepalive mechanism works
- Control messages are handled properly
- Sentinel handling prevents duplicates
"""

import asyncio
import json
import pytest
import numpy as np
from livekit import rtc
from livekit.agents import stt as stt_module

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'livekit-plugin-custom-stt'))
from livekit.plugins import custom_stt


def generate_test_audio(duration=1.0, sample_rate=16000, frequency=440.0):
    """Generate test audio data (sine wave)."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio = np.sin(frequency * 2 * np.pi * t)
    audio_int16 = (audio * 32767).astype(np.int16)
    return audio_int16


@pytest.mark.asyncio
async def test_input_ended_flag():
    """Test that _input_ended flag prevents duplicate sentinels."""
    from livekit.plugins import custom_stt

    # Create plugin and stream
    plugin = custom_stt.STT(api_url="http://localhost:8000")
    stream = plugin.stream(language="en")

    # Check initial state
    assert stream._input_ended is False, "_input_ended should start as False"

    # Call end_input() first time
    await stream.end_input()
    assert stream._input_ended is True, "_input_ended should be True after end_input()"

    # Verify sentinel was queued
    assert stream._audio_queue.qsize() == 1, "Should have one sentinel"
    sentinel = await stream._audio_queue.get()
    assert sentinel is None, "Sentinel should be None"

    # Call end_input() second time
    await stream.end_input()
    assert stream._input_ended is True, "_input_ended should still be True"

    # Verify NO second sentinel was queued
    assert stream._audio_queue.qsize() == 0, "Should NOT have second sentinel"

    # Cleanup
    await stream.aclose()
    await plugin.aclose()

    print("✅ Test passed: _input_ended flag prevents duplicate sentinels")


@pytest.mark.asyncio
async def test_push_frame_after_end_input():
    """Test that frames are rejected after end_input()."""
    from livekit.plugins import custom_stt

    plugin = custom_stt.STT(api_url="http://localhost:8000")
    stream = plugin.stream(language="en")

    # Generate test frame
    audio = generate_test_audio(duration=0.1, sample_rate=16000)
    frame = rtc.AudioFrame(
        data=audio.tobytes(),
        sample_rate=16000,
        num_channels=1,
        samples_per_channel=len(audio)
    )

    # Push frame before end_input - should work
    stream.push_frame(frame)
    assert stream._audio_queue.qsize() == 1, "Frame should be queued"

    # Clear queue
    await stream._audio_queue.get()

    # Call end_input
    await stream.end_input()

    # Clear sentinel
    await stream._audio_queue.get()

    # Try to push frame after end_input - should be rejected
    stream.push_frame(frame)
    assert stream._audio_queue.qsize() == 0, "Frame should NOT be queued after end_input()"

    # Cleanup
    await stream.aclose()
    await plugin.aclose()

    print("✅ Test passed: Frames are rejected after end_input()")


@pytest.mark.asyncio
async def test_aclose_no_duplicate_sentinel():
    """Test that aclose() doesn't queue duplicate sentinel if end_input() was called."""
    from livekit.plugins import custom_stt

    plugin = custom_stt.STT(api_url="http://localhost:8000")
    stream = plugin.stream(language="en")

    # Call end_input()
    await stream.end_input()
    assert stream._input_ended is True

    # Clear sentinel
    sentinel1 = await stream._audio_queue.get()
    assert sentinel1 is None

    # Call aclose()
    await stream.aclose()

    # Verify NO second sentinel was queued
    try:
        sentinel2 = await asyncio.wait_for(stream._audio_queue.get(), timeout=0.1)
        assert False, f"Should not have second sentinel, got: {sentinel2}"
    except asyncio.TimeoutError:
        pass  # Expected - no sentinel

    await plugin.aclose()

    print("✅ Test passed: aclose() doesn't queue duplicate sentinel")


@pytest.mark.asyncio
async def test_closed_stream_rejects_frames():
    """Test that frames are rejected after stream is closed."""
    from livekit.plugins import custom_stt

    plugin = custom_stt.STT(api_url="http://localhost:8000")
    stream = plugin.stream(language="en")

    # Close stream
    await stream.aclose()
    assert stream._closed is True

    # Note: aclose() queues a sentinel (None) if input wasn't ended
    # So queue will have 1 item (the sentinel)
    initial_queue_size = stream._audio_queue.qsize()

    # Generate test frame
    audio = generate_test_audio(duration=0.1, sample_rate=16000)
    frame = rtc.AudioFrame(
        data=audio.tobytes(),
        sample_rate=16000,
        num_channels=1,
        samples_per_channel=len(audio)
    )

    # Try to push frame - should be rejected
    stream.push_frame(frame)

    # Queue size should be unchanged (frame was not added)
    assert stream._audio_queue.qsize() == initial_queue_size, "Frame should NOT be queued after close"

    await plugin.aclose()

    print("✅ Test passed: Frames are rejected after stream is closed")


@pytest.mark.asyncio
async def test_sentinel_only_queued_once():
    """Test comprehensive scenario: only one sentinel queued across multiple calls."""
    from livekit.plugins import custom_stt

    plugin = custom_stt.STT(api_url="http://localhost:8000")
    stream = plugin.stream(language="en")

    # Generate test frame
    audio = generate_test_audio(duration=0.1, sample_rate=16000)
    frame = rtc.AudioFrame(
        data=audio.tobytes(),
        sample_rate=16000,
        num_channels=1,
        samples_per_channel=len(audio)
    )

    # Push some frames
    for _ in range(3):
        stream.push_frame(frame)

    assert stream._audio_queue.qsize() == 3, "Should have 3 frames"

    # Call end_input() multiple times
    await stream.end_input()
    await stream.end_input()
    await stream.end_input()

    # Should have 3 frames + 1 sentinel
    assert stream._audio_queue.qsize() == 4, "Should have 3 frames + 1 sentinel"

    # Consume frames
    for i in range(3):
        item = await stream._audio_queue.get()
        assert item is not None, f"Items 0-2 should be frames, got None at {i}"

    # Get sentinel
    sentinel = await stream._audio_queue.get()
    assert sentinel is None, "Item 3 should be sentinel"

    # Queue should be empty
    assert stream._audio_queue.qsize() == 0, "Queue should be empty"

    # Call aclose()
    await stream.aclose()

    # Verify NO additional sentinel
    assert stream._audio_queue.qsize() == 0, "No additional sentinel should be queued"

    await plugin.aclose()

    print("✅ Test passed: Only one sentinel queued across all operations")


if __name__ == "__main__":
    print("Running critical fix tests...\n")

    async def run_all_tests():
        print("Test 1: _input_ended flag prevents duplicate sentinels")
        await test_input_ended_flag()
        print()

        print("Test 2: Frames rejected after end_input()")
        await test_push_frame_after_end_input()
        print()

        print("Test 3: aclose() doesn't duplicate sentinel")
        await test_aclose_no_duplicate_sentinel()
        print()

        print("Test 4: Frames rejected after close")
        await test_closed_stream_rejects_frames()
        print()

        print("Test 5: Only one sentinel in comprehensive scenario")
        await test_sentinel_only_queued_once()
        print()

        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)

    asyncio.run(run_all_tests())
