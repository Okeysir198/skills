"""
Self-hosted STT API using faster-whisper and FastAPI.
Provides both batch transcription and real-time streaming via WebSocket.
"""

import asyncio
import json
import logging
import os
from typing import Optional, Literal
from io import BytesIO

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Self-Hosted STT API",
    description="Speech-to-Text API using faster-whisper",
    version="1.0.0"
)

# Global model instance
model: Optional[WhisperModel] = None

# Configuration
MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")  # tiny, base, small, medium, large-v2, large-v3
DEVICE = os.getenv("WHISPER_DEVICE", "cpu")  # cpu, cuda
COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # int8, float16, float32


def load_model():
    """Load the Whisper model on startup."""
    global model
    logger.info(f"Loading Whisper model: {MODEL_SIZE} on {DEVICE} with {COMPUTE_TYPE}")
    model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    logger.info("Model loaded successfully")


@app.on_event("startup")
async def startup_event():
    """Initialize model on startup."""
    load_model()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": MODEL_SIZE,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "model_loaded": model is not None}


@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Query(None, description="Language code (e.g., 'en', 'es', 'fr')"),
    task: Literal["transcribe", "translate"] = Query("transcribe", description="Task to perform"),
    beam_size: int = Query(5, description="Beam size for decoding"),
    vad_filter: bool = Query(True, description="Enable VAD filtering"),
):
    """
    Transcribe audio file to text.

    Args:
        file: Audio file (WAV, MP3, etc.)
        language: Source language code (auto-detect if None)
        task: 'transcribe' or 'translate' (translate to English)
        beam_size: Beam size for beam search decoding
        vad_filter: Enable voice activity detection filter

    Returns:
        JSON with transcription results
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Read audio file
        audio_bytes = await file.read()

        # Save to temporary file (faster-whisper requires file path)
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".audio") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name

        try:
            # Transcribe
            segments, info = model.transcribe(
                tmp_path,
                language=language,
                task=task,
                beam_size=beam_size,
                vad_filter=vad_filter,
            )

            # Collect all segments
            results = []
            full_text = []
            for segment in segments:
                results.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "confidence": segment.avg_logprob,
                })
                full_text.append(segment.text.strip())

            return JSONResponse({
                "text": " ".join(full_text),
                "segments": results,
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
            })

        finally:
            # Clean up temp file
            os.unlink(tmp_path)

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    WebSocket endpoint for real-time streaming transcription.

    Protocol:
    - Client connects and sends configuration as first message:
      {"language": "en", "sample_rate": 16000, "task": "transcribe"}
    - Client sends raw PCM audio data (int16 bytes)
    - Server responds with transcription events:
      {"type": "interim", "text": "partial result"}
      {"type": "final", "text": "final result", "start": 0.0, "end": 2.5}
    """
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
        chunk_duration = 2.0  # Process every 2 seconds of audio
        bytes_per_chunk = int(sample_rate * chunk_duration * 2)  # 2 bytes per int16 sample

        while True:
            try:
                # Receive audio data
                data = await websocket.receive_bytes()
                audio_buffer.extend(data)

                # Process when we have enough audio
                if len(audio_buffer) >= bytes_per_chunk:
                    # Convert bytes to numpy array
                    audio_np = np.frombuffer(bytes(audio_buffer[:bytes_per_chunk]), dtype=np.int16)
                    audio_float = audio_np.astype(np.float32) / 32768.0  # Normalize to [-1, 1]

                    # Save to temp file for processing
                    import tempfile
                    import soundfile as sf

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                        sf.write(tmp_file.name, audio_float, sample_rate)
                        tmp_path = tmp_file.name

                    try:
                        # Transcribe chunk
                        segments, info = model.transcribe(
                            tmp_path,
                            language=language,
                            task=task,
                            beam_size=3,  # Lower beam size for faster processing
                            vad_filter=True,
                        )

                        # Send results
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

                    # Remove processed audio from buffer, keep overlap
                    overlap_bytes = int(sample_rate * 0.5 * 2)  # 0.5s overlap
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


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
