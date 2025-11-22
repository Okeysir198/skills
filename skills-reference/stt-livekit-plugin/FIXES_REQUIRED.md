# Critical Fixes Required

## Fix #1: Resolve Deadlock in end_input() Flow

### Client-Side Fix (stt.py)

**File**: `livekit-plugin-custom-stt/livekit/plugins/custom_stt/stt.py`

**Lines to modify**: 211-241 (SpeechStream.__init__) and 305-322 (_send_loop)

```python
class SpeechStream(stt.SpeechStream):
    def __init__(self, ...):
        super().__init__()
        # ... existing code ...

        # ADD: Track if input has ended
        self._input_ended = False

    async def _send_loop(self):
        """Send audio frames to the WebSocket."""
        try:
            while not self._closed:
                frame = await self._audio_queue.get()

                if frame is None:
                    # FIX: Notify server that we're done sending audio
                    if self._ws and not self._ws.closed:
                        try:
                            await self._ws.send(json.dumps({"type": "end_of_stream"}))
                            logger.info("Sent end_of_stream message to server")
                        except Exception as e:
                            logger.error(f"Failed to send end_of_stream: {e}")
                    break

                if self._ws:
                    audio_data = frame.data.tobytes()
                    await self._ws.send(audio_data)

        except Exception as e:
            logger.error(f"Send loop error: {e}")
```

**Lines to modify**: 362-376 (push_frame) and 383-385 (end_input)

```python
    def push_frame(self, frame: rtc.AudioFrame):
        """Push an audio frame for transcription."""
        if self._closed:
            return

        # FIX: Don't accept frames after end_input()
        if self._input_ended:
            logger.warning("Cannot push frame after end_input() called")
            return

        try:
            self._audio_queue.put_nowait(frame)
        except asyncio.QueueFull:
            logger.warning("Audio queue is full, dropping frame")

    async def end_input(self):
        """Signal that no more audio will be sent."""
        # FIX: Only send sentinel once
        if not self._input_ended:
            self._input_ended = True
            await self._audio_queue.put(None)
```

**Lines to modify**: 387-411 (aclose)

```python
    async def aclose(self):
        """Close the stream and clean up resources."""
        if self._closed:
            return

        self._closed = True

        # FIX: Only send sentinel if not already ended
        if not self._input_ended:
            self._input_ended = True
            await self._audio_queue.put(None)

        # Cancel tasks
        if self._main_task and not self._main_task.done():
            self._main_task.cancel()
            try:
                await self._main_task
            except asyncio.CancelledError:
                pass
        if self._send_task and not self._send_task.done():
            self._send_task.cancel()
            try:
                await self._send_task
            except asyncio.CancelledError:
                pass
        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
```

### Server-Side Fix (main.py)

**File**: `stt-api/main.py`

**Lines to modify**: 186-242 (websocket_transcribe function)

```python
@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """WebSocket endpoint for real-time streaming transcription."""
    await websocket.accept()
    logger.info("WebSocket client connected")

    if model is None:
        await websocket.send_json({"type": "error", "message": "Model not loaded"})
        await websocket.close()
        return

    try:
        # Receive configuration
        config_msg = await websocket.receive_text()
        config = json.loads(config_msg)

        language = config.get("language", None)
        sample_rate = config.get("sample_rate", 16000)
        task = config.get("task", "transcribe")

        logger.info(f"WebSocket config: language={language}, sample_rate={sample_rate}, task={task}")

        # Send acknowledgment
        await websocket.send_json({
            "type": "ready",
            "message": "Ready to receive audio"
        })

        # Buffer for accumulating audio
        audio_buffer = bytearray()
        chunk_duration = 2.0
        bytes_per_chunk = int(sample_rate * chunk_duration * 2)

        # FIX: Track if client signaled end of stream
        end_of_stream = False

        while True:
            try:
                # FIX: Try to receive either text or binary
                message = await websocket.receive()

                # Check if it's a text message (control message)
                if "text" in message:
                    try:
                        control_msg = json.loads(message["text"])
                        if control_msg.get("type") == "end_of_stream":
                            logger.info("Received end_of_stream from client")
                            end_of_stream = True
                            # Process any remaining audio
                            if len(audio_buffer) > 0:
                                # Process remaining buffer
                                audio_np = np.frombuffer(bytes(audio_buffer), dtype=np.int16)
                                audio_float = audio_np.astype(np.float32) / 32768.0

                                import tempfile
                                import soundfile as sf

                                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                                    sf.write(tmp_file.name, audio_float, sample_rate)
                                    tmp_path = tmp_file.name

                                try:
                                    segments, info = model.transcribe(
                                        tmp_path,
                                        language=language,
                                        task=task,
                                        beam_size=3,
                                        vad_filter=True,
                                    )

                                    for segment in segments:
                                        await websocket.send_json({
                                            "type": "final",
                                            "text": segment.text.strip(),
                                            "start": segment.start,
                                            "end": segment.end,
                                            "confidence": segment.avg_logprob,
                                        })

                                finally:
                                    os.unlink(tmp_path)

                            # FIX: Close connection gracefully
                            logger.info("Closing WebSocket after end_of_stream")
                            break
                    except json.JSONDecodeError:
                        logger.warning("Received invalid JSON control message")
                        continue

                # It's binary audio data
                elif "bytes" in message:
                    data = message["bytes"]
                    audio_buffer.extend(data)

                    # Process when we have enough audio
                    if len(audio_buffer) >= bytes_per_chunk:
                        audio_np = np.frombuffer(bytes(audio_buffer[:bytes_per_chunk]), dtype=np.int16)
                        audio_float = audio_np.astype(np.float32) / 32768.0

                        import tempfile
                        import soundfile as sf

                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                            sf.write(tmp_file.name, audio_float, sample_rate)
                            tmp_path = tmp_file.name

                        try:
                            segments, info = model.transcribe(
                                tmp_path,
                                language=language,
                                task=task,
                                beam_size=3,
                                vad_filter=True,
                            )

                            for segment in segments:
                                await websocket.send_json({
                                    "type": "final",
                                    "text": segment.text.strip(),
                                    "start": segment.start,
                                    "end": segment.end,
                                    "confidence": segment.avg_logprob,
                                })

                        finally:
                            os.unlink(tmp_path)

                        overlap_bytes = int(sample_rate * 0.5 * 2)
                        audio_buffer = audio_buffer[bytes_per_chunk - overlap_bytes:]

            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
                break
            except Exception as e:
                logger.error(f"WebSocket processing error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })

    except Exception as e:
        logger.error(f"WebSocket error: {e}")

    finally:
        try:
            await websocket.close()
        except:
            pass
```

