# Implementation Fix Guide
## Applying Industry Best Practices to Current Code

**Date:** 2025-11-22
**Status:** Action Plan for Critical Bug Fixes
**References:** WEBSOCKET_STT_BEST_PRACTICES.md, CRITICAL_BUGS.md

---

## Overview

This guide provides step-by-step instructions to fix the critical deadlock bug identified in the LiveKit STT plugin by applying industry-standard WebSocket patterns from Deepgram, AssemblyAI, AWS Transcribe, and Azure Speech.

**Critical Finding:** All major STT providers use explicit end-of-stream messages. Our implementation violates this universal pattern.

---

## Fix #1: Add End-of-Stream Message (CRITICAL)

### Current Code (BROKEN)

**File:** `/home/user/skills/stt-livekit-plugin/livekit-plugin-custom-stt/livekit/plugins/custom_stt/stt.py`
**Lines:** 305-321

```python
async def _send_loop(self):
    """Send audio frames to the WebSocket."""
    try:
        while not self._closed:
            frame = await self._audio_queue.get()

            if frame is None:
                # Sentinel received, stop sending
                break  # ❌ BUG: Just exits, server doesn't know we're done!

            if self._ws:
                # Convert frame to bytes and send
                audio_data = frame.data.tobytes()
                await self._ws.send(audio_data)

    except Exception as e:
        logger.error(f"Send loop error: {e}")
```

### Fixed Code (INDUSTRY STANDARD)

```python
async def _send_loop(self):
    """Send audio frames to the WebSocket."""
    try:
        while not self._closed:
            frame = await self._audio_queue.get()

            if frame is None:
                # ✅ FIX: Send end-of-stream message (like Deepgram/AssemblyAI)
                if self._ws and not self._ws.closed:
                    try:
                        end_msg = json.dumps({"type": "end_of_stream"})
                        await self._ws.send(end_msg)
                        logger.info("Sent end-of-stream message to server")
                    except Exception as e:
                        logger.error(f"Failed to send end-of-stream: {e}")
                break

            if self._ws:
                # Convert frame to bytes and send
                audio_data = frame.data.tobytes()
                await self._ws.send(audio_data)

    except Exception as e:
        logger.error(f"Send loop error: {e}")
```

### Pattern Comparison

| Provider | End-of-Stream Message | Our Fix |
|----------|----------------------|---------|
| Deepgram | `{"type": "CloseStream"}` | `{"type": "end_of_stream"}` |
| AssemblyAI | `{"terminate_session": true}` | Similar pattern |
| AWS Transcribe | Empty event stream frame | JSON equivalent |

**Result:** Matches industry standard pattern used by Deepgram and AssemblyAI.

---

## Fix #2: Server-Side Changes Required

The client fix alone is not sufficient. The server must handle the end-of-stream message.

### Current Server Behavior (ASSUMED)

**File:** `/home/user/skills/stt-livekit-plugin/stt-api/` (WebSocket handler)

```python
# Current (problematic) server behavior
async def handle_websocket(websocket):
    async for message in websocket:
        if isinstance(message, bytes):
            # Process audio
            process_audio_chunk(message)
            # Send partial results
            await websocket.send(json.dumps({
                "type": "partial",
                "text": partial_transcription
            }))
        # ❌ No handling of control messages!
```

### Fixed Server Implementation

```python
async def handle_websocket(websocket):
    """Handle WebSocket STT streaming with proper end-of-stream support."""

    # State
    audio_buffer = []
    config = None

    try:
        # 1. Receive configuration
        config_msg = await websocket.recv()
        config = json.loads(config_msg)
        logger.info(f"Received config: {config}")

        # 2. Send ready acknowledgment
        await websocket.send(json.dumps({"type": "ready"}))

        # 3. Main processing loop
        async for message in websocket:
            # Binary frame = audio data
            if isinstance(message, bytes):
                audio_buffer.append(message)

                # Process audio and send partial results
                partial_text = process_audio_chunk(message)
                if partial_text:
                    await websocket.send(json.dumps({
                        "type": "partial",
                        "text": partial_text,
                        "confidence": 0.8
                    }))

            # Text frame = control message
            else:
                data = json.loads(message)
                msg_type = data.get("type")

                # ✅ Handle end-of-stream
                if msg_type == "end_of_stream":
                    logger.info("Received end-of-stream, processing final audio")

                    # Process all remaining buffered audio
                    final_text = process_final_audio(audio_buffer)

                    # Send final transcription
                    await websocket.send(json.dumps({
                        "type": "final",
                        "text": final_text,
                        "confidence": 0.95
                    }))

                    # Send session end confirmation (like AssemblyAI)
                    await websocket.send(json.dumps({
                        "type": "session_ended"
                    }))

                    # Close connection gracefully
                    await websocket.close(code=1000, reason="Normal closure")
                    break

                # ✅ Handle keepalive
                elif msg_type == "keepalive":
                    logger.debug("Received keepalive")
                    # No response needed, just prevents timeout

                else:
                    logger.warning(f"Unknown message type: {msg_type}")

    except websockets.ConnectionClosed:
        logger.info("Client closed connection")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1011, reason="Internal error")
    finally:
        # Cleanup
        audio_buffer.clear()
```

