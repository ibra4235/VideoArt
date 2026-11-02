from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .analyzers import get_analyzer
from .config import ALLOW_ANONYMOUS, ANALYZER_PROVIDER, ensure_data_dirs
from .schemas import Blueprint, BlueprintUpdateRequest, JobCreateResponse, JobRecord, JobResponse
from .storage import read_job, write_job, save_upload

app = FastAPI(
    title="VideoArt API",
    version="0.1.0",
    description="Upload → analyze → blueprint JSON (vertical slice)",
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


@app.on_event("startup")
async def startup() -> None:
    ensure_data_dirs()


@app.get("/health")
async def health() -> dict:
    return {
        "ok": True,
        "analyzer": ANALYZER_PROVIDER,
        "auth": "stub",
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
        from pathlib import Path

        blueprint = await analyzer.analyze(Path(record.video_path), record.filename)
        record.blueprint = blueprint
        record.analyzer = analyzer.name
        record.status = "completed"
        record.error = None
    except Exception as exc:  # noqa: BLE001 — persist failure for client polling
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
    content_type = (file.content_type or "").lower()
    if content_type and not (
        content_type.startswith("video/")
        or content_type in {"application/octet-stream", "application/mp4"}
    ):
        # Soft check — Photos/Files may send odd types
        pass

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
    )
    await write_job(record)
    background_tasks.add_task(_run_analyze, job_id)
    return JobCreateResponse(job_id=job_id, status="queued")


@app.get("/v1/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    record = await read_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job bulunamadı")
    return JobResponse(
        job_id=record.id,
        status=record.status,
        filename=record.filename,
        error=record.error,
        blueprint=record.blueprint,
        analyzer=record.analyzer,
    )


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
    if record.status != "completed":
        raise HTTPException(status_code=409, detail="Blueprint henüz hazır değil")
    try:
        record.blueprint = Blueprint.model_validate(body.blueprint)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Geçersiz blueprint: {exc}") from exc
    record.updated_at = _now()
    await write_job(record)
    return JobResponse(
        job_id=record.id,
        status=record.status,
        filename=record.filename,
        error=record.error,
        blueprint=record.blueprint,
        analyzer=record.analyzer,
    )


# Dev helper: sync analyze without waiting for background (tests)
@app.post("/v1/jobs/{job_id}/analyze-now", include_in_schema=False)
async def analyze_now(job_id: str) -> JobResponse:
    await _run_analyze(job_id)
    record = await read_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job bulunamadı")
    return JobResponse(
        job_id=record.id,
        status=record.status,
        filename=record.filename,
        error=record.error,
        blueprint=record.blueprint,
        analyzer=record.analyzer,
    )


def run() -> None:
    import uvicorn

    from .config import HOST, PORT

    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)


if __name__ == "__main__":
    run()
