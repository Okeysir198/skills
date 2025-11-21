"""
Speech-to-Text plugin for LiveKit using custom self-hosted STT API.
"""

import asyncio
import logging
import json
from dataclasses import dataclass
from typing import Optional, Literal
from urllib.parse import urljoin

import aiohttp
import websockets
from livekit import agents, rtc
from livekit.agents import stt, utils

logger = logging.getLogger(__name__)


@dataclass
class STTOptions:
    """Configuration options for the custom STT service."""

    language: Optional[str] = None
    """Language code (e.g., 'en', 'es', 'fr'). None for auto-detection."""

    task: Literal["transcribe", "translate"] = "transcribe"
    """Task to perform: 'transcribe' or 'translate' (translate to English)."""

    beam_size: int = 5
    """Beam size for decoding (higher = better quality, slower)."""

    vad_filter: bool = True
    """Enable Voice Activity Detection filtering."""

    sample_rate: int = 16000
    """Audio sample rate in Hz."""


class STT(stt.STT):
    """
    Speech-to-Text implementation for custom self-hosted STT API.

    This plugin connects to a self-hosted FastAPI service running
    the faster-whisper model for transcription.
    """

    def __init__(
        self,
        *,
        api_url: str = "http://localhost:8000",
        options: Optional[STTOptions] = None,
        http_session: Optional[aiohttp.ClientSession] = None,
    ):
        """
        Initialize the STT plugin.

        Args:
            api_url: Base URL of the self-hosted STT API
            options: Configuration options for transcription
            http_session: Optional aiohttp session for connection pooling
        """
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=True,
                interim_results=False,  # Whisper provides final results
            )
        )

        self._api_url = api_url.rstrip("/")
        self._options = options or STTOptions()
        self._session = http_session
        self._own_session = http_session is None

    @property
    def model(self) -> str:
        """Return the model identifier."""
        return "whisper"

    @property
    def provider(self) -> str:
        """Return the provider name."""
        return "custom-stt"

    async def _recognize_impl(
        self,
        buffer: utils.AudioBuffer,
        *,
        language: Optional[str] = None,
    ) -> stt.SpeechEvent:
        """
        Perform batch transcription on an audio buffer.

        Args:
            buffer: Audio buffer to transcribe
            language: Optional language override

        Returns:
            SpeechEvent with transcription results
        """
        session = await self._ensure_session()

        # Convert audio buffer to bytes
        audio_data = buffer.data.tobytes()

        # Prepare form data
        form_data = aiohttp.FormData()
        form_data.add_field(
            "file",
            audio_data,
            filename="audio.wav",
            content_type="audio/wav",
        )

        # Build URL with query parameters
        url = urljoin(self._api_url, "/transcribe")
        params = {
            "language": language or self._options.language,
            "task": self._options.task,
            "beam_size": self._options.beam_size,
            "vad_filter": self._options.vad_filter,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        try:
            async with session.post(url, data=form_data, params=params) as response:
                response.raise_for_status()
                result = await response.json()

                # Extract transcription text
                text = result.get("text", "")
                segments = result.get("segments", [])

                # Create alternatives with confidence scores
                alternatives = []
                if text:
                    # Use average confidence from segments
                    avg_confidence = 0.0
                    if segments:
                        confidences = [seg.get("confidence", 0.0) for seg in segments]
                        avg_confidence = sum(confidences) / len(confidences)

                    alternatives.append(
                        stt.SpeechData(
                            text=text,
                            language=result.get("language", ""),
                            confidence=avg_confidence,
                        )
                    )

                return stt.SpeechEvent(
                    type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                    alternatives=alternatives,
                )

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error during transcription: {e}")
            raise

    def stream(
        self,
        *,
        language: Optional[str] = None,
    ) -> "SpeechStream":
        """
        Create a streaming transcription session.

        Args:
            language: Optional language override

        Returns:
            SpeechStream instance for real-time transcription
        """
        return SpeechStream(
            stt=self,
            api_url=self._api_url,
            options=self._options,
            language=language,
        )

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure HTTP session exists."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def aclose(self):
        """Clean up resources."""
        if self._own_session and self._session is not None:
            await self._session.close()
            self._session = None


class SpeechStream(stt.SpeechStream):
    """
    Streaming transcription session using WebSocket.
    """

    def __init__(
        self,
        *,
        stt: STT,
        api_url: str,
        options: STTOptions,
        language: Optional[str] = None,
    ):
        super().__init__()

        self._stt = stt
        self._api_url = api_url
        self._options = options
        self._language = language

        # WebSocket connection
        self._ws: Optional[websockets.WebSocketClientProtocol] = None

        # Tasks for managing the stream
        self._send_task: Optional[asyncio.Task] = None
        self._recv_task: Optional[asyncio.Task] = None

        # Audio queue for sending
        self._audio_queue: asyncio.Queue[Optional[rtc.AudioFrame]] = asyncio.Queue()

        # Event queue for receiving transcriptions
        self._event_queue: asyncio.Queue[Optional[stt.SpeechEvent]] = asyncio.Queue()

        # State
        self._closed = False

    async def _run(self):
        """Main execution loop for the stream."""
        try:
            # Build WebSocket URL
            ws_url = self._api_url.replace("http://", "ws://").replace("https://", "wss://")
            ws_url = urljoin(ws_url, "/ws/transcribe")

            # Connect to WebSocket
            async with websockets.connect(ws_url) as ws:
                self._ws = ws
                logger.info(f"Connected to STT WebSocket: {ws_url}")

                # Send configuration
                config = {
                    "language": self._language or self._options.language,
                    "sample_rate": self._options.sample_rate,
                    "task": self._options.task,
                }
                await ws.send(json.dumps(config))

                # Wait for ready message
                ready_msg = await ws.recv()
                ready_data = json.loads(ready_msg)
                if ready_data.get("type") != "ready":
                    raise RuntimeError(f"Unexpected response: {ready_data}")

                logger.info("STT WebSocket ready")

                # Start send and receive tasks
                self._send_task = asyncio.create_task(self._send_loop())
                self._recv_task = asyncio.create_task(self._recv_loop())

                # Wait for tasks to complete
                await asyncio.gather(self._send_task, self._recv_task)

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            # Put sentinel to signal error
            await self._event_queue.put(None)

        finally:
            self._closed = True
            if self._ws:
                await self._ws.close()

    async def _send_loop(self):
        """Send audio frames to the WebSocket."""
        try:
            while not self._closed:
                frame = await self._audio_queue.get()

                if frame is None:
                    # Sentinel received, stop sending
                    break

                if self._ws:
                    # Convert frame to bytes and send
                    audio_data = frame.data.tobytes()
                    await self._ws.send(audio_data)

        except Exception as e:
            logger.error(f"Send loop error: {e}")

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

                elif event_type == "error":
                    logger.error(f"STT error: {data.get('message')}")
                    break

        except Exception as e:
            logger.error(f"Receive loop error: {e}")

        finally:
            # Signal completion
            await self._event_queue.put(None)

    def push_frame(self, frame: rtc.AudioFrame):
        """
        Push an audio frame for transcription.

        Args:
            frame: Audio frame to transcribe
        """
        if self._closed:
            return

        asyncio.create_task(self._audio_queue.put(frame))

    async def flush(self):
        """Flush any buffered audio."""
        # Not needed for this implementation
        pass

    async def end_input(self):
        """Signal that no more audio will be sent."""
        await self._audio_queue.put(None)

    async def aclose(self):
        """Close the stream and clean up resources."""
        if self._closed:
            return

        self._closed = True

        # Signal tasks to stop
        await self._audio_queue.put(None)

        # Cancel tasks
        if self._send_task and not self._send_task.done():
            self._send_task.cancel()
        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()

        # Close WebSocket
        if self._ws:
            await self._ws.close()

    async def __anext__(self) -> stt.SpeechEvent:
        """Get the next transcription event."""
        event = await self._event_queue.get()

        if event is None:
            raise StopAsyncIteration

        return event
