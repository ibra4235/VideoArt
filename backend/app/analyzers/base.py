from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from ..schemas import Blueprint


@runtime_checkable
class VideoAnalyzer(Protocol):
    """Analyze a reference video file into a remake blueprint JSON."""

    name: str

    async def analyze(self, video_path: Path, filename: str) -> Blueprint:
        """Return a Blueprint matching docs/videoart-mvp-blueprint.md schema."""
