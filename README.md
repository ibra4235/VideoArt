# VideoArt

iOS-first **format inspiration / your own content** app.

**Flow (this slice):** paste Instagram/TikTok link *(or file backup)* → analyze → blueprint → flat talking-head shoot guidance → record one clip → remake (montage + caption burn-in + gen stubs) → preview / share.

## Repo layout

```
backend/          FastAPI — link/file analyze, user clip, FFmpeg remake draft
ios/VideoArt/     SwiftUI — link → guidance → capture → remake → preview
```

## Prerequisites

- **Backend:** Python 3.10+, `ffmpeg` / `ffprobe`
- **iOS:** Xcode 15+, iOS 17 SDK, Mac (Simulator or device)

## Backend (local)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional; stub analyzer works with no keys
python -m app
# → http://127.0.0.1:8000
# docs: http://127.0.0.1:8000/docs
```

### Environment variables

| Var | Default | Notes |
|-----|---------|--------|
| `ANALYZER_PROVIDER` | `stub` | `stub` or `openai` |
| `OPENAI_API_KEY` | — | Required when provider=`openai` |
| `OPENAI_VISION_MODEL` | `gpt-4o` | Vision chat model |
| `DATA_DIR` | `./data` | Uploads, clips, outputs, job JSON |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Uvicorn bind |
| `ALLOW_ANONYMOUS` | `true` | Stub auth; clients may send `X-User-Id` |

### API (this slice)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness + features |
| `POST` | `/v1/jobs/analyze` | Multipart `file` → analyze job |
| `POST` | `/v1/jobs/analyze-from-link` | JSON `{url}` → **stub** link ingest + analyze |
| `GET` | `/v1/jobs/{id}` | Poll status + blueprint + remake meta |
| `PUT` | `/v1/jobs/{id}/blueprint` | Persist edited blueprint JSON |
| `POST` | `/v1/jobs/{id}/user-clip` | Multipart talking-head clip |
| `POST` | `/v1/jobs/{id}/remake` | Queue FFmpeg montage + captions + gen stubs |
| `GET` | `/v1/jobs/{id}/draft` | Download draft MP4 |

### Smoke test without iOS

```bash
# with server running:
bash backend/scripts/smoke_test.sh
```

## iOS app (local)

1. Start the backend (above).
2. Open `ios/VideoArt/VideoArt.xcodeproj` in Xcode.
3. Set your **Team** for signing (`PRODUCT_BUNDLE_IDENTIFIER` = `com.videoart.app`).
4. **Simulator:** `APIClient.baseURL` defaults to `http://127.0.0.1:8000`. Camera unavailable → use Photos/Files for the talking-head clip.
5. **Physical device:** set `APIClient.baseURL` to your Mac’s LAN IP.
6. Run → link veya dosya → blueprint → çekim rehberi → klip → remake → önizle / paylaş.

Turkish UI copy is intentional for this slice.

## What works vs stubbed

| Area | Status |
|------|--------|
| Paste IG/TikTok link | Works as **interface + stub** — validates host, synthesizes placeholder reference (no scrape) |
| File upload backup | Works (Photos + Files) |
| Analyze → blueprint + `shoot_guidance` | Works (stub analyzer; OpenAI hook optional) |
| Flat shoot guidance UI | Works — “otur, bak, gülümse, N sn konuş” |
| Talking-head capture | Works — camera (device) / Photos / Files |
| Remake montage + mild zoompan | Works (FFmpeg) |
| Caption burn-in | Works when ffmpeg `drawtext` available; else concat without burn-in |
| Generative video | **Stub** labeled B-roll clips (no API key) |
| Preview + ShareLink export | Works (local draft file) |
| Auth / StoreKit / S3 / Postgres | Stubbed / skipped |

## Limits — Instagram / TikTok ToS

- VideoArt does **not** scrape or download Instagram/TikTok CDN media in this codebase.
- `analyze-from-link` is a **developer stub** so the product flow can be tested end-to-end. Production must use: user-provided files, Share Extension, or a **licensed / official** API if one exists.
- Do not market as a “clone” bot. Positioning: **format inspiration / your own content**.
- Do not copy original platform music tracks into remakes; audio policy = `user_or_licensed_only`.

## Product language

Do not market as “clone”. Caption fields are *ilham metni*.

## Out of this slice

Sign in with Apple, StoreKit pricing, real gen-video vendor, S3/Postgres/queue workers, Share Extension.
