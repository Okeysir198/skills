"""
Self-hosted STT API Server using FastAPI and Whisper/Hugging Face models.

This server provides WebSocket-based real-time speech-to-text transcription
compatible with LiveKit STT plugin interface.
"""

import asyncio
import json
import logging
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import torch
import torchaudio
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Self-Hosted STT API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
class Config:
    MODEL_ID: str = "openai/whisper-large-v3"  # Can be changed to other models
    DEVICE: str = "cuda:0" if torch.cuda.is_available() else "cpu"
    TORCH_DTYPE: torch.dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    SAMPLE_RATE: int = 16000
    CHUNK_DURATION_MS: int = 1000  # Process audio in 1-second chunks

config = Config()

# Global model instance (loaded on startup)
model = None
processor = None
pipe = None

@app.on_event("startup")
async def startup_event():
    """Load the model on startup to avoid loading it for each request."""
    global model, processor, pipe

    logger.info(f"Loading model: {config.MODEL_ID}")
    logger.info(f"Using device: {config.DEVICE}")

    try:
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            config.MODEL_ID,
            torch_dtype=config.TORCH_DTYPE,
            low_cpu_mem_usage=True,
            use_safetensors=True
        )
        model.to(config.DEVICE)

        processor = AutoProcessor.from_pretrained(config.MODEL_ID)

        pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            max_new_tokens=128,
            chunk_length_s=30,
            batch_size=16,
            return_timestamps=True,
            torch_dtype=config.TORCH_DTYPE,
            device=config.DEVICE,
        )

        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model": config.MODEL_ID,
        "device": config.DEVICE
    }

@app.get("/health")
async def health():
    """Health check for the service."""
    return {
        "status": "healthy" if pipe is not None else "initializing",
        "model_loaded": pipe is not None
    }

class AudioBuffer:
    """Buffer for accumulating audio chunks."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.buffer = []

    def add_chunk(self, chunk: bytes):
        """Add audio chunk to buffer."""
        self.buffer.append(chunk)

    def get_audio_array(self) -> Optional[np.ndarray]:
        """Convert buffered chunks to numpy array."""
        if not self.buffer:
            return None

        # Combine all chunks
        audio_bytes = b''.join(self.buffer)

        # Convert bytes to numpy array (assuming 16-bit PCM)
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)

        # Normalize to [-1, 1]
        audio_array = audio_array.astype(np.float32) / 32768.0

        return audio_array

    def clear(self):
        """Clear the buffer."""
        self.buffer = []

    def duration_seconds(self) -> float:
        """Get current buffer duration in seconds."""
        if not self.buffer:
            return 0.0
        total_bytes = sum(len(chunk) for chunk in self.buffer)
        # 16-bit PCM = 2 bytes per sample
        total_samples = total_bytes // 2
        return total_samples / self.sample_rate

@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """
    WebSocket endpoint for real-time transcription.

    Expected message format:
    - Audio chunks: raw binary audio data (16-bit PCM, 16kHz)
    - Config message: {"type": "config", "language": "en", "detect_language": false}
    - End message: {"type": "end"}

    Response format:
    - {"type": "interim", "text": "partial transcription..."}
    - {"type": "final", "text": "complete transcription", "language": "en"}
    """
    await websocket.accept()
    logger.info("WebSocket connection established")

    audio_buffer = AudioBuffer(sample_rate=config.SAMPLE_RATE)
    language = "en"
    detect_language = False

    try:
        while True:
            # Receive message (either binary audio or JSON config)
            message = await websocket.receive()

            if "bytes" in message:
                # Audio chunk received
                audio_chunk = message["bytes"]
                audio_buffer.add_chunk(audio_chunk)

                # Process when buffer reaches threshold
                if audio_buffer.duration_seconds() >= config.CHUNK_DURATION_MS / 1000:
                    audio_array = audio_buffer.get_audio_array()

                    if audio_array is not None and len(audio_array) > 0:
                        # Run transcription
                        try:
                            result = pipe(
                                audio_array,
                                generate_kwargs={
                                    "language": None if detect_language else language,
                                }
                            )

                            # Send interim result
                            await websocket.send_json({
                                "type": "interim",
                                "text": result["text"],
                                "chunks": result.get("chunks", [])
                            })

                        except Exception as e:
                            logger.error(f"Transcription error: {e}")
                            await websocket.send_json({
                                "type": "error",
                                "message": str(e)
                            })

                    # Clear buffer after processing
                    audio_buffer.clear()

            elif "text" in message:
                # JSON control message
                data = json.loads(message["text"])
                msg_type = data.get("type")

                if msg_type == "config":
                    # Update configuration
                    language = data.get("language", language)
                    detect_language = data.get("detect_language", detect_language)
                    logger.info(f"Config updated: language={language}, detect={detect_language}")

                elif msg_type == "end":
                    # Process remaining audio in buffer
                    audio_array = audio_buffer.get_audio_array()

                    if audio_array is not None and len(audio_array) > 0:
                        try:
                            result = pipe(
                                audio_array,
                                generate_kwargs={
                                    "language": None if detect_language else language,
                                }
                            )

                            # Send final result
                            await websocket.send_json({
                                "type": "final",
                                "text": result["text"],
                                "chunks": result.get("chunks", []),
                                "language": result.get("language", language)
                            })

                        except Exception as e:
                            logger.error(f"Final transcription error: {e}")
                            await websocket.send_json({
                                "type": "error",
                                "message": str(e)
                            })

                    audio_buffer.clear()
                    break

    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