### Key Changes

1. **Distinguish binary vs text frames** - Audio vs control messages
2. **Handle end-of-stream message** - Process final audio, send final results
3. **Send confirmation** - Let client know processing is complete
4. **Graceful close** - Close with code 1000 (normal closure)

---

## Fix #3: Add Keepalive Support (RECOMMENDED)

Following Deepgram's pattern to prevent timeout errors.

### Client: Add Keepalive Task

**Add to `SpeechStream.__init__`:**

```python
def __init__(self, ...):
    super().__init__()
    # ... existing code ...

    # Keepalive task
    self._keepalive_task: Optional[asyncio.Task] = None
```

**Add keepalive loop:**

```python
async def _keepalive_loop(self):
    """Send periodic keepalive messages to prevent timeout."""
    try:
        while not self._closed and self._ws:
            await asyncio.sleep(5.0)  # Every 5 seconds

            if self._ws and not self._ws.closed:
                try:
                    keepalive_msg = json.dumps({"type": "keepalive"})
                    await self._ws.send(keepalive_msg)
                    logger.debug("Sent keepalive")
                except Exception as e:
                    logger.warning(f"Keepalive failed: {e}")
                    break

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Keepalive loop error: {e}")
```

**Start in `_run()` method (around line 290):**

```python
async def _run(self):
    try:
        async with websockets.connect(ws_url) as ws:
            self._ws = ws
            # ... config handshake ...

            # Start tasks
            self._send_task = asyncio.create_task(self._send_loop())
            self._recv_task = asyncio.create_task(self._recv_loop())
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())  # ✅ NEW

            # Wait for tasks
            await asyncio.gather(
                self._send_task,
                self._recv_task,
                self._keepalive_task  # ✅ NEW
            )
    # ... rest of method ...
```

**Cancel in `aclose()` (around line 404):**

```python
async def aclose(self):
    # ... existing code ...

    # Cancel tasks
    for task in [self._main_task, self._send_task, self._recv_task, self._keepalive_task]:  # ✅ ADD keepalive
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    # ... rest of method ...
```

---

## Fix #4: Track Input Ended State (IMPORTANT)

Prevent multiple None sentinels and frames pushed after end_input().

### Add State Flag

**In `__init__` (around line 240):**

```python
def __init__(self, ...):
    super().__init__()
    # ... existing code ...

    # State
    self._closed = False
    self._input_ended = False  # ✅ NEW
    self._main_task: Optional[asyncio.Task] = None
```

### Update end_input()

**Current (lines 383-385):**

```python
async def end_input(self):
    """Signal that no more audio will be sent."""
    await self._audio_queue.put(None)
```

**Fixed:**

```python
async def end_input(self):
    """Signal that no more audio will be sent."""
    if self._input_ended:
        logger.warning("end_input() already called, ignoring")
        return

    self._input_ended = True
    await self._audio_queue.put(None)
    logger.info("Input ended, queued sentinel")
```

### Update push_frame()

**Current (lines 362-376):**

```python
def push_frame(self, frame: rtc.AudioFrame):
    """Push an audio frame for transcription."""
    if self._closed:
        return

    try:
        self._audio_queue.put_nowait(frame)
    except asyncio.QueueFull:
        logger.warning("Audio queue is full, dropping frame")
```

**Fixed:**

```python
def push_frame(self, frame: rtc.AudioFrame):
    """Push an audio frame for transcription."""
    if self._closed:
        logger.warning("Cannot push frame: stream closed")
        return

    if self._input_ended:  # ✅ NEW CHECK
        logger.warning("Cannot push frame: input already ended")
        return

    try:
        self._audio_queue.put_nowait(frame)
    except asyncio.QueueFull:
        logger.warning("Audio queue is full, dropping frame")
```

### Update aclose()

**Current (around line 395):**

```python
async def aclose(self):
    if self._closed:
        return

    self._closed = True

    # Signal tasks to stop
    await self._audio_queue.put(None)  # ❌ May be duplicate

    # ... rest of method ...
```

**Fixed:**

