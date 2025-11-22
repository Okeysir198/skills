"""LiveKit plugin for custom self-hosted STT API."""

from .stt import STT
from .version import __version__

__all__ = ["STT", "__version__"]
