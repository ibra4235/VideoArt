from __future__ import annotations

import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def load_dotenv_if_present() -> None:
    env_path = BACKEND_ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_dotenv_if_present()

ANALYZER_PROVIDER = _env("ANALYZER_PROVIDER", "stub").lower() or "stub"
OPENAI_API_KEY = _env("OPENAI_API_KEY")
OPENAI_VISION_MODEL = _env("OPENAI_VISION_MODEL", "gpt-4o") or "gpt-4o"

_raw_data = _env("DATA_DIR", "./data") or "./data"
DATA_DIR = Path(_raw_data)
if not DATA_DIR.is_absolute():
    DATA_DIR = (BACKEND_ROOT / DATA_DIR).resolve()

UPLOADS_DIR = DATA_DIR / "uploads"
JOBS_DIR = DATA_DIR / "jobs"
HOST = _env("HOST", "0.0.0.0") or "0.0.0.0"
PORT = int(_env("PORT", "8000") or "8000")
ALLOW_ANONYMOUS = _env("ALLOW_ANONYMOUS", "true").lower() in {"1", "true", "yes"}


def ensure_data_dirs() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
