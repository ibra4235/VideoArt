from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import aiofiles

from .config import EVENTS_DIR, EVENTS_FILE, ensure_data_dirs

_lock = asyncio.Lock()

# Canonical client/server event names for MVP founder visibility.
KNOWN_EVENT_NAMES = frozenset(
    {
        "app_open",
        "link_submit",
        "file_upload",
        "analyze_start",
        "analyze_complete",
        "shoot_guidance_view",
        "clip_upload",
        "remake_start",
        "remake_complete",
        "export_share",
        "error",
    }
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _events_path() -> Path:
    ensure_data_dirs()
    return EVENTS_FILE


async def append_event(
    *,
    event_name: str,
    user_id: str = "anonymous",
    job_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    timestamp: Optional[str] = None,
) -> dict[str, Any]:
    """Append one JSONL event. Fire-and-forget safe; never raises to callers if wrapped."""
    record = {
        "id": str(uuid.uuid4()),
        "user_id": (user_id or "anonymous").strip() or "anonymous",
        "event_name": event_name.strip(),
        "timestamp": timestamp or _now(),
        "job_id": job_id,
        "metadata": metadata or {},
    }
    line = json.dumps(record, ensure_ascii=False) + "\n"
    path = _events_path()
    async with _lock:
        async with aiofiles.open(path, "a", encoding="utf-8") as f:
            await f.write(line)
    return record


async def list_events(*, limit: int = 200, event_name: Optional[str] = None) -> list[dict[str, Any]]:
    """Return newest-first events (up to limit)."""
    path = _events_path()
    if not path.is_file() or path.stat().st_size == 0:
        return []

    async with _lock:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            raw = await f.read()

    rows: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event_name and obj.get("event_name") != event_name:
            continue
        rows.append(obj)

    rows.reverse()  # newest last on disk → newest first
    if limit > 0:
        rows = rows[:limit]
    return rows


async def event_count() -> int:
    path = _events_path()
    if not path.is_file():
        return 0
    async with _lock:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            raw = await f.read()
    return sum(1 for line in raw.splitlines() if line.strip())
