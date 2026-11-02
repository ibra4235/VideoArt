"""Remake pipeline: montage + caption burn-in + generative video stubs.

Takes one flat talking-head user clip + approved blueprint and produces a
9:16 draft MP4. Generative B-roll slots are filled with labeled stub clips
when no GEN_VIDEO provider key is configured.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path

from .analyzers.media import probe_duration_ms
from .schemas import Blueprint, RemakeResult


@dataclass
class RemakePaths:
    work_dir: Path
    draft_path: Path


def _run_ffmpeg(args: list[str], timeout: int = 180) -> None:
    result = subprocess.run(
        ["ffmpeg", "-y", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-800:]}")


def _escape_drawtext(text: str) -> str:
    # Escape for ffmpeg drawtext
    t = text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    t = t.replace("%", "\\%")
    return t


def _safe_segment_name(scene_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", scene_id) or "scene"


def _make_gen_stub_clip(
    out: Path,
    duration_s: float,
    prompt_hint: str | None,
    scene_id: str,
) -> Path:
    """Placeholder generative B-roll (no API key required)."""
    label = f"GEN STUB {scene_id}"
    hint = (prompt_hint or "B-roll placeholder")[:48]
    vf = (
        f"scale=720:1280,"
        f"drawtext=text='{_escape_drawtext(label)}':fontsize=36:fontcolor=white:"
        f"x=(w-text_w)/2:y=h*0.42:box=1:boxcolor=black@0.5,"
        f"drawtext=text='{_escape_drawtext(hint)}':fontsize=22:fontcolor=0xA8F0D8:"
        f"x=(w-text_w)/2:y=h*0.52"
    )
    try:
        _run_ffmpeg(
            [
                "-f",
                "lavfi",
                "-i",
                f"color=c=0x2A1840:s=720x1280:d={max(duration_s, 0.5):.3f}:r=30",
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=r=44100:cl=stereo:d={max(duration_s, 0.5):.3f}",
                "-vf",
                vf,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(out),
            ]
        )
    except RuntimeError:
        _run_ffmpeg(
            [
                "-f",
                "lavfi",
                "-i",
                f"color=c=0x2A1840:s=720x1280:d={max(duration_s, 0.5):.3f}:r=30",
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=r=44100:cl=stereo:d={max(duration_s, 0.5):.3f}",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(out),
            ]
        )
    return out


def _cut_user_segment(
    user_clip: Path,
    out: Path,
    start_s: float,
    duration_s: float,
    zoom: float = 1.08,
) -> Path:
    """Cut a slice of the user clip and apply a mild push-in (camera feel)."""
    # zoompan gives a slight handheld/push feel; fall back to plain trim+scale.
    frames = max(int(duration_s * 30), 1)
    vf_zoom = (
        f"scale=800:1422,"
        f"zoompan=z='min({zoom},zoom+0.0008)':x='iw/2-(iw/zoom/2)':"
        f"y='ih/2-(ih/zoom/2)':d={frames}:s=720x1280:fps=30,"
        f"setsar=1"
    )
    try:
        _run_ffmpeg(
            [
                "-ss",
                f"{max(start_s, 0):.3f}",
                "-i",
                str(user_clip),
                "-t",
                f"{max(duration_s, 0.2):.3f}",
                "-vf",
                vf_zoom,
                "-an",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(out),
            ],
            timeout=120,
        )
    except RuntimeError:
        _run_ffmpeg(
            [
                "-ss",
                f"{max(start_s, 0):.3f}",
                "-i",
                str(user_clip),
                "-t",
                f"{max(duration_s, 0.2):.3f}",
                "-vf",
                "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1",
                "-an",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(out),
            ],
            timeout=120,
        )
    return out


def _burn_captions(segments: list[tuple[Path, str, float]], out: Path) -> Path:
    """Concat scene segments and burn center-lower captions."""
    work = out.parent
    list_file = work / "concat.txt"
    lines = []
    for path, _, _ in segments:
        # concat demuxer needs escaped paths
        p = str(path).replace("'", "'\\''")
        lines.append(f"file '{p}'")
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    concat_raw = work / "concat_raw.mp4"
    # Re-encode (not stream-copy): gen stubs may include silent audio while
    # user cuts are video-only — mismatched streams break concat -c copy.
    _run_ffmpeg(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(concat_raw),
        ],
        timeout=180,
    )

    # Build drawtext filters timed relative to concat timeline
    filters: list[str] = []
    t = 0.0
    for _, caption, dur in segments:
        if caption.strip():
            wrapped = "\\n".join(textwrap.wrap(caption.strip(), width=28)[:3])
            start = t
            end = t + dur
            filters.append(
                "drawtext="
                f"text='{_escape_drawtext(wrapped)}':"
                "fontsize=42:fontcolor=white:borderw=3:bordercolor=black:"
                "x=(w-text_w)/2:y=h*0.72:"
                f"enable='between(t,{start:.3f},{end:.3f})'"
            )
        t += dur

    if not filters:
        shutil.copy(concat_raw, out)
        return out

    vf = ",".join(filters)
    try:
        _run_ffmpeg(
            [
                "-i",
                str(concat_raw),
                "-vf",
                vf,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-an",
                str(out),
            ],
            timeout=180,
        )
    except RuntimeError:
        # Fonts / drawtext unavailable — ship concat without burn-in
        shutil.copy(concat_raw, out)
    return out


def assemble_draft(
    blueprint: Blueprint,
    user_clip: Path,
    work_dir: Path,
    draft_path: Path,
) -> RemakeResult:
    """Build draft MP4 from user clip + blueprint. Stub gen where needed."""
    work_dir.mkdir(parents=True, exist_ok=True)
    draft_path.parent.mkdir(parents=True, exist_ok=True)

    clip_ms, _ = probe_duration_ms(user_clip)
    if clip_ms <= 0:
        raise RuntimeError("Kullanıcı klibi okunamadı (ffprobe)")

    scenes = blueprint.scenes or []
    if not scenes:
        raise RuntimeError("Blueprint’te sahne yok")

    # Map scenes onto the single flat talking-head clip by proportional time.
    total_scene_ms = sum(max(s.end_ms - s.start_ms, 1) for s in scenes)
    gen_stubs: list[str] = []
    segments: list[tuple[Path, str, float]] = []
    cursor_ms = 0

    for i, scene in enumerate(scenes):
        scene_dur_ms = max(scene.end_ms - scene.start_ms, 400)
        scene_dur_s = scene_dur_ms / 1000.0
        name = _safe_segment_name(scene.id)
        seg_path = work_dir / f"{i:02d}_{name}.mp4"

        if scene.gen_video.needed:
            _make_gen_stub_clip(
                seg_path,
                scene_dur_s,
                scene.gen_video.prompt_hint,
                scene.id,
            )
            gen_stubs.append(scene.id)
        else:
            # Proportional slice from user talking-head
            share = scene_dur_ms / total_scene_ms
            take_ms = max(int(clip_ms * share), 400)
            start_ms = min(cursor_ms, max(clip_ms - take_ms, 0))
            zoom = 1.06 + (0.02 if scene.role == "hook" else 0.0)
            _cut_user_segment(
                user_clip,
                seg_path,
                start_ms / 1000.0,
                take_ms / 1000.0,
                zoom=zoom,
            )
            cursor_ms = start_ms + take_ms

        caption = scene.caption.text if scene.caption else ""
        segments.append((seg_path, caption, scene_dur_s))

    _burn_captions(segments, draft_path)
    if not draft_path.is_file() or draft_path.stat().st_size == 0:
        raise RuntimeError("Draft üretilemedi")

    draft_ms, _ = probe_duration_ms(draft_path)
    return RemakeResult(
        draft_path=str(draft_path),
        duration_ms=draft_ms,
        gen_stub_scenes=gen_stubs,
        montage="ffmpeg_concat_zoompan",
        captions="drawtext_burn_in",
        note=(
            "Draft assembled from one flat talking-head clip. "
            "Gen scenes are labeled stubs (no GEN API key). "
            "Camera feel = mild zoompan; captions burned center-lower."
        ),
    )
