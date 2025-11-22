# WebSocket-Based Streaming STT Best Practices
## Industry Standards from Major Providers

**Research Date:** 2025-11-22
**Sources:** Deepgram, AWS Transcribe, Azure Speech, AssemblyAI, Google Cloud Speech

---

## Executive Summary

This document compiles industry-standard best practices for WebSocket-based streaming speech-to-text (STT) implementations based on comprehensive analysis of production services from Deepgram, AWS Transcribe, Azure Speech Service, AssemblyAI, and related implementations.

**Key Finding:** The critical issue identified in `/home/user/skills/stt-livekit-plugin/CRITICAL_BUGS.md` (deadlock in `end_input()` flow) is a violation of the universal pattern used by all major STT providers.

**Universal Pattern:** All production STT services use an explicit end-of-stream message to signal completion, not just closing the send loop.

---

## 1. End-of-Stream Signaling Patterns

### Industry Standard Approaches

All major providers use **explicit signaling** rather than implicit connection closure:

#### Deepgram: CloseStream Message
```json
{"type": "CloseStream"}
```

**Behavior:**
- Send as text WebSocket frame (NOT binary)
- Server processes all cached audio
- Server sends final transcription results
- Server sends metadata summary
- Server closes WebSocket connection

**Critical Rule:** Do NOT send empty bytes (`b''` in Python, `Uint8Array(0)` in JavaScript) - this is deprecated and causes errors.

**Source:** Deepgram WebSocket API Documentation

#### AssemblyAI: terminate_session Message
```json
{"terminate_session": true}
```

**Additional Control:**
```json
{"force_end_utterance": true}
```

**Behavior:**
- Client sends terminate_session when done
- Server processes remaining audio
- Server sends final transcripts
- Server sends SessionTerminated message
- Connection closes gracefully

**Source:** AssemblyAI Universal-Streaming API Documentation

#### AWS Transcribe: Empty Event Stream Frame
```
Event stream encoded message with:
- Headers: :message-type=event, :event-type=AudioEvent
- Body: Empty (no audio bytes)
```

**Behavior:**
- Send signed empty frame in event stream encoding
- Server recognizes end of audio
- Server sends final results (isPartial=false)
- Wait 2-3 seconds past last detected audio before sending

**Source:** AWS Transcribe Streaming API Documentation

#### Azure Speech Service: Audio Message with Empty Payload
**Binary frame format:**
- First 2 bytes: Header size (big-endian)
- Headers: path=audio, x-requestid, x-timestamp
- Body: Empty

**Note:** Azure primarily uses proprietary protocol; WebSocket access is through SDK

**Source:** Azure Speech SDK WebSocket Protocol

### Pattern Comparison

| Provider | Message Type | Format | Critical Detail |
|----------|-------------|--------|-----------------|
| Deepgram | JSON text | `{"type": "CloseStream"}` | Send as TEXT frame, not binary |
| AssemblyAI | JSON text | `{"terminate_session": true}` | Wait for SessionTerminated response |
| AWS Transcribe | Binary | Event stream encoding, empty body | Must be signed like audio frames |
| Azure Speech | Binary | Headers + empty body | Proprietary event stream format |

**Universal Truth:** No production service relies on WebSocket close alone for end-of-stream signaling.

---

## 2. WebSocket Lifecycle: The Complete Flow

### Standard Lifecycle Pattern

Based on all providers, the universal flow is:

```
1. Client: Connect WebSocket
2. Client → Server: Configuration message (JSON)
3. Server → Client: Ready/Acknowledgment message
4. Client → Server: Binary audio frames (streaming)
5. Server → Client: Partial transcription results (ongoing)
6. Client → Server: End-of-stream message (JSON) ⚠️ CRITICAL
7. Server: Process remaining buffered audio
8. Server → Client: Final transcription results
9. Server → Client: Summary/metadata (optional)
10. Server: Close WebSocket (or Client closes after receiving final)
11. Connection cleanup
```

### Critical Phases

