#!/usr/bin/env bash
# Generate one image and wait for it in the same request (?wait=60).
# Usage: ./text-to-image.sh "A small red fox curled up in a teacup, soft morning light"
# Requires: curl, jq, uuidgen
set -euo pipefail
API="${POPNOW_API_BASE:-https://api.popnow.ai}/api/v1"
KEY="${POPNOW_API_KEY:?Set POPNOW_API_KEY to your sk-popnow-... key}"
PROMPT="${1:-A small red fox curled up in a teacup, soft morning light}"

BODY=$(jq -n --arg prompt "$PROMPT" \
  '{model: "alibaba/z-image-turbo/text-to-image", input: {prompt: $prompt, aspect_ratio: "1:1"}}')

RES=$(curl -sS -X POST "$API/jobs/createTask?wait=60" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d "$BODY")

echo "$RES" | jq '.data | {taskId, state, credits, url: .output.assets[0].url}'
# If state is still "queued" or "running", follow up with ./poll-job.sh <taskId>.
