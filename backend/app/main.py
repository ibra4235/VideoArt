from __future__ import annotations

import html
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import BackgroundTasks, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from .analyzers import get_analyzer
from .config import (
    ADMIN_TOKEN,
    ALLOW_ANONYMOUS,
    ANALYZER_PROVIDER,
    UPLOADS_DIR,
    ensure_data_dirs,
)
from .events import append_event, event_count, list_events
from .link_ingest import ingest_link_stub
from .remake import assemble_draft
from .schemas import (
    AnalyzeFromLinkRequest,
    Blueprint,
    BlueprintUpdateRequest,
    EventCreateRequest,
    EventCreateResponse,
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
    version="0.3.0",
    description=(
        "Link/file → analyze → shoot guidance → user clip → remake draft "
        "(montage + caption burn-in + gen stubs). In-house usage events for founder."
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


def _require_admin(
    x_admin_token: Optional[str] = None,
    token_query: Optional[str] = None,
) -> None:
    provided = (x_admin_token or token_query or "").strip()
    if not provided or provided != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Admin token required (X-Admin-Token)")


async def _safe_log(
    event_name: str,
    *,
    user_id: str = "anonymous",
    job_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    try:
        await append_event(
            event_name=event_name,
            user_id=user_id,
            job_id=job_id,
            metadata=metadata,
        )
    except Exception:  # noqa: BLE001 — never break product paths for analytics
        pass


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
        "features": [
            "analyze_file",
            "analyze_link_stub",
            "user_clip",
            "remake_ffmpeg",
            "usage_events",
        ],
        "link_download": "stub_only_tos",
    }


async def _run_analyze(job_id: str) -> None:
    record = await read_job(job_id)
    if record is None:
        return
    record.status = "processing"
    record.updated_at = _now()
    await write_job(record)
    await _safe_log(
        "analyze_start",
        user_id=record.user_id,
        job_id=job_id,
        metadata={"source_kind": record.source_kind, "source": "server"},
    )

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
        await _safe_log(
            "analyze_complete",
            user_id=record.user_id,
            job_id=job_id,
            metadata={
                "analyzer": analyzer.name,
                "scenes": len(blueprint.scenes),
                "source": "server",
            },
        )
    except Exception as exc:  # noqa: BLE001 — persist failure for client polling
        record.status = "failed"
        record.error = str(exc)
        await _safe_log(
            "error",
            user_id=record.user_id,
            job_id=job_id,
            metadata={"stage": "analyze", "message": str(exc), "source": "server"},
        )
    record.updated_at = _now()
    await write_job(record)


async def _run_remake(job_id: str) -> None:
    record = await read_job(job_id)
    if record is None:
        return
    record.status = "remaking"
    record.updated_at = _now()
    await write_job(record)
    await _safe_log(
        "remake_start",
        user_id=record.user_id,
        job_id=job_id,
        metadata={"source": "server"},
    )

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
        await _safe_log(
            "remake_complete",
            user_id=record.user_id,
            job_id=job_id,
            metadata={
                "duration_ms": result.duration_ms,
                "gen_stub_scenes": result.gen_stub_scenes,
                "source": "server",
            },
        )
    except Exception as exc:  # noqa: BLE001
        record.status = "failed"
        record.error = str(exc)
        await _safe_log(
            "error",
            user_id=record.user_id,
            job_id=job_id,
            metadata={"stage": "remake", "message": str(exc), "source": "server"},
        )
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
    await _safe_log(
        "file_upload",
        user_id=user_id,
        job_id=job_id,
        metadata={"filename": filename, "bytes": len(data), "source": "server"},
    )
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
    await _safe_log(
        "link_submit",
        user_id=user_id,
        job_id=job_id,
        metadata={
            "platform": result.platform,
            "source": "server",
        },
    )
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
    await _safe_log(
        "clip_upload",
        user_id=record.user_id,
        job_id=job_id,
        metadata={"filename": filename, "bytes": len(data), "source": "server"},
    )
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


@app.post("/v1/events", response_model=EventCreateResponse)
async def create_event(
    body: EventCreateRequest,
    x_user_id: Optional[str] = Header(default=None),
) -> EventCreateResponse:
    """Fire-and-forget client analytics. Always 200 when persisted; soft-fail never."""
    user_id = _resolve_user(x_user_id)
    name = body.event_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="event_name required")
    record = await append_event(
        event_name=name,
        user_id=user_id,
        job_id=body.job_id,
        metadata=body.metadata or {},
        timestamp=body.timestamp,
    )
    return EventCreateResponse(ok=True, id=record["id"], event_name=record["event_name"])


def _render_admin_html(events: list[dict[str, Any]], total: int, limit: int) -> str:
    rows = []
    for ev in events:
        meta = ev.get("metadata") or {}
        meta_s = html.escape(str(meta)[:240])
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(ev.get('timestamp', '')))}</td>"
            f"<td><code>{html.escape(str(ev.get('event_name', '')))}</code></td>"
            f"<td>{html.escape(str(ev.get('user_id', '')))}</td>"
            f"<td><code>{html.escape(str(ev.get('job_id') or '—'))}</code></td>"
            f"<td class='meta'>{meta_s}</td>"
            "</tr>"
        )
    body_rows = "\n".join(rows) if rows else (
        "<tr><td colspan='5'>Henüz olay yok. iOS veya "
        "<code>POST /v1/events</code> ile yaz.</td></tr>"
    )
    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>VideoArt · Events</title>
  <style>
    :root {{
      --bg: #0f1419;
      --card: #1a222c;
      --text: #e8eef4;
      --muted: #8b9aab;
      --accent: #33d9a0;
      --line: #2a3542;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; padding: 24px;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif;
      background: linear-gradient(160deg, #0f1419, #12201c 50%, #0f1419);
      color: var(--text); min-height: 100vh;
    }}
    h1 {{ margin: 0 0 4px; font-size: 1.6rem; }}
    .sub {{ color: var(--muted); margin-bottom: 20px; font-size: 0.95rem; }}
    .pill {{
      display: inline-block; background: var(--card); border: 1px solid var(--line);
      padding: 4px 10px; border-radius: 999px; color: var(--accent); font-size: 0.85rem;
      margin-right: 8px;
    }}
    table {{
      width: 100%; border-collapse: collapse; background: var(--card);
      border: 1px solid var(--line); border-radius: 12px; overflow: hidden;
    }}
    th, td {{
      text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--line);
      vertical-align: top; font-size: 0.9rem;
    }}
    th {{ color: var(--muted); font-weight: 600; background: #141b24; }}
    tr:last-child td {{ border-bottom: none; }}
    code {{ color: var(--accent); }}
    .meta {{ color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.78rem; word-break: break-all; }}
    a {{ color: var(--accent); }}
  </style>
</head>
<body>
  <h1>VideoArt events</h1>
  <p class="sub">Founder görünümü · son {limit} olay (toplam ~{total}). JSON:
    <a href="/admin/events.json">/admin/events.json</a></p>
  <p><span class="pill">ADMIN_TOKEN korumalı</span>
     <span class="pill">JSONL store</span></p>
  <table>
    <thead>
      <tr><th>Timestamp</th><th>Event</th><th>User</th><th>Job</th><th>Metadata</th></tr>
    </thead>
    <tbody>
      {body_rows}
    </tbody>
  </table>
</body>
</html>"""


@app.get("/admin/events", response_class=HTMLResponse)
async def admin_events_html(
    limit: int = Query(default=200, ge=1, le=2000),
    event_name: Optional[str] = Query(default=None),
    x_admin_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> HTMLResponse:
    _require_admin(x_admin_token, token)
    events = await list_events(limit=limit, event_name=event_name)
    total = await event_count()
    return HTMLResponse(_render_admin_html(events, total, limit))


@app.get("/admin/events.json")
async def admin_events_json(
    limit: int = Query(default=200, ge=1, le=2000),
    event_name: Optional[str] = Query(default=None),
    x_admin_token: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> JSONResponse:
    _require_admin(x_admin_token, token)
    events = await list_events(limit=limit, event_name=event_name)
    total = await event_count()
    return JSONResponse({"ok": True, "total": total, "count": len(events), "events": events})


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
