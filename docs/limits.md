# Rate limits

> How many requests you can send, what happens when you send more, and the other limits worth knowing.

Online version: <https://popnow.ai/docs/limits>

Limits protect everyone sharing the service. The defaults are generous for normal use; if you hit one, the response tells you exactly how long to wait.

## At a glance

| Limit                                                         | Default                                                             | When you hit it          |
| ------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------ |
| Writes per account (`createTask`, `retry`, uploads …)         | 1,000 per 10 seconds                                                | `429` with `Retry-After` |
| Reads per account (`recordInfo`, `models`, `jobs`, `quote` …) | 1,000 per 10 seconds                                                | `429` with `Retry-After` |
| Upload tickets                                                | 1,000 per 10 seconds, on top of writes                              | `429` with `Retry-After` |
| Usage report (`/api/v1/usage`)                                | 30 per minute per account                                           | `429` with `Retry-After` |
| Asset library                                                 | 60 reads and 30 saves per minute, plus a daily number of new assets | `429` with `Retry-After` |
| Any request, before the key is checked                        | 6,000 per minute per network                                        | `429`                    |
| Request body                                                  | 2 MiB of JSON                                                       | `413`                    |
| Balance                                                       | What is in your account                                             | `40201`                  |
| Key spend caps                                                | None unless you set one                                             | `40202`                  |

Limits count per **account**, not per key — creating more keys does not raise them.

## Response headers

| Header                  | Meaning                                                                            |
| ----------------------- | ---------------------------------------------------------------------------------- |
| `X-RateLimit-Limit`     | Your allowance for the current window                                              |
| `X-RateLimit-Remaining` | Requests left in it — sent on successful responses too, so you can slow down early |
| `Retry-After`           | On `429`: seconds to wait before trying again                                      |

The numbers above are defaults and can change; trust the headers rather than hard-coding them.

## What a limit looks like

```json
{ "code": 429, "msg": "Too many requests. Retry in a moment", "request_id": "req_…" }
```

A request over the limit is rejected immediately — not queued — and costs nothing.

## Handling it

* Wait at least `Retry-After` seconds, then retry. Add a little random jitter so a batch of clients does not come back at the same instant.
* When you retry `createTask`, send the **same** `Idempotency-Key` ([Idempotency](idempotency.md)).
* Poll gently: every few seconds for images, every 10–15 seconds for video. Better still, use [webhooks](webhooks.md) — they cost no requests at all.

## Running many tasks at once

Rate limits cap how fast you **send** requests, not how many tasks run at the same time. You can have many tasks in flight; long video jobs simply take longer. If you need to start thousands of tasks, spread them out and let webhooks bring the results back.

Need a higher allowance for a launch or a large batch? [Contact us](https://popnow.ai/contact) with your expected volume.
