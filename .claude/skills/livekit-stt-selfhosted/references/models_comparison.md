# Hugging Face STT Models Comparison

Guide for selecting the best speech-to-text model for your self-hosted API.

## Whisper Models (Recommended)

OpenAI Whisper models are the most popular choice for self-hosted STT.

### Model Variants

| Model | Parameters | VRAM | Speed | Quality | Use Case |
|-------|-----------|------|-------|---------|----------|
| whisper-large-v3 | 1550M | ~10GB | Slow | Excellent | Production, best accuracy |
| whisper-medium | 769M | ~5GB | Medium | Very Good | Balanced performance |
| whisper-small | 244M | ~2GB | Fast | Good | Resource-constrained |
| whisper-tiny | 39M | <1GB | Very Fast | Fair | Real-time, CPU-only |

### Model IDs
- `openai/whisper-large-v3` - Latest and most accurate
- `openai/whisper-large-v2` - Previous version
- `openai/whisper-medium`
- `openai/whisper-small`
- `openai/whisper-tiny`

### Language Support
All Whisper models support 99+ languages. Specify language in API config or enable auto-detection.

## Alternative Models

### WhisperX (Faster Inference)
- Model: Uses faster-whisper backend
- Speed: Up to 70x realtime with large-v2
- Benefits: Word-level timestamps, speaker diarization
- Drawback: Requires additional setup

### Wav2Vec 2.0
- Model: `facebook/wav2vec2-large-960h`
- Language: English only
- Speed: Very fast
- Quality: Good for English
- VRAM: ~2GB

### Hubert
- Model: `facebook/hubert-large-ls960-ft`
- Language: English only
- Speed: Fast
- Use case: Good for noisy environments

## Fine-tuned Models

Search Hugging Face for domain-specific models:
- Medical: Search "whisper medical"
- Legal: Search "whisper legal"
- Accents: Many accent-specific fine-tunes available

## Selection Guide

### For Best Accuracy
Use `openai/whisper-large-v3` with GPU (8GB+ VRAM)

### For Production Balance
Use `openai/whisper-medium` - good quality, reasonable speed

### For Real-time Requirements
Use `openai/whisper-small` or `whisper-tiny` depending on quality needs

### For CPU-only Deployment
Use `openai/whisper-tiny` or `facebook/wav2vec2-large-960h`

### For Multilingual
Use any Whisper model with language auto-detection

## Performance Optimization

### GPU Acceleration
```python
DEVICE = "cuda:0"
TORCH_DTYPE = torch.float16  # Use FP16 on GPU
```

### CPU Optimization
```python
DEVICE = "cpu"
TORCH_DTYPE = torch.float32  # Use FP32 on CPU
```

### Batch Processing
Increase `batch_size` in pipeline for processing multiple requests:
```python
pipe = pipeline(..., batch_size=16)
```

### Memory Management
Set `low_cpu_mem_usage=True` when loading model:
```python
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    model_id,
    low_cpu_mem_usage=True
)
```

## Model Updates (2025)

- **SimulStreaming** is replacing WhisperStreaming for better real-time performance
- **Whisper Large V3** is the current SOTA from OpenAI
- **Distil-Whisper** models offer 6x faster inference with minimal quality loss

## Additional Resources

- Hugging Face Models: https://huggingface.co/models?pipeline_tag=automatic-speech-recognition
- Whisper Documentation: https://github.com/openai/whisper
- WhisperX: https://github.com/m-bain/whisperX