#### Phase 1: Handshake & Configuration
```python
# Connect
ws = await websockets.connect(ws_url)

# Send config (JSON text frame)
config = {
    "language": "en",
    "sample_rate": 16000,
    "encoding": "pcm_s16le"
}
await ws.send(json.dumps(config))

# Wait for ready
ready_msg = await ws.recv()
assert json.loads(ready_msg)["type"] == "ready"
```

#### Phase 2: Streaming Audio
```python
# Send audio as BINARY frames
while audio_available:
    audio_chunk = get_audio_chunk()  # bytes
    await ws.send(audio_chunk)  # Binary WebSocket frame

    # Optionally receive partial results concurrently
```

#### Phase 3: End-of-Stream Signaling ⚠️
```python
# CRITICAL: Send end-of-stream message as TEXT frame
end_msg = {"type": "end_of_stream"}  # or provider-specific format
await ws.send(json.dumps(end_msg))

# DO NOT just break/return - server needs to know!
```

#### Phase 4: Receiving Final Results
```python
# Continue receiving until final results
while True:
    msg = await ws.recv()
    data = json.loads(msg)

    if data["type"] == "final":
        process_final_transcript(data)
    elif data["type"] == "session_terminated":
        break  # Clean termination
```

#### Phase 5: Connection Cleanup
```python
# Close WebSocket
await ws.close(code=1000)  # Normal closure
```

---

## 3. Binary Audio + JSON Control Messages

### The Universal Pattern: Frame Type Separation

**All providers use the same approach:**
- **Binary WebSocket frames** for audio data
- **Text WebSocket frames** for control messages and transcription results

### WebSocket Frame Types (RFC 6455)

WebSocket protocol defines distinct frame types:
- **Text frames (opcode 0x1):** UTF-8 encoded text
- **Binary frames (opcode 0x2):** Raw binary data

### Implementation Pattern

```python
# Sending audio (binary)
audio_bytes = frame.data.tobytes()
await websocket.send(audio_bytes)  # Sent as binary frame

# Sending control (text)
control_msg = json.dumps({"type": "KeepAlive"})
await websocket.send(control_msg)  # Sent as text frame

# Receiving (auto-detected by library)
message = await websocket.recv()
if isinstance(message, bytes):
    # Binary frame received (unusual for STT, mostly send-only)
    pass
elif isinstance(message, str):
    # Text frame (JSON response)
    data = json.loads(message)
    process_response(data)
```

### Common Mistakes

**❌ Wrong: Sending JSON as binary**
```python
msg = json.dumps({"type": "CloseStream"}).encode()
await ws.send(msg)  # May be interpreted as audio!
```

**✅ Correct: Explicit text frame**
```python
msg = json.dumps({"type": "CloseStream"})
await ws.send(msg)  # String = text frame
```

### Provider-Specific Details

#### Deepgram
- Audio: Binary frames (raw PCM, opus, etc.)
- Control: Text frames (KeepAlive, CloseStream)
- **Critical:** KeepAlive MUST be text frame, not binary
- Responses: Text frames (JSON transcription results)

#### AssemblyAI
- Audio: Binary frames (PCM recommended: pcm_s16le)
- Control: Text frames (terminate_session, force_end_utterance)
- Responses: Text frames (JSON with type: transcript, SessionTerminated, etc.)

#### AWS Transcribe
- Audio: Binary frames (event stream encoding)
- **Unique:** Audio messages are binary-encoded JSON envelopes
- All messages use event stream encoding
- Headers distinguish message types

#### Azure Speech
- Audio: Binary frames with custom header format
- Control: Binary frames with specific header paths
- **Unique:** All messages are binary with internal structure

### Buffer Size Best Practices

| Provider | Recommended Chunk Size | Notes |
|----------|----------------------|-------|
| Deepgram | 20-250ms of audio | Optimal for real-time |
| AssemblyAI | 16-48KB | Real-time streaming |
| AWS Transcribe | No strict limit | Max 96200 bytes for 48kHz |
| Azure Speech | Varies by codec | SDK handles chunking |

**General Rule:** Chunk sizes between 20-100ms of audio (320-1600 bytes for 16kHz PCM)

---

## 4. Graceful Shutdown Patterns

### WebSocket Close Codes

Standard close codes for normal operation:

