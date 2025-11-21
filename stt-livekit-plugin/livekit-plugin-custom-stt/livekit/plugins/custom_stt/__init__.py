"""
LiveKit plugin for custom self-hosted STT API.
"""

from .stt import STT, STTOptions
from .version import __version__

__all__ = ["STT", "STTOptions", "__version__"]
