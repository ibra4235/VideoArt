# VideoArt

iOS-first **format inspiration / your own content** app.

Upload a short viral reference video file → AI analyzes a **blueprint JSON** (scenes, captions, style) → review & edit captions. Remake / gen video / StoreKit are **out of this slice**.

## Repo layout

```
backend/          FastAPI — upload, analyze job, blueprint persist
ios/VideoArt/     SwiftUI app — picker → analyze → blueprint review
```

## Prerequisites

- **Backend:** Python 3.10+, `ffmpeg` / `ffprobe` (for duration + optional OpenAI frame sampling)
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
| `DATA_DIR` | `./data` | Uploads + job JSON |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Uvicorn bind |
| `ALLOW_ANONYMOUS` | `true` | Stub auth; clients may send `X-User-Id` |

### API (this slice)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness + active analyzer |
| `POST` | `/v1/jobs/analyze` | Multipart `file` → create analyze job |
| `GET` | `/v1/jobs/{id}` | Poll status + blueprint |
| `PUT` | `/v1/jobs/{id}/blueprint` | Persist edited blueprint JSON |

Blueprint schema matches the MVP doc (`version`, `source`, `global_style`, `scenes[]`, `audio`, `export`).

### Smoke test without iOS

```bash
# with server running:
curl -s http://127.0.0.1:8000/health
# create a tiny test mp4 via ffmpeg, then:
ffmpeg -y -f lavfi -i color=c=black:s=720x1280:d=3 -c:v libx264 -pix_fmt yuv420p /tmp/ref.mp4
curl -s -F "file=@/tmp/ref.mp4" http://127.0.0.1:8000/v1/jobs/analyze
# poll returned job_id until status=completed
```

## iOS app (local)

1. Start the backend (above).
2. Open `ios/VideoArt/VideoArt.xcodeproj` in Xcode.
3. Set your **Team** for signing (`PRODUCT_BUNDLE_IDENTIFIER` = `com.videoart.app`).
4. **Simulator:** `APIClient.baseURL` defaults to `http://127.0.0.1:8000` (works when backend runs on the same Mac).
5. **Physical device:** change `APIClient.baseURL` in `ios/VideoArt/VideoArt/Services/APIClient.swift` to your Mac’s LAN IP (e.g. `http://192.168.x.x:8000`).
6. Run → Hoş geldin → referans seç (Photos/Files) → analiz → blueprint’te caption düzenle → Kaydet.

Turkish UI copy is intentional for this slice.

## What works vs stubbed

| Area | Status |
|------|--------|
| Upload reference video | Works (Photos + Files) |
| Analyze job + persist blueprint | Works (local JSON files) |
| Stub analyzer (no API key) | Works — duration-scaled sample scenes |
| OpenAI vision analyzer | Hook ready — set `ANALYZER_PROVIDER=openai` + `OPENAI_API_KEY` |
| Blueprint review + caption edit + save | Works |
| Auth | Stub (`X-User-Id` / anonymous) — no Sign in with Apple |
| S3 / Postgres / queue workers | Not in slice (local disk) |
| Gen video, montage, caption burn-in | Stubbed / skipped |
| StoreKit / pricing | Skipped |

## Product language

Do not market as “clone”. Positioning: **format inspiration / your own content**. Caption fields are shown as *ilham metni*.

## Next slices (not here)

User clips → gen video provider → FFmpeg assemble + captions → export → StoreKit.
