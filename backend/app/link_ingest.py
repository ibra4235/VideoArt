"""Instagram / TikTok link ingest — interface + stub.

IMPORTANT (product / legal):
- Instagram and TikTok Terms of Service generally prohibit unauthorized
  scraping / automated download of media. VideoArt must NOT ship a
  production scraper that pulls private CDN assets without an official API
  or explicit platform permission.
- This module accepts a public reel/tiktok URL, validates host shape, and
  produces a *placeholder* reference video so the analyze → remake pipe
  can be exercised end-to-end. Real download is intentionally stubbed.

TODO (when/if legally cleared):
- Integrate an official partner API, user Share Extension + local file,
  or licensed third-party provider with ToS-safe access.
- Never store or redistribute the original platform audio track as a clone.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

_IG_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com"}
_TT_HOSTS = {"tiktok.com", "www.tiktok.com", "vm.tiktok.com", "m.tiktok.com"}

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


@dataclass
class LinkIngestResult:
    platform: str  # instagram | tiktok
    normalized_url: str
    stub_video_path: Path
    stub_note: str


def normalize_and_validate_url(raw: str) -> tuple[str, str]:
    """Return (platform, normalized_url) or raise ValueError."""
    url = (raw or "").strip()
    if not url:
        raise ValueError("Link boş")
    if not _URL_RE.match(url):
        url = "https://" + url
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in _IG_HOSTS or host.endswith(".instagram.com"):
        return "instagram", url
    if host in _TT_HOSTS or host.endswith(".tiktok.com"):
        return "tiktok", url
    raise ValueError(
        "Sadece Instagram veya TikTok linki desteklenir "
        "(ör. https://www.instagram.com/reel/... veya https://www.tiktok.com/@.../video/...)"
    )


def create_stub_reference_video(dest: Path, duration_sec: float = 8.0) -> Path:
    """Synthesize a 9:16 placeholder MP4 so analyze can run without scraping."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Soft teal gradient-ish solid + on-screen note that this is a stub.
    # drawtext may be unavailable if libfreetype missing — fall back to color only.
    label = "VideoArt link stub — not a real download"
    vf = (
        f"scale=720:1280,drawtext=text='{label}':fontsize=28:fontcolor=white:"
        "x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.45"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=0x1A3A36:s=720x1280:d={duration_sec}:r=30",
        "-f",
        "lavfi",
        "-i",
        f"anullsrc=r=44100:cl=stereo:d={duration_sec}",
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0 or not dest.is_file():
        # Retry without drawtext
        cmd_plain = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x1A3A36:s=720x1280:d={duration_sec}:r=30",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r=44100:cl=stereo:d={duration_sec}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(dest),
        ]
        result2 = subprocess.run(cmd_plain, capture_output=True, text=True, timeout=60)
        if result2.returncode != 0 or not dest.is_file():
            raise RuntimeError(
                f"Stub referans video üretilemedi: {result2.stderr[-400:] or result.stderr[-400:]}"
            )
    return dest


async def ingest_link_stub(url: str, dest: Path) -> LinkIngestResult:
    """Validate URL and write a stub reference video. No network scrape."""
    platform, normalized = normalize_and_validate_url(url)
    create_stub_reference_video(dest)
    note = (
        f"STUB: {platform} link accepted ({normalized}). "
        "Real media download is NOT implemented (IG/TikTok ToS). "
        "A synthetic placeholder was analyzed instead — use file upload for real references."
    )
    return LinkIngestResult(
        platform=platform,
        normalized_url=normalized,
        stub_video_path=dest,
        stub_note=note,
    )
