#!/usr/bin/env bash
# List every model your key can call, with its price in credits.
# Usage: ./list-models.sh [image|video|audio]
# Requires: curl, jq
set -euo pipefail
API="${POPNOW_API_BASE:-https://api.popnow.ai}/api/v1"
KEY="${POPNOW_API_KEY:?Set POPNOW_API_KEY to your sk-popnow-... key}"

QUERY=""
if [ -n "${1:-}" ]; then QUERY="?modality=$1"; fi

curl -sS "$API/models$QUERY" \
  -H "Authorization: Bearer $KEY" |
  jq -r 'if .code != 200 then error("\(.code) \(.msg) (\(.request_id))") else .data.items[] | "\(.model)\t\(.modality)\t\(.credits)" end'
