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


class Blueprint(BaseModel):
    version: int = 1
    source: SourceInfo
    global_style: GlobalStyle = Field(default_factory=GlobalStyle)
    scenes: list[Scene] = Field(default_factory=list)
    audio: AudioInfo = Field(default_factory=AudioInfo)
    export: ExportInfo = Field(default_factory=ExportInfo)


JobStatus = Literal["queued", "processing", "completed", "failed"]


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


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    filename: str
    error: Optional[str] = None
    blueprint: Optional[Blueprint] = None
    analyzer: str = "stub"


class BlueprintUpdateRequest(BaseModel):
    """Partial blueprint update — clients typically patch scene captions."""

    blueprint: dict[str, Any]
