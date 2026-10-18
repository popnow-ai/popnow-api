#!/usr/bin/env bash
# Price a task before running it. Nothing is created and nothing is held.
# The quote is valid for five minutes; pass quoteId and expectedCredits to createTask
# to make sure the price you showed is the price that is held.
# Requires: curl, jq
set -euo pipefail
API="${POPNOW_API_BASE:-https://api.popnow.ai}/api/v1"
KEY="${POPNOW_API_KEY:?Set POPNOW_API_KEY to your sk-popnow-... key}"

curl -sS -X POST "$API/jobs/quote" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "alibaba/wan-3.0/image-to-video",
    "input": {
      "image_url": "https://media.popnow.ai/movie/lighthouse.webp",
      "prompt": "Waves roll in slowly, the camera drifts toward the lighthouse",
      "resolution": "480p",
      "duration_seconds": 5
    }
  }' | jq '.data | {quoteId, model, maxCredits, expectedCredits, maxCharge, expiresAt}'
