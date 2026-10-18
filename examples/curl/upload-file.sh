#!/usr/bin/env bash
# Upload a local file in three calls (ticket, PUT, commit) and print its popnow:// URI.
# Use the URI in a model's media field, e.g. "image_url": "popnow://f/fil_...".
# Usage: ./upload-file.sh photo.png image/png
# Requires: curl, jq
set -euo pipefail
API="${POPNOW_API_BASE:-https://api.popnow.ai}/api/v1"
KEY="${POPNOW_API_KEY:?Set POPNOW_API_KEY to your sk-popnow-... key}"
FILE="${1:?Usage: $0 <file> <content-type>}"
CONTENT_TYPE="${2:?Usage: $0 <file> <content-type>}"
BYTES=$(wc -c < "$FILE" | tr -d ' ')

# 1. Ask for an upload ticket.
TICKET=$(curl -sS -X POST "$API/common/upload-url" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d "{\"contentType\": \"$CONTENT_TYPE\", \"bytes\": $BYTES}")
if [ "$(echo "$TICKET" | jq -r .code)" != "200" ]; then echo "$TICKET" | jq . >&2; exit 1; fi
UPLOAD_URL=$(echo "$TICKET" | jq -r .data.uploadUrl)
FILE_ID=$(echo "$TICKET" | jq -r .data.fileId)

# 2. PUT the bytes with every header from the ticket, and no Authorization header.
HEADER_ARGS=()
while IFS= read -r h; do HEADER_ARGS+=(-H "$h"); done < <(echo "$TICKET" | jq -r '.data.headers | to_entries[] | "\(.key): \(.value)"')
STATUS=$(curl -sS -o /dev/null -w "%{http_code}" -X PUT "$UPLOAD_URL" ${HEADER_ARGS[@]+"${HEADER_ARGS[@]}"} --data-binary @"$FILE")
if [ "${STATUS:0:1}" != "2" ]; then echo "PUT failed with HTTP $STATUS" >&2; exit 1; fi

# 3. Commit: checks size, type and signature, then returns the URI.
curl -sS -X POST "$API/files/$FILE_ID/commit" \
  -H "Authorization: Bearer $KEY" | jq '.data | {uri, contentType, bytes, width, height, expiresAt}'