```python
async def aclose(self):
    if self._closed:
        return

    self._closed = True

    # Signal tasks to stop (only if not already done)
    if not self._input_ended:  # ✅ CHECK FIRST
        await self._audio_queue.put(None)

    # ... rest of method ...
```

---

## Fix #5: Improve _recv_loop() Error Handling

Handle session_ended message from server.

### Updated _recv_loop()

**Current (lines 323-360):**

```python
async def _recv_loop(self):
    """Receive transcription events from the WebSocket."""
    try:
        while not self._closed and self._ws:
            message = await self._ws.recv()

            # Parse JSON response
            data = json.loads(message)
            event_type = data.get("type")

            if event_type == "final":
                # ... process final ...
            elif event_type == "error":
                logger.error(f"STT error: {data.get('message')}")
                break

    except Exception as e:
        logger.error(f"Receive loop error: {e}")

    finally:
        await self._event_queue.put(None)
```

**Fixed:**

```python
async def _recv_loop(self):
    """Receive transcription events from the WebSocket."""
    try:
        while not self._closed and self._ws:
            message = await self._ws.recv()

            # Parse JSON response
            data = json.loads(message)
            event_type = data.get("type")

            if event_type == "final":
                # Final transcription result
                text = data.get("text", "")
                confidence = data.get("confidence", 0.0)

                if text:
                    event = stt.SpeechEvent(
                        type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                        alternatives=[
                            stt.SpeechData(
                                text=text,
                                language=self._language or "",
                                confidence=confidence,
                            )
                        ],
                    )
                    await self._event_queue.put(event)

            elif event_type == "partial":  # ✅ NEW: Handle partial results
                text = data.get("text", "")
                if text:
                    event = stt.SpeechEvent(
                        type=stt.SpeechEventType.INTERIM_TRANSCRIPT,
                        alternatives=[
                            stt.SpeechData(
                                text=text,
                                language=self._language or "",
                                confidence=data.get("confidence", 0.0),
                            )
                        ],
                    )
                    await self._event_queue.put(event)

            elif event_type == "session_ended":  # ✅ NEW: Handle graceful end
                logger.info("Server ended session gracefully")
                break

            elif event_type == "error":
                error_msg = data.get("message", "Unknown error")
                logger.error(f"STT error: {error_msg}")
                break

            else:
                logger.warning(f"Unknown message type: {event_type}")

    except websockets.ConnectionClosed as e:
        logger.info(f"Connection closed: code={e.code}, reason={e.reason}")
    except Exception as e:
        logger.error(f"Receive loop error: {e}")

    finally:
        # Signal completion
        await self._event_queue.put(None)
```

---

## Fix #6: Update STTCapabilities (OPTIONAL)

If server now supports interim results:

**Current (lines 64-67):**

```python
super().__init__(
    capabilities=stt.STTCapabilities(
        streaming=True,
        interim_results=False,  # Whisper provides final results
    )
)
```

**If server supports partial transcripts:**

```python
super().__init__(
    capabilities=stt.STTCapabilities(
        streaming=True,
        interim_results=True,  # ✅ Now supported
    )
)
```

---

## Implementation Checklist

### Client-Side Changes (`stt.py`)

- [ ] ✅ Fix #1: Add end-of-stream message in `_send_loop()`
- [ ] ✅ Fix #3: Add `_keepalive_loop()` method
- [ ] ✅ Fix #3: Start keepalive task in `_run()`
- [ ] ✅ Fix #3: Cancel keepalive task in `aclose()`
- [ ] ✅ Fix #4: Add `_input_ended` flag to `__init__`
- [ ] ✅ Fix #4: Update `end_input()` to set flag
- [ ] ✅ Fix #4: Update `push_frame()` to check flag
- [ ] ✅ Fix #4: Update `aclose()` to check flag
- [ ] ✅ Fix #5: Improve `_recv_loop()` error handling
- [ ] ✅ Fix #5: Handle `session_ended` message
- [ ] ✅ Fix #5: Handle `partial` message (if supported)
- [ ] 🟡 Fix #6: Update capabilities if interim results supported

### Server-Side Changes

- [ ] ✅ Fix #2: Handle binary vs text frames separately
- [ ] ✅ Fix #2: Handle `end_of_stream` control message
- [ ] ✅ Fix #2: Process final audio on end-of-stream
- [ ] ✅ Fix #2: Send `session_ended` confirmation
- [ ] ✅ Fix #2: Close connection with code 1000
- [ ] 🟡 Fix #3: Handle `keepalive` messages (optional)
- [ ] 🟡 Support partial transcripts (optional)

### Testing

