from __future__ import annotations

from pathlib import Path

from ..schemas import (
    AudioInfo,
    Blueprint,
    CaptionStyle,
    ExportInfo,
    GenVideo,
    GlobalStyle,
    Scene,
    SceneCaption,
    SourceInfo,
    UserClip,
)
from .media import probe_duration_ms


class StubAnalyzer:
    """Deterministic mock analyzer — no API keys required."""

    name = "stub"

    async def analyze(self, video_path: Path, filename: str) -> Blueprint:
        duration_ms, fps = probe_duration_ms(video_path)
        if duration_ms <= 0:
            duration_ms = 18000

        # Scale sample scene cuts to video length (cap at 30s for export)
        usable = min(duration_ms, 30000)
        cuts = [0, int(usable * 0.14), int(usable * 0.39), int(usable * 0.72), usable]
        roles = ["hook", "demo", "proof", "cta"]
        shots = [
            "close_up_face_or_product",
            "over_shoulder / process",
            "detail insert",
            "wide or reaction",
        ]
        actions = [
            "direct address / reveal start",
            "adım adım gösterim",
            "sonuç / sosyal kanıt",
            "kapanış çağrısı",
        ]
        captions = [
            "Bunu denemeden geçme",
            "3 saniyede hazır",
            "İşte fark",
            "Sen de dene",
        ]
        guidances = [
            "Yüz veya ürün close-up, 2–3 sn",
            "İşlemi gösteren orta plan",
            "Detay veya sonuç close-up",
            "Kamera bakışı / CTA jesti",
        ]

        scenes: list[Scene] = []
        for i in range(4):
            start_ms = cuts[i]
            end_ms = cuts[i + 1]
            cap_start = start_ms + min(200, max(0, (end_ms - start_ms) // 10))
            scenes.append(
                Scene(
                    id=f"s{i + 1}",
                    start_ms=start_ms,
                    end_ms=end_ms,
                    role=roles[i],
                    shot=shots[i],
                    action=actions[i],
                    caption=SceneCaption(
                        text=captions[i],
                        start_ms=cap_start,
                        end_ms=end_ms - 100 if end_ms - 100 > cap_start else end_ms,
                    ),
                    gen_video=GenVideo(
                        needed=(i == 1),
                        prompt_hint=(
                            "B-roll: same mood, product texture detail, 9:16"
                            if i == 1
                            else None
                        ),
                    ),
                    user_clip=UserClip(required=True, guidance=guidances[i]),
                )
            )

        return Blueprint(
            version=1,
            source=SourceInfo(
                filename=filename,
                duration_ms=duration_ms,
                aspect="9:16",
                fps_hint=fps,
            ),
            global_style=GlobalStyle(
                mood="energetic",
                color_grade="high-contrast warm",
                transition_default="hard_cut",
                caption_style=CaptionStyle(
                    placement="center_lower",
                    font_hint="bold_sans",
                    emphasis="word_highlight",
                ),
                camera_notes="handheld close-ups, quick push-ins",
            ),
            scenes=scenes,
            audio=AudioInfo(
                policy="user_or_licensed_only",
                beat_hints=["cut_on_energy_peaks"],
                tts_optional=False,
            ),
            export=ExportInfo(
                targets=["instagram_reel", "tiktok"],
                max_duration_ms=30000,
            ),
        )