```python
# Normal closure - task complete
await ws.close(code=1000, reason="Normal closure")

# Going away - client shutting down
await ws.close(code=1001, reason="Client disconnecting")
```

**Source:** RFC 6455, websockets library documentation

### Provider-Specific Patterns

#### Deepgram: CloseStream + Wait + Close

```python
# 1. Send CloseStream message
await ws.send(json.dumps({"type": "CloseStream"}))

# 2. Wait for final transcripts + metadata
while True:
    msg = await ws.recv()
    data = json.loads(msg)
    if data.get("type") == "Metadata":
        # Final metadata received
        break
    elif data.get("is_final"):
        process_transcript(data)

# 3. Server closes connection automatically
# Or client can close
await ws.close(code=1000)
```

**Benefits:**
- Ensures all audio is processed
- Receives all transcripts
- No charged for unprocessed audio
- Clean server-side cleanup

#### AssemblyAI: Terminate + Wait + Close

```python
# 1. Send terminate message
await ws.send(json.dumps({"terminate_session": true}))

# 2. Wait for SessionTerminated
while True:
    msg = await ws.recv()
    data = json.loads(msg)
    if data.get("message_type") == "SessionTerminated":
        break
    elif data.get("message_type") == "FinalTranscript":
        process_transcript(data)

# 3. Close WebSocket
await ws.close(code=1000)
```

**Try-Finally Pattern:**
```python
try:
    # Streaming logic
    pass
finally:
    await stream.disconnect()  # Graceful shutdown
```

#### AWS Transcribe: Empty Frame + Wait + Close

```python
# 1. Send empty audio event
empty_event = AudioEvent()  # No payload
await send_event_stream(empty_event)

# 2. Wait for final results
async for event in response_stream:
    if event.transcript.results:
        result = event.transcript.results[0]
        if not result.is_partial:
            # Final result
            process_final(result)

# 3. Stream automatically closes
```

### Error During Shutdown

```python
async def graceful_shutdown(ws, send_end_message=True):
    """Best practice shutdown pattern."""
    try:
        if send_end_message and ws.open:
            # Send end-of-stream
            await asyncio.wait_for(
                ws.send(json.dumps({"type": "end_stream"})),
                timeout=5.0
            )

            # Wait for final responses (with timeout)
            try:
                while True:
                    msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    data = json.loads(msg)
                    if is_final_message(data):
                        break
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for final results")

    except Exception as e:
        logger.error(f"Error during graceful shutdown: {e}")
    finally:
        # Always close WebSocket
        if not ws.closed:
            await ws.close(code=1000)
```

---

## 5. Error Recovery & Partial Data Handling

### Connection Error Types

#### Network Errors
```python
try:
    async with websockets.connect(url) as ws:
        # streaming
        pass
except websockets.exceptions.ConnectionClosed as e:
    logger.error(f"Connection closed: code={e.code}, reason={e.reason}")
    # Reconnect logic
except OSError as e:
    logger.error(f"Network error: {e}")
    # Retry after delay
```

#### Timeout Errors

**Deepgram NET-0001:** No audio received within 10 seconds

**Prevention:**
```python
import asyncio

# Keep-alive loop
async def keepalive_loop(ws):
    while ws.open:
        await asyncio.sleep(5.0)  # Every 5 seconds
        try:
            await ws.send(json.dumps({"type": "KeepAlive"}))
        except Exception:
            break

# Must also send at least one audio message
```

**AssemblyAI Code 3005:** Session expired

**Causes:**
- Exceeded maximum session duration
- Sending audio faster than real-time
- No activity timeout

### Retry Strategy

#### Exponential Backoff Pattern

```python
async def connect_with_retry(url, max_retries=5):
    """Industry standard retry pattern."""
    base_delay = 1.0

    for attempt in range(max_retries):
        try:
            ws = await websockets.connect(url)
            return ws
        except Exception as e:
            if attempt == max_retries - 1:
                raise

            delay = base_delay * (2 ** attempt)  # Exponential
            jitter = random.uniform(0, 0.1 * delay)  # Jitter
            total_delay = min(delay + jitter, 60.0)  # Cap at 60s

            logger.warning(f"Connection failed (attempt {attempt+1}), "
                         f"retrying in {total_delay:.2f}s: {e}")
            await asyncio.sleep(total_delay)
```

