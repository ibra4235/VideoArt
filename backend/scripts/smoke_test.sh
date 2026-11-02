#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE_URL:-http://127.0.0.1:8000}"
REF="${1:-/tmp/ref.mp4}"

if [[ ! -f "$REF" ]]; then
  ffmpeg -y -f lavfi -i color=c=orange:s=720x1280:d=4 -c:v libx264 -pix_fmt yuv420p "$REF"
fi

curl -sf "$BASE/health" | python3 -m json.tool
CREATE=$(curl -sf -F "file=@${REF};type=video/mp4" -H "X-User-Id: smoke" "$BASE/v1/jobs/analyze")
JOB_ID=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["job_id"])' <<<"$CREATE")
echo "job_id=$JOB_ID"

for _ in $(seq 1 30); do
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
assert job["blueprint"] and job["blueprint"]["scenes"]
print("SMOKE_OK scenes=", len(job["blueprint"]["scenes"]))
PY
