from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class CaptionStyle(BaseModel):
    placement: str = "center_lower"
    font_hint: str = "bold_sans"
    emphasis: str = "word_highlight"


class GlobalStyle(BaseModel):
    mood: str = "energetic"
    color_grade: str = "high-contrast warm"
    transition_default: str = "hard_cut"
    caption_style: CaptionStyle = Field(default_factory=CaptionStyle)
    camera_notes: str = "handheld close-ups, quick push-ins"


class SourceInfo(BaseModel):
    filename: str
    duration_ms: int = 0
    aspect: str = "9:16"
    fps_hint: float = 30.0
    source_kind: str = "file"  # file | link_stub
    source_url: Optional[str] = None
    platform: Optional[str] = None


class SceneCaption(BaseModel):
    text: str
    start_ms: int
    end_ms: int


class GenVideo(BaseModel):
    needed: bool = False
    prompt_hint: Optional[str] = None


class UserClip(BaseModel):
    required: bool = True
    guidance: str = ""


class Scene(BaseModel):
    id: str
    start_ms: int
    end_ms: int
    role: str = "body"
    shot: str = ""
    action: str = ""
    caption: SceneCaption
    gen_video: GenVideo = Field(default_factory=GenVideo)
    user_clip: UserClip = Field(default_factory=UserClip)


class AudioInfo(BaseModel):
    policy: str = "user_or_licensed_only"
    beat_hints: list[str] = Field(default_factory=lambda: ["cut_on_energy_peaks"])
    tts_optional: bool = False


class ExportInfo(BaseModel):
    targets: list[str] = Field(default_factory=lambda: ["instagram_reel", "tiktok"])
    max_duration_ms: int = 30000


class ShootGuidance(BaseModel):
    """Flat single-take guidance — user records one plain talking-head clip."""

    mode: str = "flat_talking_head"
    title: str = "Tek plan çekim"
    instruction: str = "Otur, kameraya bak, gülümse, konuş"
    duration_sec: int = 15
    tips: list[str] = Field(
        default_factory=lambda: [
            "Telefonu dikey tut (9:16)",
            "Yüzün çerçevede net görünsün",
            "Arka plan sade olsun",
            "Kendi cümlelerinle konuş — metni ezberleme",
        ]
    )


class Blueprint(BaseModel):
    version: int = 1
    source: SourceInfo
    global_style: GlobalStyle = Field(default_factory=GlobalStyle)
    scenes: list[Scene] = Field(default_factory=list)
    audio: AudioInfo = Field(default_factory=AudioInfo)
    export: ExportInfo = Field(default_factory=ExportInfo)
    shoot_guidance: ShootGuidance = Field(default_factory=ShootGuidance)


JobStatus = Literal[
    "queued",
    "processing",
    "completed",
    "failed",
    "awaiting_clip",
    "remaking",
    "draft_ready",
]


class RemakeResult(BaseModel):
    draft_path: str
    duration_ms: int = 0
    gen_stub_scenes: list[str] = Field(default_factory=list)
    montage: str = "ffmpeg_concat_zoompan"
    captions: str = "drawtext_burn_in"
    note: str = ""


class JobRecord(BaseModel):
    id: str
    status: JobStatus
    user_id: str = "anonymous"
    filename: str
    video_path: str
    created_at: str
    updated_at: str
    error: Optional[str] = None
    blueprint: Optional[Blueprint] = None
    analyzer: str = "stub"
    source_kind: str = "file"  # file | link_stub
    source_url: Optional[str] = None
    platform: Optional[str] = None
    ingest_note: Optional[str] = None
    user_clip_path: Optional[str] = None
    user_clip_filename: Optional[str] = None
    remake: Optional[RemakeResult] = None
    draft_path: Optional[str] = None


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus
    ingest_note: Optional[str] = None


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    filename: str
    error: Optional[str] = None
    blueprint: Optional[Blueprint] = None
    analyzer: str = "stub"
    source_kind: str = "file"
    source_url: Optional[str] = None
    platform: Optional[str] = None
    ingest_note: Optional[str] = None
    has_user_clip: bool = False
    remake: Optional[RemakeResult] = None
    draft_ready: bool = False


class BlueprintUpdateRequest(BaseModel):
    """Partial blueprint update — clients typically patch scene captions."""

    blueprint: dict[str, Any]


class AnalyzeFromLinkRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=2048)
