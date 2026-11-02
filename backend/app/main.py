from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .analyzers import get_analyzer
from .config import ALLOW_ANONYMOUS, ANALYZER_PROVIDER, UPLOADS_DIR, ensure_data_dirs
from .link_ingest import ingest_link_stub
from .remake import assemble_draft
from .schemas import (
    AnalyzeFromLinkRequest,
    Blueprint,
    BlueprintUpdateRequest,
    JobCreateResponse,
    JobRecord,
    JobResponse,
    ShootGuidance,
)
from .storage import (
    draft_path_for,
    read_job,
    remake_work_dir,
    save_upload,
    save_user_clip,
    write_job,
)

app = FastAPI(
    title="VideoArt API",
    version="0.2.0",
    description=(
        "Link/file → analyze → shoot guidance → user clip → remake draft "
        "(montage + caption burn-in + gen stubs)"
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_user(x_user_id: Optional[str]) -> str:
    if x_user_id and x_user_id.strip():
        return x_user_id.strip()
    if ALLOW_ANONYMOUS:
        return "anonymous"
    raise HTTPException(status_code=401, detail="X-User-Id required (stub auth)")


def _to_response(record: JobRecord) -> JobResponse:
    return JobResponse(
        job_id=record.id,
        status=record.status,
        filename=record.filename,
        error=record.error,
        blueprint=record.blueprint,
        analyzer=record.analyzer,
        source_kind=record.source_kind,
        source_url=record.source_url,
        platform=record.platform,
        ingest_note=record.ingest_note,
        has_user_clip=bool(record.user_clip_path),
        remake=record.remake,
        draft_ready=bool(record.draft_path) and record.status == "draft_ready",
    )


def _enrich_blueprint(
    blueprint: Blueprint,
    *,
    source_kind: str,
    source_url: Optional[str],
    platform: Optional[str],
) -> Blueprint:
    blueprint.source.source_kind = source_kind
    blueprint.source.source_url = source_url
    blueprint.source.platform = platform
    if blueprint.shoot_guidance is None:
        speak = max(8, min(int(round(blueprint.source.duration_ms / 1000.0)) or 15, 30))
        blueprint.shoot_guidance = ShootGuidance(
            instruction=f"Otur, kameraya bak, gülümse, yaklaşık {speak} saniye konuş",
            duration_sec=speak,
        )
    return blueprint


@app.on_event("startup")
async def startup() -> None:
    ensure_data_dirs()


@app.get("/health")
async def health() -> dict:
    return {
        "ok": True,
        "analyzer": ANALYZER_PROVIDER,
        "auth": "stub",
        "features": ["analyze_file", "analyze_link_stub", "user_clip", "remake_ffmpeg"],
        "link_download": "stub_only_tos",
    }


async def _run_analyze(job_id: str) -> None:
    record = await read_job(job_id)
    if record is None:
        return
    record.status = "processing"
    record.updated_at = _now()
    await write_job(record)

    try:
        analyzer = get_analyzer()
        blueprint = await analyzer.analyze(Path(record.video_path), record.filename)
        blueprint = _enrich_blueprint(
            blueprint,
            source_kind=record.source_kind,
            source_url=record.source_url,
            platform=record.platform,
        )
        record.blueprint = blueprint
        record.analyzer = analyzer.name
        record.status = "completed"
        record.error = None
    except Exception as exc:  # noqa: BLE001 — persist failure for client polling
        record.status = "failed"
        record.error = str(exc)
    record.updated_at = _now()
    await write_job(record)


async def _run_remake(job_id: str) -> None:
    record = await read_job(job_id)
    if record is None:
        return
    record.status = "remaking"
    record.updated_at = _now()
    await write_job(record)

    try:
        if not record.blueprint:
            raise RuntimeError("Blueprint yok")
        if not record.user_clip_path or not Path(record.user_clip_path).is_file():
            raise RuntimeError("Kullanıcı klibi yok")
        work = remake_work_dir(job_id)
        draft = draft_path_for(job_id)
        result = assemble_draft(
            record.blueprint,
            Path(record.user_clip_path),
            work,
            draft,
        )
        record.remake = result
        record.draft_path = result.draft_path
        record.status = "draft_ready"
        record.error = None
    except Exception as exc:  # noqa: BLE001
        record.status = "failed"
        record.error = str(exc)
    record.updated_at = _now()
    await write_job(record)


@app.post("/v1/jobs/analyze", response_model=JobCreateResponse)
async def create_analyze_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    x_user_id: Optional[str] = Header(default=None),
) -> JobCreateResponse:
    user_id = _resolve_user(x_user_id)
    filename = file.filename or "ref.mp4"
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Boş dosya")

    job_id = str(uuid.uuid4())
    video_path = await save_upload(job_id, filename, data)
    now = _now()
    record = JobRecord(
        id=job_id,
        status="queued",
        user_id=user_id,
        filename=filename,
        video_path=str(video_path),
        created_at=now,
        updated_at=now,
        analyzer=ANALYZER_PROVIDER,
        source_kind="file",
    )
    await write_job(record)
    background_tasks.add_task(_run_analyze, job_id)
    return JobCreateResponse(job_id=job_id, status="queued")


@app.post("/v1/jobs/analyze-from-link", response_model=JobCreateResponse)
async def create_analyze_from_link(
    body: AnalyzeFromLinkRequest,
    background_tasks: BackgroundTasks,
    x_user_id: Optional[str] = Header(default=None),
) -> JobCreateResponse:
    """Accept IG/TikTok URL. Real download is STUBBED (ToS) — analyzes a placeholder."""
    user_id = _resolve_user(x_user_id)
    job_id = str(uuid.uuid4())
    ensure_data_dirs()
    dest = UPLOADS_DIR / f"{job_id}_link_stub_ref.mp4"
    try:
        result = await ingest_link_stub(body.url, dest)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Link stub başarısız: {exc}") from exc

    now = _now()
    record = JobRecord(
        id=job_id,
        status="queued",
        user_id=user_id,
        filename=f"{result.platform}_link_stub.mp4",
        video_path=str(result.stub_video_path),
        created_at=now,
        updated_at=now,
        analyzer=ANALYZER_PROVIDER,
        source_kind="link_stub",
        source_url=result.normalized_url,
        platform=result.platform,
        ingest_note=result.stub_note,
    )
    await write_job(record)
    background_tasks.add_task(_run_analyze, job_id)
    return JobCreateResponse(
        job_id=job_id,
        status="queued",
        ingest_note=result.stub_note,
    )


@app.get("/v1/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    record = await read_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job bulunamadı")
    return _to_response(record)


@app.put("/v1/jobs/{job_id}/blueprint", response_model=JobResponse)
async def update_blueprint(
    job_id: str,
    body: BlueprintUpdateRequest,
    x_user_id: Optional[str] = Header(default=None),
) -> JobResponse:
    _resolve_user(x_user_id)
    record = await read_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job bulunamadı")
    if record.status not in {"completed", "awaiting_clip", "draft_ready"}:
        raise HTTPException(status_code=409, detail="Blueprint henüz hazır değil")
    try:
        record.blueprint = Blueprint.model_validate(body.blueprint)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Geçersiz blueprint: {exc}") from exc
    record.updated_at = _now()
    await write_job(record)
    return _to_response(record)


@app.post("/v1/jobs/{job_id}/user-clip", response_model=JobResponse)
async def upload_user_clip(
    job_id: str,
    file: UploadFile = File(...),
    x_user_id: Optional[str] = Header(default=None),
) -> JobResponse:
    _resolve_user(x_user_id)
    record = await read_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job bulunamadı")
    if record.blueprint is None or record.status in {"queued", "processing", "failed"}:
        if record.status == "failed":
            raise HTTPException(status_code=409, detail="Önce başarılı analiz gerekli")
        if record.blueprint is None:
            raise HTTPException(status_code=409, detail="Blueprint henüz hazır değil")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Boş klip")
    filename = file.filename or "talking_head.mp4"
    clip_path = await save_user_clip(job_id, filename, data)
    record.user_clip_path = str(clip_path)
    record.user_clip_filename = filename
    # Blueprint remains usable; has_user_clip signals readiness for remake.
    if record.status not in {"draft_ready", "remaking"}:
        record.status = "completed"
    record.error = None
    record.updated_at = _now()
    await write_job(record)
    return _to_response(record)


@app.post("/v1/jobs/{job_id}/remake", response_model=JobResponse)
async def start_remake(
    job_id: str,
    background_tasks: BackgroundTasks,
    x_user_id: Optional[str] = Header(default=None),
) -> JobResponse:
    _resolve_user(x_user_id)
    record = await read_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job bulunamadı")
    if not record.blueprint:
        raise HTTPException(status_code=409, detail="Blueprint yok")
    if not record.user_clip_path:
        raise HTTPException(status_code=409, detail="Önce talking-head klip yükle")
    if record.status == "remaking":
        return _to_response(record)

    record.status = "remaking"
    record.error = None
    record.updated_at = _now()
    await write_job(record)
    background_tasks.add_task(_run_remake, job_id)
    return _to_response(record)


@app.get("/v1/jobs/{job_id}/draft")
async def get_draft(job_id: str) -> FileResponse:
    record = await read_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job bulunamadı")
    path = Path(record.draft_path) if record.draft_path else draft_path_for(job_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Draft henüz yok")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"videoart-draft-{job_id[:8]}.mp4",
    )


# Dev helper: sync analyze without waiting for background (tests)
@app.post("/v1/jobs/{job_id}/analyze-now", include_in_schema=False)
async def analyze_now(job_id: str) -> JobResponse:
    await _run_analyze(job_id)
    record = await read_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job bulunamadı")
    return _to_response(record)


@app.post("/v1/jobs/{job_id}/remake-now", include_in_schema=False)
async def remake_now(job_id: str) -> JobResponse:
    await _run_remake(job_id)
    record = await read_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job bulunamadı")
    return _to_response(record)


def run() -> None:
    import uvicorn

    from .config import HOST, PORT

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)


if __name__ == "__main__":
    run()
