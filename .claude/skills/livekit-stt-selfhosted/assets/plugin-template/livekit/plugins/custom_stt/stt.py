"""
Custom STT plugin for LiveKit Agents connecting to self-hosted API.

This plugin implements the LiveKit STT interface to connect to a
self-hosted speech-to-text API server (like the FastAPI Whisper server).
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp
from livekit import rtc
from livekit.agents import stt, utils

logger = logging.getLogger(__name__)


@dataclass
class STTOptions:
    """Configuration options for the STT service."""

    api_url: str
    language: str = "en"
    detect_language: bool = False
    sample_rate: int = 16000


class STT(stt.STT):
    """
    Custom STT implementation that connects to a self-hosted API.

    Example:
        from livekit.plugins import custom_stt

        stt_instance = custom_stt.STT(
            api_url="ws://localhost:8000/ws/transcribe",
            language="en"
        )
    """

    def __init__(
        self,
        *,
        api_url: str = "ws://localhost:8000/ws/transcribe",
        language: str = "en",
        detect_language: bool = False,
        sample_rate: int = 16000,
    ):
        """
        Initialize the custom STT plugin.

        Args:
            api_url: WebSocket URL of the self-hosted STT API
            language: Language code for transcription (e.g., "en", "es")
            detect_language: Whether to auto-detect language
            sample_rate: Audio sample rate in Hz
        """
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=True,
                interim_results=True,
            )
        )

        self._opts = STTOptions(
            api_url=api_url,
            language=language,
            detect_language=detect_language,
            sample_rate=sample_rate,
        )

    def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have an active aiohttp session."""
        if not hasattr(self, "_session") or self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _recognize_impl(
        self,
        buffer: utils.AudioBuffer,
        *,
        language: Optional[str] = None,
    ) -> stt.SpeechEvent:
        """
        Recognize speech from a complete audio buffer (non-streaming).

        Args:
            buffer: Audio buffer to transcribe
            language: Optional language override

        Returns:
            SpeechEvent with the final transcription
        """
        # Convert audio buffer to bytes (16-bit PCM)
        audio_data = buffer.remix_and_resample(
            self._opts.sample_rate, 1
        ).data.tobytes()

        session = self._ensure_session()

        try:
            # Connect to WebSocket
            async with session.ws_connect(self._opts.api_url) as ws:
                # Send configuration
                await ws.send_json({
                    "type": "config",
                    "language": language or self._opts.language,
                    "detect_language": self._opts.detect_language,
                })

                # Send audio data
                await ws.send_bytes(audio_data)

                # Send end signal
                await ws.send_json({"type": "end"})

                # Wait for final response
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)

                        if data.get("type") == "final":
                            return stt.SpeechEvent(
                                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                                alternatives=[
                                    stt.SpeechData(
                                        text=data.get("text", ""),
                                        language=data.get("language", language or self._opts.language),
                                    )
                                ],
                            )
                        elif data.get("type") == "error":
                            raise Exception(f"STT API error: {data.get('message')}")

                # If we exit the loop without getting a final result
                return stt.SpeechEvent(
                    type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                    alternatives=[
                        stt.SpeechData(text="", language=language or self._opts.language)
                    ],
                )

        except Exception as e:
            logger.error(f"Recognition error: {e}")
            raise

    def stream(
        self,
        *,
        language: Optional[str] = None,
    ) -> "SpeechStream":
        """
        Create a streaming recognition session.

        Args:
            language: Optional language override

        Returns:
            SpeechStream instance for streaming transcription
        """
        return SpeechStream(
            stt=self,
            language=language or self._opts.language,
            sample_rate=self._opts.sample_rate,
        )


class SpeechStream(stt.SpeechStream):
    """Streaming speech recognition session."""

    def __init__(
        self,
        *,
        stt: STT,
        language: str,
        sample_rate: int,
    ):
        super().__init__(stt=stt, sample_rate=sample_rate)
        self._stt = stt
        self._language = language
        self._sample_rate = sample_rate
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._closed = False

    async def _run(self):
        """Run the streaming recognition session."""
        try:
            self._session = aiohttp.ClientSession()
            self._ws = await self._session.ws_connect(self._stt._opts.api_url)

            # Send initial configuration
            await self._ws.send_json({
                "type": "config",
                "language": self._language,
                "detect_language": self._stt._opts.detect_language,
            })

            # Start tasks for sending and receiving
            send_task = asyncio.create_task(self._send_task())
            receive_task = asyncio.create_task(self._receive_task())

            # Wait for either task to complete
            await asyncio.gather(send_task, receive_task, return_exceptions=True)

        except Exception as e:
            logger.error(f"Stream error: {e}")
        finally:
            await self._cleanup()

    async def _send_task(self):
        """Task for sending audio chunks to the API."""
        try:
            async for frame in self._input_ch:
                if self._closed or self._ws is None:
                    break

                # Convert frame to bytes (16-bit PCM)
                audio_data = frame.remix_and_resample(
                    self._sample_rate, 1
                ).data.tobytes()

                # Send audio chunk
                await self._ws.send_bytes(audio_data)

        except Exception as e:
            logger.error(f"Send task error: {e}")

    async def _receive_task(self):
        """Task for receiving transcription results from the API."""
        try:
            if self._ws is None:
                return

            async for msg in self._ws:
                if self._closed:
                    break

                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)

                    if data.get("type") == "interim":
                        # Interim result
                        event = stt.SpeechEvent(
                            type=stt.SpeechEventType.INTERIM_TRANSCRIPT,
                            alternatives=[
                                stt.SpeechData(
                                    text=data.get("text", ""),
                                    language=self._language,
                                )
                            ],
                        )
                        self._event_ch.send_nowait(event)

                    elif data.get("type") == "final":
                        # Final result
                        event = stt.SpeechEvent(
                            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                            alternatives=[
                                stt.SpeechData(
                                    text=data.get("text", ""),
                                    language=data.get("language", self._language),
                                )
                            ],
                        )
                        self._event_ch.send_nowait(event)

                    elif data.get("type") == "error":
                        logger.error(f"STT API error: {data.get('message')}")

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {msg}")
                    break

        except Exception as e:
            logger.error(f"Receive task error: {e}")

    async def _cleanup(self):
        """Clean up resources."""
        self._closed = True

        if self._ws is not None:
            try:
                await self._ws.send_json({"type": "end"})
                await self._ws.close()
            except:
                pass
            self._ws = None

        if self._session is not None:
            try:
                await self._session.close()
            except:
                pass
            self._session = None

    async def aclose(self):
        """Close the stream."""
        await self._cleanup()
        await super().aclose()