**AWS Transcribe:**
```python
# SDK built-in retry
client = TranscribeStreamingClient(
    config=Config(
        retries={
            'max_attempts': 5,
            'mode': 'adaptive'
        }
    )
)
```

### Partial Data Handling

#### Buffering Strategy

```python
class AudioBuffer:
    """Buffer audio chunks for retry."""

    def __init__(self, max_duration_seconds=10):
        self.buffer = deque()
        self.max_duration = max_duration_seconds

    def add_chunk(self, audio_chunk, duration_ms):
        """Add chunk with timestamp."""
        self.buffer.append((audio_chunk, duration_ms, time.time()))

        # Trim old chunks
        total_duration = sum(d for _, d, _ in self.buffer)
        while total_duration > self.max_duration * 1000:
            self.buffer.popleft()
            total_duration = sum(d for _, d, _ in self.buffer)

    def get_buffered_audio(self):
        """Get all buffered audio for retry."""
        return [chunk for chunk, _, _ in self.buffer]
```

#### Reconnection with Buffer Replay

```python
async def streaming_with_recovery(url, audio_source):
    """Robust streaming with automatic recovery."""
    buffer = AudioBuffer(max_duration_seconds=10)

    while True:
        try:
            async with websockets.connect(url) as ws:
                # Send config
                await ws.send(json.dumps(config))

                # Replay buffered audio
                for chunk in buffer.get_buffered_audio():
                    await ws.send(chunk)

                # Continue streaming
                async for audio_chunk in audio_source:
                    buffer.add_chunk(audio_chunk, chunk_duration_ms)
                    await ws.send(audio_chunk)

        except websockets.ConnectionClosed as e:
            if e.code == 1000:  # Normal closure
                break
            logger.warning(f"Connection lost (code {e.code}), reconnecting...")
            await asyncio.sleep(1.0)
            # Loop continues, reconnects with buffer replay
```

#### Partial Transcript Handling

All providers send partial results during streaming:

```python
async def handle_transcripts(ws):
    """Handle both partial and final transcripts."""
    current_segment = ""

    async for message in ws:
        data = json.loads(message)

        # Deepgram
        if data.get("is_final"):
            final_text = data["channel"]["alternatives"][0]["transcript"]
            yield {"type": "final", "text": final_text}
            current_segment = ""
        else:
            partial_text = data["channel"]["alternatives"][0]["transcript"]
            current_segment = partial_text
            yield {"type": "partial", "text": partial_text}

        # AssemblyAI
        msg_type = data.get("message_type")
        if msg_type == "FinalTranscript":
            yield {"type": "final", "text": data["text"]}
        elif msg_type == "PartialTranscript":
            yield {"type": "partial", "text": data["text"]}

        # AWS Transcribe
        for result in data.get("transcript", {}).get("results", []):
            result_type = "final" if not result["is_partial"] else "partial"
            text = result["alternatives"][0]["transcript"]
            yield {"type": result_type, "text": text}
```

### Error Code Reference

#### Deepgram
- `1011`: Internal error / timeout (NET-0001)
- `1008`: Policy violation
- `1003`: Unsupported data

#### AssemblyAI
- `1008`: Not authorized (invalid API key, insufficient balance)
- `3005`: Session expired (max duration, too fast playback)
- `4000`: Bad request
- `4031`: Insufficient balance
- `4032`: Concurrency limit exceeded

#### AWS Transcribe
- `InternalFailureException`: Retry recommended
- `LimitExceededException`: Reduce concurrent streams
- `BadRequestException`: Check audio format

---

## 6. Application to Current Implementation

### Critical Issues in `/home/user/skills/stt-livekit-plugin`

Based on `/home/user/skills/stt-livekit-plugin/CRITICAL_BUGS.md`:

#### Issue #1: Missing End-of-Stream Message (CRITICAL)

**Current Code (lines 305-321):**
```python
async def _send_loop(self):
    while not self._closed:
        frame = await self._audio_queue.get()
        if frame is None:
            break  # ❌ Just exits, doesn't notify server!
        if self._ws:
            await self._ws.send(audio_data)
```

