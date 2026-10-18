# Tasks

> Create a task, follow its state, read the result, and use wait, the task list, retry and purge.

Online version: <https://popnow.ai/docs/tasks>

Every generation is a **task**. You create it with one call, it runs on its own, and you collect the result when it is ready — by asking for it, by waiting on the first call, or by receiving a [webhook](webhooks.md).

1. `POST /jobs/createTask` → `taskId`
2. `GET /jobs/recordInfo` → `state`
3. `GET output.assets[].url`

Three calls, in this order. Poll recordInfo until the state is final, then download the file before its link expires.

## Create a task

```bash
curl -X POST "https://api.popnow.ai/api/v1/jobs/createTask" \
  -H "Authorization: Bearer $POPNOW_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "model": "alibaba/wan-3.0/image-to-video",
    "input": {
      "image_url": "https://media.popnow.ai/movie/lighthouse.webp",
      "prompt": "Waves roll in slowly, the camera drifts toward the lighthouse",
      "resolution": "480p",
      "duration_seconds": 5
    },
    "callBackUrl": "https://your-app.example.com/hooks/popnow"
  }'
```

### Body

| Field                        | Required | Meaning                                                                          |
| ---------------------------- | -------- | -------------------------------------------------------------------------------- |
| `model`                      | Yes      | The model ID from [Models](https://popnow.ai/docs/models)                                         |
| `input`                      | Yes      | The model's own fields, validated against its input schema                       |
| `callBackUrl`                | No       | Public HTTPS URL that receives the finished task. See [Webhooks](webhooks.md) |
| `quoteId`, `expectedCredits` | No       | Lock in a price you confirmed with [jobs/quote](https://popnow.ai/docs/billing#quote)             |

### Headers

| Header                              | Meaning                                                                                                                 |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `Authorization: Bearer sk-popnow-…` | Your API key                                                                                                            |
| `Idempotency-Key`                   | Strongly recommended. A retry with the same key returns the original task. See [Idempotency](idempotency.md)         |
| `X-PopNow-Retention`                | Optional. Seconds to keep this task's outputs and prompt. It can only shorten how long things are kept, never extend it |
| `Accept-Language`                   | Optional. Language of error messages. See [Errors](errors.md#error-message-language)                                         |

### Response

A new task comes back as HTTP `202`:

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "taskId": "job_01JH8Z4Q5W2N7R3K9M6P1C0VXD",
    "state": "queued",
    "estimatedCredits": 34,
    "estimatedCost": "0.34",
    "deadlineAt": "2026-10-16T09:40:00Z"
  },
  "request_id": "req_…"
}
```

`202` means **accepted**, not finished. `estimatedCredits` is the amount held from your balance — the most this task can cost (`estimatedCost` is the same amount in US dollars). If creation fails instead, nothing is created and nothing is held; the `code` tells you why ([Errors](errors.md)).

## States

`queued` → `running` → `succeeded` / `failed` / `expired`

A task is in exactly one state at a time. Only succeeded is charged; every other final state returns the held credits in full.

| State       | Final? | Meaning                                                                    |
| ----------- | ------ | -------------------------------------------------------------------------- |
| `queued`    | No     | Accepted, waiting to start                                                 |
| `running`   | No     | Generating                                                                 |
| `succeeded` | Yes    | Done; the files are in `output.assets`                                     |
| `failed`    | Yes    | Could not finish; see `errorCode` and `errorMessage`. The hold is released |
| `expired`   | Yes    | Passed its deadline without finishing. The hold is released                |
| `canceled`  | Yes    | Only on old records. An accepted task cannot be canceled today             |

Treat any state you do not recognise as "not final yet" and keep reading.

## Skip the polling loop with `wait`

Add `?wait=<seconds>` (up to 60) to `createTask` and the connection stays open until the task finishes or the time runs out:

* Finished in time → HTTP `200` with the full task record, the same shape `recordInfo` returns. Check `data.state`: final does not always mean succeeded.
* Not finished → the ordinary `202`, and you carry on polling or wait for the webhook.

Use it for images and short audio; video almost always outlasts 60 seconds. Disconnecting early does not stop or cancel the task.

## Read a task

```bash
curl "https://api.popnow.ai/api/v1/jobs/recordInfo?taskId=job_01JH8Z4Q5W2N7R3K9M6P1C0VXD" \
  -H "Authorization: Bearer $POPNOW_API_KEY"
```

| Field                                    | Meaning                                                                                                                         |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `taskId`, `model`, `state`               | Which task, which model, where it is                                                                                            |
| `input`                                  | The input as it was run, including the `seed` that was picked if you left it out                                                |
| `output.assets[]`                        | The files. Each has `url`, `expiresAt`, `mime`, and when it applies `width`, `height`, `durationSeconds`, `bytes`, `role`       |
| `errorCode`, `errorMessage`              | Why a task failed. Branch on `errorCode`, show `errorMessage`                                                                   |
| `credits`, `cost`, `settled`             | While `settled` is `false`, `credits` is the hold; once `true`, it is the final charge. `cost` is the same amount in US dollars |
| `createdAt`, `completedAt`, `deadlineAt` | Timestamps; `deadlineAt` is when an unfinished task expires                                                                     |
| `retention.outputsExpireAt`              | When this task's files will be removed                                                                                          |
| `contentState`                           | `present`, or `expired` / `purged` once the content has been removed                                                            |

### Three different expiry times

* **`deadlineAt`** — how long the task may run. Past it, the task becomes `expired` and the hold is released.
* **`output.assets[].expiresAt`** — how long that one signed link works, about 20 minutes. Read the task again for a fresh link; the file itself is still there.
* **`retention.outputsExpireAt`** — when the stored file is removed. Download anything you want to keep before then, or save it to your [asset library](assets.md).

### What `output` contains

Most tasks return one asset. Some return more: several images when the model makes variations, a joined clip plus the new segment for video extension (`role: "video"` then `role: "segment"`), or a base image plus transparent layers for layer separation (each with a `layer` object). Speech-to-text returns the transcript in `output.text`.

Asset links are bearer links: anyone with the URL can download the file until it expires, and you should **not** send your API key when fetching them.

## Webhooks first, polling as a fallback

Polling works, but a webhook is cheaper for both sides: you hear about the result the moment it exists and spend nothing on requests in between. A robust integration uses both — webhooks for the normal path, and an occasional `recordInfo` sweep for any task whose webhook you did not receive.

When you poll, back off: every 2–3 seconds for images, every 10–15 seconds for video, and stop at `deadlineAt`.

## The task list

`GET /api/v1/jobs` returns the tasks this key created, newest first, without inputs or outputs:

```bash
curl "https://api.popnow.ai/api/v1/jobs?state=failed&from=2026-10-01&limit=50" \
  -H "Authorization: Bearer $POPNOW_API_KEY"
```

Filters: `from` and `to` (UTC dates, at most 92 days apart; the default is the last seven days), `state`, `model`, `limit` (up to 100). When `hasMore` is `true`, pass `nextCursor` back as `cursor` with the same filters.

## Retry a failed task

`POST /api/v1/jobs/retry` with `{ "taskId": "…" }` creates a **new** task from a `failed` or `expired` one, using its original input at today's price. The original task is never changed. It answers `409` while the source task is not final yet, and cannot retry a task that succeeded — create a new one instead.

## Delete a task's content

`POST /api/v1/jobs/purge` with `{ "taskId": "…" }` deletes the task's files, its result and its stored prompt. The billing record stays: the charge, the model, the state and the timestamps remain, and the response says so with `billingRetained: true`. Only finished tasks can be purged, and repeating the call is safe.

## Next

* [Webhooks](webhooks.md) — receive results instead of polling.
* [Media](media.md) — upload your own reference files.
* [Errors](errors.md) — every code and whether to retry.
