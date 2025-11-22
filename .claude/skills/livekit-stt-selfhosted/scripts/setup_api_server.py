#!/usr/bin/env python3
"""
Setup script for creating a new self-hosted STT API server from template.

Usage:
    python setup_api_server.py <server-name> [--output-dir OUTPUT_DIR] [--model MODEL_ID]

Example:
    python setup_api_server.py my-stt-server --model openai/whisper-medium
"""

import argparse
import shutil
from pathlib import Path


def setup_api_server(server_name: str, output_dir: Path, template_dir: Path, model_id: str):
    """
    Create a new STT API server from the template.

    Args:
        server_name: Name for the server directory
        output_dir: Directory where the server will be created
        template_dir: Path to the API server template
        model_id: Hugging Face model ID to use
    """
    # Create server directory
    server_path = output_dir / server_name

    # Check if directory already exists
    if server_path.exists():
        raise FileExistsError(f"Server directory already exists: {server_path}")

    print(f"Creating STT API server: {server_name}")
    print(f"Location: {server_path}")
    print(f"Model: {model_id}")

    # Copy template
    shutil.copytree(template_dir, server_path)

    # Update .env with model ID
    env_file = server_path / ".env"
    env_example = server_path / ".env.example"

    if env_example.exists():
        content = env_example.read_text()
        # Set the model ID
        content = content.replace(
            "MODEL_ID=openai/whisper-large-v3",
            f"MODEL_ID={model_id}"
        )
        env_file.write_text(content)

    # Create Dockerfile
    dockerfile_content = """FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Install Python and dependencies
RUN apt-get update && apt-get install -y \\
    python3.10 \\
    python3-pip \\
    ffmpeg \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Optional: Download model at build time (saves startup time)
# Uncomment to pre-download model
# RUN python3 -c "from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor; \\
#     AutoModelForSpeechSeq2Seq.from_pretrained('MODEL_ID'); \\
#     AutoProcessor.from_pretrained('MODEL_ID')"

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
""".replace("MODEL_ID", model_id)

    (server_path / "Dockerfile").write_text(dockerfile_content)

    # Create docker-compose.yml
    docker_compose_content = f"""version: '3.8'

services:
  stt-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MODEL_ID={model_id}
      - DEVICE=cuda:0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped
"""

    (server_path / "docker-compose.yml").write_text(docker_compose_content)

    print(f"\n✅ API server created successfully!")
    print(f"\nNext steps:")
    print(f"1. cd {server_path}")
    print(f"2. Review and customize main.py if needed")
    print(f"3. Install dependencies: pip install -r requirements.txt")
    print(f"4. Run the server:")
    print(f"   - Development: python main.py")
    print(f"   - Production: uvicorn main:app --host 0.0.0.0 --port 8000")
    print(f"   - Docker: docker-compose up")
    print(f"\nThe API will be available at: http://localhost:8000")
    print(f"WebSocket endpoint: ws://localhost:8000/ws/transcribe")


def main():
    parser = argparse.ArgumentParser(
        description="Create a new self-hosted STT API server from template"
    )
    parser.add_argument(
        "server_name",
        help="Name for the server directory (e.g., 'my-stt-server')"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory where the server will be created (default: current directory)",
    )
    parser.add_argument(
        "--model",
        default="openai/whisper-large-v3",
        help="Hugging Face model ID (default: openai/whisper-large-v3)",
    )

    args = parser.parse_args()

    # Get the template directory (relative to this script)
    script_dir = Path(__file__).parent
    template_dir = script_dir.parent / "assets" / "api-server"

    if not template_dir.exists():
        print(f"❌ Error: Template directory not found: {template_dir}")
        return 1

    try:
        setup_api_server(args.server_name, args.output_dir, template_dir, args.model)
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