**Problem:** Violates universal STT pattern - server never knows client is done.

**Fix (Aligned with Industry Standards):**
```python
async def _send_loop(self):
    while not self._closed:
        frame = await self._audio_queue.get()
        if frame is None:
            # ✅ Send end-of-stream message (like Deepgram/AssemblyAI)
            if self._ws and not self._ws.closed:
                try:
                    end_msg = json.dumps({"type": "end_of_stream"})
                    await self._ws.send(end_msg)
                    logger.info("Sent end-of-stream message to server")
                except Exception as e:
                    logger.error(f"Failed to send end-of-stream: {e}")
            break
        if self._ws:
            await self._ws.send(audio_data)
```

**Server-Side Required Change:**
```python
# In server's WebSocket handler
async def handle_websocket(websocket):
    async for message in websocket:
        if isinstance(message, bytes):
            # Audio data
            process_audio(message)
        else:
            # JSON control message
            data = json.loads(message)
            if data.get("type") == "end_of_stream":
                # Process remaining audio
                final_result = flush_and_transcribe()
                await websocket.send(json.dumps({
                    "type": "final",
                    "text": final_result
                }))
                # Close connection
                await websocket.close(code=1000)
                break
```

### Comparison with Industry Standards

| Provider | End-of-Stream Message | Server Response | Our Fix |
|----------|----------------------|-----------------|---------|
| Deepgram | `{"type": "CloseStream"}` | Final transcript + metadata | `{"type": "end_of_stream"}` ✅ |
| AssemblyAI | `{"terminate_session": true}` | SessionTerminated | Similar pattern ✅ |
| AWS | Empty event stream frame | Final results | JSON equivalent ✅ |

**Conclusion:** The proposed fix aligns with Deepgram and AssemblyAI patterns.

---

## 7. Recommended Patterns Summary

### Pattern 1: Full Lifecycle Implementation

```python
class STTWebSocketStream:
    """Production-ready STT WebSocket stream."""

    async def _run(self):
        """Main streaming loop."""
        try:
            # 1. Connect
            async with websockets.connect(self.ws_url) as ws:
                self._ws = ws

                # 2. Handshake
                await ws.send(json.dumps(self.config))
                ready = await ws.recv()
                assert json.loads(ready)["type"] == "ready"

                # 3. Start concurrent tasks
                send_task = asyncio.create_task(self._send_loop())
                recv_task = asyncio.create_task(self._recv_loop())
                keepalive_task = asyncio.create_task(self._keepalive_loop())

                # 4. Wait for completion
                await asyncio.gather(send_task, recv_task, keepalive_task)

        except Exception as e:
            logger.error(f"Stream error: {e}")
            await self._event_queue.put(None)
        finally:
            self._closed = True

    async def _send_loop(self):
        """Send audio frames + end-of-stream."""
        try:
            while not self._closed:
                frame = await self._audio_queue.get()

                if frame is None:
                    # ✅ CRITICAL: Send end-of-stream
                    if self._ws and not self._ws.closed:
                        await self._ws.send(json.dumps({
                            "type": "end_of_stream"
                        }))
                    break

                # Send audio as binary
                audio_bytes = frame.data.tobytes()
                await self._ws.send(audio_bytes)

        except Exception as e:
            logger.error(f"Send error: {e}")

    async def _recv_loop(self):
        """Receive transcription results."""
        try:
            while not self._closed and self._ws:
                message = await self._ws.recv()
                data = json.loads(message)

                if data.get("type") == "final":
                    # Emit final transcript
                    event = create_speech_event(data)
                    await self._event_queue.put(event)

                elif data.get("type") == "session_ended":
                    # Server confirmed end
                    break

        except websockets.ConnectionClosed:
            logger.info("Connection closed by server")
        except Exception as e:
            logger.error(f"Receive error: {e}")
        finally:
            await self._event_queue.put(None)

    async def _keepalive_loop(self):
        """Send periodic keepalive messages."""
        try:
            while not self._closed and self._ws:
                await asyncio.sleep(5.0)
                if self._ws and not self._ws.closed:
                    await self._ws.send(json.dumps({
                        "type": "keepalive"
                    }))
        except Exception:
            pass
```

