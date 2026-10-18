#!/usr/bin/env bash
# Poll a task until it reaches a final state, then print its file URL.
# Usage: ./poll-job.sh job_...
# Requires: curl, jq
set -euo pipefail
API="${POPNOW_API_BASE:-https://api.popnow.ai}/api/v1"
KEY="${POPNOW_API_KEY:?Set POPNOW_API_KEY to your sk-popnow-... key}"
TASK_ID="${1:?Usage: $0 <taskId>}"

DELAY=3
while true; do
  TASK=$(curl -sS "$API/jobs/recordInfo?taskId=$TASK_ID" -H "Authorization: Bearer $KEY")
  if [ "$(echo "$TASK" | jq -r .code)" != "200" ]; then
    echo "$TASK" | jq . >&2
    exit 1
  fi
  STATE=$(echo "$TASK" | jq -r .data.state)
  # A final task can still have files being copied into storage ("pending").
  COPYING=$(echo "$TASK" | jq '[.data.output.assets[]? | select(.pending == true and .unavailable != true)] | length')
  case "$STATE" in
    succeeded|failed|expired|canceled)
      if [ "$COPYING" = "0" ]; then break; fi ;;
  esac
  echo "state=$STATE, checking again in ${DELAY}s" >&2
  sleep "$DELAY"
  # Back off gently: images finish in seconds, video in minutes.
  DELAY=$(( DELAY < 15 ? DELAY + 3 : 15 ))
done

echo "$TASK" | jq '.data | {taskId, state, credits, cost, errorCode, errorMessage, url: .output.assets[0].url}'
# The signed URL works for about 20 minutes and needs no API key:
#   curl -L -o result.mp4 "<url>"
