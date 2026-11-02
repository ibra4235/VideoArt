from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path

import httpx

from ..config import OPENAI_API_KEY, OPENAI_VISION_MODEL
from ..schemas import Blueprint
from .media import probe_duration_ms, sample_frames
from .stub import StubAnalyzer

SYSTEM_PROMPT = """Sen VideoArt analiz motorusun. Kullanıcının yüklediği kısa viral referans videoyu
format ilhamı olarak çöz. Asla bire bir kopyala deme; yapısal blueprint üret.

Sadece geçerli JSON döndür. Şema:
{
  "version": 1,
  "source": {"filename": str, "duration_ms": int, "aspect": "9:16", "fps_hint": number},
  "global_style": {
    "mood": str, "color_grade": str, "transition_default": str,
    "caption_style": {"placement": str, "font_hint": str, "emphasis": str},
    "camera_notes": str
  },
  "scenes": [{
    "id": "s1", "start_ms": int, "end_ms": int, "role": str, "shot": str, "action": str,
    "caption": {"text": str, "start_ms": int, "end_ms": int},
    "gen_video": {"needed": bool, "prompt_hint": str|null},
    "user_clip": {"required": bool, "guidance": str}
  }],
  "audio": {"policy": "user_or_licensed_only", "beat_hints": [str], "tts_optional": false},
  "export": {"targets": ["instagram_reel","tiktok"], "max_duration_ms": 30000}
}

Caption metinleri ilham metni olsun (Türkçe tercih). 3–6 sahne. duration_ms ile hizalı kesimler.
"""


class OpenAIVisionAnalyzer:
    """Vision-LLM hook: sample frames → OpenAI chat completions → Blueprint."""

    name = "openai"

    async def analyze(self, video_path: Path, filename: str) -> Blueprint:
        duration_ms, fps = probe_duration_ms(video_path)
        with tempfile.TemporaryDirectory(prefix="videoart_frames_") as tmp:
            frames = sample_frames(video_path, Path(tmp), count=6)
            if not frames:
                # Fallback if ffmpeg frame extract fails
                return await StubAnalyzer().analyze(video_path, filename)

            content: list[dict] = [
                {
                    "type": "text",
                    "text": (
                        f"Dosya: {filename}. duration_ms≈{duration_ms}, fps≈{fps}. "
                        "Frame’lerden blueprint JSON üret."
                    ),
                }
            ]
            for frame in frames:
                b64 = base64.b64encode(frame.read_bytes()).decode("ascii")
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64}",
                            "detail": "low",
                        },
                    }
                )

            payload = {
                "model": OPENAI_VISION_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.4,
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            raw_text = data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_text)
            if "source" not in parsed or not isinstance(parsed["source"], dict):
                parsed["source"] = {}
            parsed["source"].setdefault("filename", filename)
            parsed["source"].setdefault("duration_ms", duration_ms or 18000)
            parsed["source"].setdefault("aspect", "9:16")
            parsed["source"].setdefault("fps_hint", fps)
            # Ensure SourceInfo filename matches upload
            parsed["source"]["filename"] = filename
            if duration_ms:
                parsed["source"]["duration_ms"] = duration_ms

            return Blueprint.model_validate(parsed)
