#!/usr/bin/env bash
# Verify a task callback signature offline, e.g. against a delivery you saved while debugging.
#   signature = base64( HMAC-SHA256( secret, "<taskId>.<timestamp>.<sha256_hex(raw_body)>" ) )
# Usage: POPNOW_WEBHOOK_SECRET=... ./webhook-verify.sh body.json <X-Webhook-Timestamp> <X-Webhook-Signature>
# Requires: openssl, jq
# For a real receiver, see ../python/webhook_receiver.py or ../node/webhook-receiver.mjs.
set -euo pipefail
SECRET="${POPNOW_WEBHOOK_SECRET:?Set POPNOW_WEBHOOK_SECRET to your webhook signing secret}"
BODY_FILE="${1:?Usage: $0 <raw-body-file> <timestamp> <signature>}"
TS="${2:?missing timestamp}"
SIG="${3:?missing signature}"

TASK_ID=$(jq -r .data.taskId "$BODY_FILE")
DIGEST=$(openssl dgst -sha256 -r "$BODY_FILE" | cut -d' ' -f1)
EXPECTED=$(printf '%s' "$TASK_ID.$TS.$DIGEST" | openssl dgst -sha256 -hmac "$SECRET" -binary | openssl base64 -A)

if [ "$EXPECTED" = "$SIG" ]; then
  echo "valid signature for $TASK_ID"
else
  echo "INVALID signature" >&2
  exit 1
fi