---

## Testing the Fixes

### Test Case 1: end_input() no longer deadlocks

```python
async def test_end_input_no_deadlock():
    plugin = custom_stt.STT(api_url="http://localhost:8000")
    stream = plugin.stream(language="en")

    # Start receiving
    events = []
    async def receive():
        async for event in stream:
            events.append(event)
            print(f"Event: {event.alternatives[0].text}")

    recv_task = asyncio.create_task(receive())

    # Give stream time to connect
    await asyncio.sleep(0.5)

    # Push some frames
    for i in range(10):
        audio = generate_test_audio(duration=0.2)
        frame = rtc.AudioFrame(
            data=audio.tobytes(),
            sample_rate=16000,
            num_channels=1,
            samples_per_channel=len(audio)
        )
        stream.push_frame(frame)
        await asyncio.sleep(0.1)

    # Signal end
    await stream.end_input()

    # THIS SHOULD NOT HANG - should complete within reasonable time
    try:
        await asyncio.wait_for(recv_task, timeout=5.0)
        print("✅ No deadlock - completed successfully")
    except asyncio.TimeoutError:
        print("❌ DEADLOCK - timed out")
        await stream.aclose()
        raise AssertionError("end_input() caused deadlock")

    # Clean up
    await stream.aclose()
    await plugin.aclose()

    assert len(events) > 0, "Should have received events"
```

### Test Case 2: Multiple end_input() calls

```python
async def test_multiple_end_input():
    plugin = custom_stt.STT(api_url="http://localhost:8000")
    stream = plugin.stream(language="en")

    # Call end_input() twice
    await stream.end_input()
    await stream.end_input()  # Should not queue second None

    # Verify only one None in queue
    frame1 = await asyncio.wait_for(stream._audio_queue.get(), timeout=0.1)
    assert frame1 is None

    # Queue should be empty now
    try:
        frame2 = await asyncio.wait_for(stream._audio_queue.get(), timeout=0.1)
        raise AssertionError("Should not have second None")
    except asyncio.TimeoutError:
        pass  # Expected

    await stream.aclose()
    await plugin.aclose()
```

### Test Case 3: Frames after end_input() are rejected

```python
async def test_frames_after_end_input():
    plugin = custom_stt.STT(api_url="http://localhost:8000")
    stream = plugin.stream(language="en")

    # End input
    await stream.end_input()

    # Try to push frame - should be rejected
    audio = generate_test_audio(duration=0.1)
    frame = rtc.AudioFrame(
        data=audio.tobytes(),
        sample_rate=16000,
        num_channels=1,
        samples_per_channel=len(audio)
    )

    # Should log warning but not crash
    stream.push_frame(frame)

    # Verify frame was not queued
    try:
        queued_frame = await asyncio.wait_for(stream._audio_queue.get(), timeout=0.1)
        if queued_frame is not None:
            raise AssertionError("Frame should not have been queued")
    except asyncio.TimeoutError:
        pass  # Expected - queue has only None

    await stream.aclose()
    await plugin.aclose()
```

---

## Implementation Priority

### Critical (Must Fix)
1. ✅ Fix #1: Add end-of-stream message (client + server)
2. ✅ Test: Verify no deadlock

### High Priority (Should Fix)
3. ✅ Fix #2: Track `_input_ended` flag
4. ✅ Fix #3: Reject frames after `end_input()`
5. ✅ Update tests to verify fixes

### Medium Priority (Nice to Have)
6. ⚠️ Fix #5: Remove unnecessary None in `aclose()`
7. ⚠️ Await cancelled tasks properly

### Low Priority (Polish)
8. ℹ️ Move imports to top of file
9. ℹ️ Add type hints
10. ℹ️ Add docstring examples

---

## Estimated Time

- Implementing fixes: **1-2 hours**
- Testing fixes: **1 hour**
- Documentation updates: **30 minutes**

**Total**: **2.5-3.5 hours**

---

## Verification Checklist

After implementing fixes, verify:

- [ ] `end_input()` completes without hanging
- [ ] Server closes connection after `end_of_stream`
- [ ] Multiple `end_input()` calls don't queue multiple sentinels
- [ ] Frames pushed after `end_input()` are rejected with warning
- [ ] All existing tests still pass
- [ ] New tests for fixes pass
- [ ] Documentation updated
- [ ] Examples updated

---

**Status**: ⏳ **Fixes Pending**
**Timeline**: ~3 hours to production ready
**Blocker**: Critical deadlock must be fixed before production use