- [ ] Test normal flow: push frames → end_input() → receive final
- [ ] Test no deadlock after end_input()
- [ ] Test keepalive prevents timeout
- [ ] Test multiple end_input() calls (idempotent)
- [ ] Test push_frame() after end_input() (rejected)
- [ ] Test graceful aclose()
- [ ] Test error handling
- [ ] Test reconnection scenario

---

## Testing the Fixes

### Test 1: Verify End-of-Stream Flow

```python
@pytest.mark.asyncio
async def test_end_of_stream_signaling():
    """Verify end-of-stream message is sent and handled."""
    stt_instance = STT(api_url="http://localhost:8000")
    stream = stt_instance.stream()

    # Push audio
    for i in range(5):
        frame = create_test_frame()
        stream.push_frame(frame)

    # Signal end
    await stream.end_input()

    # Receive results (should NOT hang!)
    results = []
    async for event in stream:
        results.append(event)

    # Should receive final transcript
    assert len(results) > 0
    assert any(e.type == stt.SpeechEventType.FINAL_TRANSCRIPT for e in results)

    # Cleanup
    await stream.aclose()
```

### Test 2: Verify No Deadlock

```python
@pytest.mark.asyncio
async def test_no_deadlock_on_end_input():
    """Ensure end_input() doesn't cause deadlock."""
    stt_instance = STT(api_url="http://localhost:8000")
    stream = stt_instance.stream()

    stream.push_frame(create_test_frame())

    # This should complete within reasonable time
    await asyncio.wait_for(stream.end_input(), timeout=5.0)

    # Receive results with timeout
    try:
        async with asyncio.timeout(10.0):
            async for event in stream:
                print(f"Received: {event}")
    except asyncio.TimeoutError:
        pytest.fail("Deadlock detected - timed out waiting for results")

    await stream.aclose()
```

### Test 3: Verify Keepalive

```python
@pytest.mark.asyncio
async def test_keepalive_prevents_timeout(mock_server):
    """Test keepalive messages are sent periodically."""
    stt_instance = STT(api_url="ws://localhost:8000")
    stream = stt_instance.stream()

    # Wait longer than timeout period
    await asyncio.sleep(12.0)

    # Verify keepalive messages sent
    keepalives = mock_server.get_messages_by_type("keepalive")
    assert len(keepalives) >= 2  # Should have sent 2+ in 12 seconds

    await stream.aclose()
```

---

## Rollout Plan

### Phase 1: Server Updates (1-2 hours)
1. Update server WebSocket handler to distinguish binary/text frames
2. Add end-of-stream message handling
3. Add session_ended response
4. Test server independently

### Phase 2: Client Updates (2-3 hours)
1. Apply Fix #1 (end-of-stream message)
2. Apply Fix #4 (input ended tracking)
3. Apply Fix #5 (recv_loop improvements)
4. Test integration

### Phase 3: Enhancements (1-2 hours)
1. Apply Fix #3 (keepalive)
2. Add partial transcript support (optional)
3. Comprehensive testing

### Phase 4: Validation (1 hour)
1. Run all existing tests
2. Run new tests
3. Manual testing
4. Update documentation

**Total Estimated Time:** 5-8 hours

---

## Expected Outcomes

### Before Fixes

```
User code:
await stream.end_input()
async for event in stream:  # ❌ HANGS FOREVER
    print(event)
```

**Result:** Deadlock - client and server both waiting

### After Fixes

```
User code:
await stream.end_input()
async for event in stream:  # ✅ Works correctly
    print(event)
```

**Result:**
1. Client sends `{"type": "end_of_stream"}`
2. Server processes remaining audio
3. Server sends final transcript
4. Server sends `{"type": "session_ended"}`
5. Server closes connection
6. Client receives events and exits loop cleanly

---

## Verification

After implementing all fixes, verify:

```bash
# Run tests
cd /home/user/skills/stt-livekit-plugin
pytest tests/ -v

# Should see:
# ✅ test_streaming_transcription - PASSED
# ✅ test_end_of_stream_signaling - PASSED
# ✅ test_no_deadlock - PASSED
# ✅ test_keepalive - PASSED
# ✅ test_graceful_shutdown - PASSED
```

---

## References

- **Industry Standards:** `/home/user/skills/stt-livekit-plugin/WEBSOCKET_STT_BEST_PRACTICES.md`
- **Critical Bugs:** `/home/user/skills/stt-livekit-plugin/CRITICAL_BUGS.md`
- **Current Implementation:** `/home/user/skills/stt-livekit-plugin/livekit-plugin-custom-stt/livekit/plugins/custom_stt/stt.py`

---

**Status:** Ready for Implementation
**Priority:** CRITICAL (fixes production-blocking deadlock)
**Estimated Effort:** 5-8 hours
**Risk:** Low (aligned with industry standards, well-tested pattern)
