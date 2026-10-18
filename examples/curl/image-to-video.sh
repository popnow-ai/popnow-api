#!/usr/bin/env bash
# Animate an image into a 5-second video. Video takes longer than 60 seconds,
# so this creates the task and then polls recordInfo until it is final.
# Usage: ./image-to-video.sh [image_url] [prompt]
# Requires: curl, jq, uuidgen
set -euo pipefail
API="${POPNOW_API_BASE:-https://api.popnow.ai}/api/v1"
KEY="${POPNOW_API_KEY:?Set POPNOW_API_KEY to your sk-popnow-... key}"
IMAGE="${1:-https://media.popnow.ai/movie/lighthouse.webp}"
PROMPT="${2:-Waves roll in slowly, the camera drifts toward the lighthouse}"

BODY=$(jq -n --arg image "$IMAGE" --arg prompt "$PROMPT" '{
  model: "alibaba/wan-3.0/image-to-video",
  input: {image_url: $image, prompt: $prompt, resolution: "480p", duration_seconds: 5}
}')

# Generate the idempotency key once and reuse it if you retry this request.
CREATED=$(curl -sS -X POST "$API/jobs/createTask" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d "$BODY")

if [ "$(echo "$CREATED" | jq -r .code)" != "200" ]; then
  echo "$CREATED" | jq . >&2
  exit 1
fi
TASK_ID=$(echo "$CREATED" | jq -r .data.taskId)
echo "Created $TASK_ID (holding $(echo "$CREATED" | jq -r .data.estimatedCredits) credits)" >&2

exec "$(dirname "$0")/poll-job.sh" "$TASK_ID"