### Pattern 2: Graceful Shutdown

```python
async def aclose(self):
    """Industry-standard graceful shutdown."""
    if self._closed:
        return

    logger.info("Closing STT stream gracefully")

    # 1. Signal end of input (if not already done)
    if not self._input_ended:
        await self.end_input()

    # 2. Wait for final results (with timeout)
    try:
        if self._main_task and not self._main_task.done():
            await asyncio.wait_for(self._main_task, timeout=10.0)
    except asyncio.TimeoutError:
        logger.warning("Timeout waiting for stream completion")

    # 3. Cancel any remaining tasks
    for task in [self._send_task, self._recv_task, self._keepalive_task]:
        if task and not task.done():
            task.cancel()

    # 4. Close WebSocket
    if self._ws and not self._ws.closed:
        await self._ws.close(code=1000, reason="Normal closure")

    self._closed = True
    logger.info("STT stream closed")
```

### Pattern 3: Error Recovery

```python
async def streaming_with_retry(url, audio_source, max_retries=3):
    """Retry pattern with exponential backoff."""

    for attempt in range(max_retries):
        try:
            stream = STTWebSocketStream(url)

            # Start streaming
            async for event in stream:
                yield event

            # Success - exit retry loop
            break

        except websockets.ConnectionClosed as e:
            if e.code == 1000:  # Normal closure
                break

            if attempt < max_retries - 1:
                delay = 2 ** attempt  # Exponential: 1s, 2s, 4s
                logger.warning(f"Connection closed (attempt {attempt+1}), "
                             f"retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                logger.error("Max retries exceeded")
                raise

        finally:
            await stream.aclose()
```

---

## 8. Testing Best Practices

### Test Coverage Requirements

Based on production STT service testing patterns:

```python
import pytest

class TestSTTWebSocket:
    """Comprehensive test suite following industry patterns."""

    @pytest.mark.asyncio
    async def test_normal_lifecycle(self):
        """Test complete normal flow."""
        stream = stt.stream()

        # Push audio
        for frame in audio_frames:
            stream.push_frame(frame)

        # Signal end
        await stream.end_input()

        # Receive results
        results = []
        async for event in stream:
            results.append(event)

        # Verify final results received
        assert any(e.type == FINAL_TRANSCRIPT for e in results)

        # Cleanup
        await stream.aclose()

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Test graceful shutdown with pending audio."""
        stream = stt.stream()

        # Push some audio
        stream.push_frame(audio_frame)

        # Immediate close
        await stream.aclose()

        # Should not hang or error
        assert stream._closed

    @pytest.mark.asyncio
    async def test_end_of_stream_signaling(self, mock_server):
        """Verify end-of-stream message is sent."""
        stream = stt.stream()

        stream.push_frame(audio_frame)
        await stream.end_input()

        # Wait for server to receive end message
        await asyncio.sleep(0.1)

        # Verify server received end-of-stream
        messages = mock_server.get_received_messages()
        assert any(
            json.loads(m).get("type") == "end_of_stream"
            for m in messages if isinstance(m, str)
        )

    @pytest.mark.asyncio
    async def test_connection_recovery(self):
        """Test automatic reconnection on failure."""
        # Simulate connection drop
        with pytest.raises(websockets.ConnectionClosed):
            stream = stt.stream()
            # Inject connection failure
            await stream._ws.close()
            stream.push_frame(audio_frame)

        # Should be able to create new stream
        stream2 = stt.stream()
        stream2.push_frame(audio_frame)
        await stream2.aclose()

    @pytest.mark.asyncio
    async def test_keepalive_prevents_timeout(self, mock_server):
        """Test keepalive messages prevent timeout."""
        stream = stt.stream()

        # Wait longer than timeout period
        await asyncio.sleep(12.0)

        # Verify keepalive messages sent
        keepalives = mock_server.get_keepalive_count()
        assert keepalives >= 2  # Should send every 5 seconds

        # Connection should still be alive
        assert not stream._ws.closed

        await stream.aclose()
```

---

## 9. Configuration Best Practices

### Audio Configuration

