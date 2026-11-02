#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE_URL:-http://127.0.0.1:8000}"
REF="${1:-/tmp/ref.mp4}"
CLIP="${2:-/tmp/talking_head.mp4}"

if [[ ! -f "$REF" ]]; then
  ffmpeg -y -f lavfi -i color=c=orange:s=720x1280:d=4 -c:v libx264 -pix_fmt yuv420p "$REF"
fi
if [[ ! -f "$CLIP" ]]; then
  ffmpeg -y -f lavfi -i color=c=teal:s=720x1280:d=12 \
    -f lavfi -i sine=f=440:d=12 \
    -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "$CLIP"
fi

echo "== health =="
curl -sf "$BASE/health" | python3 -m json.tool

echo "== analyze file =="
CREATE=$(curl -sf -F "file=@${REF};type=video/mp4" -H "X-User-Id: smoke" "$BASE/v1/jobs/analyze")
JOB_ID=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])' <<<"$CREATE")
echo "job_id=$JOB_ID"

for _ in $(seq 1 40); do
  JOB=$(curl -sf "$BASE/v1/jobs/$JOB_ID")
  STATUS=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' <<<"$JOB")
  echo "status=$STATUS"
  [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]] && break
  sleep 0.4
done

python3 - "$JOB" <<'PY'
import json, sys
job = json.loads(sys.argv[1])
assert job["status"] == "completed", job
bp = job["blueprint"]
assert bp and bp["scenes"]
assert "shoot_guidance" in bp
print("SMOKE_OK file analyze scenes=", len(bp["scenes"]), "speak=", bp["shoot_guidance"]["duration_sec"])
PY

echo "== analyze-from-link stub =="
LINK_CREATE=$(curl -sf -H "Content-Type: application/json" -H "X-User-Id: smoke" \
  -d '{"url":"https://www.instagram.com/reel/SMOKETEST123/"}' \
  "$BASE/v1/jobs/analyze-from-link")
LINK_JOB=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])' <<<"$LINK_CREATE")
echo "link_job_id=$LINK_JOB note=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("ingest_note","")[:80])' <<<"$LINK_CREATE")"
for _ in $(seq 1 40); do
  LJOB=$(curl -sf "$BASE/v1/jobs/$LINK_JOB")
  LSTATUS=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' <<<"$LJOB")
  echo "link_status=$LSTATUS"
  [[ "$LSTATUS" == "completed" || "$LSTATUS" == "failed" ]] && break
  sleep 0.4
done
python3 - "$LJOB" <<'PY'
import json, sys
job = json.loads(sys.argv[1])
assert job["status"] == "completed", job
assert job.get("source_kind") == "link_stub"
assert job["blueprint"]["shoot_guidance"]
print("SMOKE_OK link stub analyze platform=", job.get("platform"))
PY

echo "== user-clip + remake =="
curl -sf -F "file=@${CLIP};type=video/mp4" -H "X-User-Id: smoke" \
  "$BASE/v1/jobs/$JOB_ID/user-clip" | python3 -m json.tool >/tmp/va_clip.json
curl -sf -X POST -H "X-User-Id: smoke" "$BASE/v1/jobs/$JOB_ID/remake" | python3 -m json.tool >/tmp/va_remake.json

for _ in $(seq 1 90); do
  RJOB=$(curl -sf "$BASE/v1/jobs/$JOB_ID")
  RSTATUS=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' <<<"$RJOB")
  echo "remake_status=$RSTATUS"
  [[ "$RSTATUS" == "draft_ready" || "$RSTATUS" == "failed" ]] && break
  sleep 0.8
done

python3 - "$RJOB" <<'PY'
import json, sys
job = json.loads(sys.argv[1])
assert job["status"] == "draft_ready", job
assert job.get("draft_ready") is True
assert job.get("remake")
print("SMOKE_OK remake gen_stubs=", job["remake"].get("gen_stub_scenes"), "ms=", job["remake"].get("duration_ms"))
PY

OUT=/tmp/videoart-draft-smoke.mp4
curl -sf -o "$OUT" "$BASE/v1/jobs/$JOB_ID/draft"
ls -la "$OUT"
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT"
echo "SMOKE_ALL_OK"
