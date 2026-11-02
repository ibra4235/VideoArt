from __future__ import annotations

import json
from pathlib import Path

import aiofiles

from .config import JOBS_DIR, UPLOADS_DIR, ensure_data_dirs
from .schemas import JobRecord


def job_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


async def save_upload(job_id: str, filename: str, data: bytes) -> Path:
    ensure_data_dirs()
    safe_name = Path(filename).name or "ref.mp4"
    dest = UPLOADS_DIR / f"{job_id}_{safe_name}"
    async with aiofiles.open(dest, "wb") as f:
        await f.write(data)
    return dest


async def write_job(record: JobRecord) -> None:
    ensure_data_dirs()
    path = job_path(record.id)
    tmp = path.with_suffix(".json.tmp")
    payload = record.model_dump(mode="json")
    async with aiofiles.open(tmp, "w", encoding="utf-8") as f:
        await f.write(json.dumps(payload, ensure_ascii=False, indent=2))
    tmp.replace(path)


async def read_job(job_id: str) -> JobRecord | None:
    path = job_path(job_id)
    if not path.is_file() or path.stat().st_size == 0:
        return None
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        raw = await f.read()
    if not raw.strip():
        return None
    return JobRecord.model_validate_json(raw)


def list_job_ids() -> list[str]:
    ensure_data_dirs()
    return sorted(p.stem for p in JOBS_DIR.glob("*.json"))