```python
# Industry-standard audio config
STT_CONFIG = {
    "sample_rate": 16000,      # 16kHz is standard
    "encoding": "pcm_s16le",    # 16-bit PCM little-endian
    "channels": 1,              # Mono
    "chunk_duration_ms": 50,    # 50ms chunks (800 bytes @ 16kHz)
}

# Provider-specific optimizations
DEEPGRAM_CONFIG = {
    **STT_CONFIG,
    "model": "nova-2",
    "smart_format": True,
    "punctuate": True,
}

ASSEMBLYAI_CONFIG = {
    **STT_CONFIG,
    "word_boost": ["custom", "vocabulary"],
    "end_utterance_silence_threshold": 700,  # ms
}
```

### Connection Configuration

```python
# Timeout configuration
TIMEOUTS = {
    "connect": 10.0,         # WebSocket connect timeout
    "handshake": 5.0,        # Config handshake timeout
    "keepalive": 5.0,        # Keepalive interval
    "response": 30.0,        # Max time waiting for response
    "shutdown": 10.0,        # Graceful shutdown timeout
}

# Retry configuration
RETRY_CONFIG = {
    "max_attempts": 5,
    "base_delay": 1.0,
    "max_delay": 60.0,
    "exponential_base": 2,
    "jitter": 0.1,
}
```

---

## 10. Summary of Critical Findings

### Universal Truths Across All Providers

1. **End-of-stream MUST be explicit** - No provider relies on connection close alone
2. **Binary/Text frame separation** - Audio is binary, control is text (JSON)
3. **Handshake protocol** - All use config → ready → stream pattern
4. **Keepalive required** - Prevent timeout on long pauses
5. **Graceful shutdown** - Always wait for final results before closing
6. **Error recovery** - Exponential backoff retry pattern
7. **Partial vs final** - All provide both types of results

### Critical Anti-Patterns to Avoid

❌ **Breaking send loop without notifying server** (Current bug)
❌ **Sending empty bytes for end-of-stream** (Deprecated)
❌ **Mixing binary/text frames incorrectly**
❌ **Not implementing keepalive** (Causes timeouts)
❌ **Ungraceful connection closure** (Loses final results)
❌ **No retry logic** (Fragile in production)
❌ **Ignoring partial results** (Poor UX)

### Production Readiness Checklist

- [ ] End-of-stream message implemented (JSON text frame)
- [ ] Server handles end-of-stream message
- [ ] Keepalive mechanism (every 5 seconds)
- [ ] Graceful shutdown with timeout
- [ ] Retry logic with exponential backoff
- [ ] Proper WebSocket close codes (1000, 1001)
- [ ] Error handling and logging
- [ ] Buffering for reconnection
- [ ] Comprehensive tests (normal, error, edge cases)
- [ ] Documentation of protocol

---

## 11. References

### Official Documentation
- Deepgram WebSocket API: https://developers.deepgram.com/docs/lower-level-websockets
- AssemblyAI Streaming: https://www.assemblyai.com/docs/guides/real-time-streaming-transcription
- AWS Transcribe Streaming: https://docs.aws.amazon.com/transcribe/latest/dg/streaming-websocket.html
- Azure Speech WebSocket: https://github.com/Azure-Samples/SpeechToText-WebSockets-Javascript
- RFC 6455 (WebSocket Protocol): https://tools.ietf.org/html/rfc6455

### Code Examples
- Deepgram Python SDK: https://github.com/deepgram/deepgram-python-sdk
- AssemblyAI Python SDK: https://github.com/AssemblyAI/assemblyai-python-sdk
- AWS Transcribe Examples: https://github.com/aws-samples/amazon-transcribe-streaming-python-websockets

### Related Issues
- LiveKit STT Plugin Critical Bugs: `/home/user/skills/stt-livekit-plugin/CRITICAL_BUGS.md`
- LiveKit STT Plugin Architecture: `/home/user/skills/stt-livekit-plugin/ARCHITECTURE_ANALYSIS.md`

---

**Document Version:** 1.0
**Research Date:** 2025-11-22
**Status:** Comprehensive Industry Analysis
**Next Actions:** Apply patterns to fix critical bugs in LiveKit plugin
