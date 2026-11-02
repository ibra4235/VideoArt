from __future__ import annotations

from ..config import ANALYZER_PROVIDER, OPENAI_API_KEY
from .base import VideoAnalyzer
from .openai_vision import OpenAIVisionAnalyzer
from .stub import StubAnalyzer


def get_analyzer() -> VideoAnalyzer:
    if ANALYZER_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise RuntimeError(
                "ANALYZER_PROVIDER=openai but OPENAI_API_KEY is empty. "
                "Set the key or use ANALYZER_PROVIDER=stub."
            )
        return OpenAIVisionAnalyzer()
    return StubAnalyzer()


__all__ = ["VideoAnalyzer", "StubAnalyzer", "OpenAIVisionAnalyzer", "get_analyzer"]
