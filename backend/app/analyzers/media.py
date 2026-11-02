from __future__ import annotations

import json
import subprocess
from pathlib import Path


def probe_duration_ms(video_path: Path) -> tuple[int, float]:
    """Return (duration_ms, fps_hint) via ffprobe; zeros on failure."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        if result.returncode != 0:
            return 0, 30.0
        data = json.loads(result.stdout or "{}")
        duration_s = float(data.get("format", {}).get("duration") or 0)
        fps = 30.0
        for stream in data.get("streams") or []:
            if stream.get("codec_type") == "video":
                rate = stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "30/1"
                if isinstance(rate, str) and "/" in rate:
                    num, den = rate.split("/", 1)
                    den_f = float(den) or 1.0
                    fps = float(num) / den_f
                break
        return int(duration_s * 1000), round(fps, 2)
    except Exception:
        return 0, 30.0


def sample_frames(video_path: Path, out_dir: Path, count: int = 6) -> list[Path]:
    """Extract evenly spaced JPEG frames for vision analysis."""
    out_dir.mkdir(parents=True, exist_ok=True)
    duration_ms, _ = probe_duration_ms(video_path)
    duration_s = max(duration_ms / 1000.0, 1.0)
    frames: list[Path] = []
    for i in range(count):
        t = (i + 0.5) * duration_s / count
        out = out_dir / f"frame_{i:02d}.jpg"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{t:.3f}",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-q:v",
                "3",
                str(out),
            ],
            capture_output=True,
            check=False,
            timeout=60,
        )
        if out.is_file() and out.stat().st_size > 0:
            frames.append(out)
    return frames
