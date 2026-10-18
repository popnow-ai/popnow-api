# Errors

> Every business code, what it means, and which errors are worth retrying.

Online version: <https://popnow.ai/docs/errors>

When a call goes wrong, the response gives you a **number** (`code`) that says what kind of problem it is and a **sentence** (`msg`) for a person to read. Branch on the number; show or log the sentence.

## The envelope

```json
{ "code": 40201, "msg": "Insufficient balance", "request_id": "req_…" }
```

* `code` is a business code. `200` means success; everything else is listed below.
* On failure there is no `data` field, except on a few [asset library](assets.md#errors) errors and on prompts or input images declined by the content check at submission (`400`, nothing charged); both add a machine-readable `data.reason`.
* The HTTP status is set too (`40201` comes with HTTP `402`). Branch on one of the two, not a mix — we recommend `code`, which is more specific.
* `request_id` is also in the `X-Request-Id` header. Include it when you contact support.

If a response is not JSON at all — an HTML or plain-text page from the network in between — handle it by HTTP status and log the first part of the body.

## Error message language

`msg` and a failed task's `errorMessage` are English by default. Send `Accept-Language` with one of `en`, `zh-CN`, `zh-TW`, `ja`, `ko`, `de`, `fr`, `es`, `pt-BR`, `ru`, `it` or `pl`, or set the API error language in the console, to get them in that language; other languages fall back to English. Error responses carry `Content-Language`. Codes never change with the language — another reason never to parse `msg`.

When a model reports a specific reason for failing (for example an unreadable reference image), `errorMessage` passes that reason on in English, with internal details removed.

## General codes

| `code`  | HTTP      | Meaning                                                                          | Retry?                                   |
| ------- | --------- | -------------------------------------------------------------------------------- | ---------------------------------------- |
| `200`   | 200 / 202 | Success                                                                          | —                                        |
| `400`   | 400       | The request or its `input` is invalid; `msg` names the problem                   | No — fix it                              |
| `40003` | 400       | An upload does not match its ticket (size, type or content)                      | No — new ticket, upload again            |
| `40004` | 400       | Valid request, but the model cannot serve this combination of settings right now | No — change the setting named in `msg`   |
| `401`   | 401       | Missing, unknown or revoked key ([details](authentication.md#what-a-failure-looks-like))         | No                                       |
| `403`   | 403       | Not allowed (see [Permissions](#permissions))                                    | No                                       |
| `404`   | 404       | Does not exist, or belongs to another key                                        | No                                       |
| `409`   | 409       | Conflicts with the current state ([when to retry](#when-409-is-worth-retrying))                   | Sometimes                                |
| `40901` | 409       | A quote expired or the price changed                                             | Quote again                              |
| `413`   | 413       | Request body too large                                                           | No — upload media instead of inlining it |
| `429`   | 429       | Too many requests                                                                | Yes — after `Retry-After`                |
| `500`   | 500       | Something broke on our side                                                      | Yes — with backoff                       |
| `503`   | 503       | A supporting service is briefly unavailable                                      | Yes — after `Retry-After`                |

## Balance and caps

| `code`  | HTTP | Meaning                                 | What to do                                                |
| ------- | ---- | --------------------------------------- | --------------------------------------------------------- |
| `40201` | 402  | Not enough credits for this task's hold | [Buy credits](https://popnow.ai/pricing), then send again |
| `40202` | 402  | A key spend cap was reached             | Raise the cap in the API console, or wait for it to reset |

## Permissions

| `code`  | HTTP | Meaning                                                     | What to do                                                                   |
| ------- | ---- | ----------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `40301` | 403  | This key may not call this model                            | Add the model to the key's allowed list                                      |
| `40302` | 403  | Request came from an address outside the key's IP allowlist | Add the address or remove the restriction                                    |
| `40303` | 403  | The service is not offered in this region                   | Cannot be worked around                                                      |
| `40310` | 403  | The account's email address is not verified yet             | Open the link in your sign-up email; the key works as soon as it is verified |

A plain `403` with a valid key means the account cannot use the API right now; contact support with the `request_id`.

## Model availability

| `code`  | HTTP | Meaning                                      | Retry?                               |
| ------- | ---- | -------------------------------------------- | ------------------------------------ |
| `50301` | 503  | The model cannot take tasks right now        | Yes, later — or choose another model |
| `40004` | 400  | The model works, but not with these settings | No — change the setting              |

Neither creates a task or holds credits.

## Task failure codes

A task that was accepted and then failed has `state: "failed"` and one of these in `errorCode`. The list is closed: treat any other value as `upstream_failed`.

| `errorCode`               | Meaning                                                      | Retry?                                           |
| ------------------------- | ------------------------------------------------------------ | ------------------------------------------------ |
| `invalid_request`         | The model did not accept the parameters                      | No — fix them                                    |
| `unsupported_combination` | This combination of settings is not supported right now      | No — change a setting                            |
| `content_rejected`        | The model declined this content                              | No — change the prompt or the reference          |
| `invalid_asset`           | A reference file could not be read or is no longer available | Upload it again and create a new task            |
| `rate_limited`            | The generation service was busy                              | Yes, with backoff                                |
| `upstream_unavailable`    | Generation is temporarily unavailable                        | Yes, shortly                                     |
| `generation_failed`       | Generation ran but produced nothing                          | Maybe — the same input often fails the same way  |
| `timeout`                 | The task ran out of time                                     | Maybe — try a shorter or lower-resolution output |
| `upstream_failed`         | Anything else                                                | Yes, with backoff                                |

A failed task releases its hold, so it costs nothing (a few models charge for content refusals, and say so on their page). `errorMessage` explains the reason in words; branch on `errorCode` only.

## When `409` is worth retrying

| Case                                                                     | Retry?                                      |
| ------------------------------------------------------------------------ | ------------------------------------------- |
| Two requests with the same `Idempotency-Key` arrived together            | Yes, with the same key, after a short pause |
| The `Idempotency-Key` was used for a different request or by another key | No                                          |
| An upload or an output is still being processed                          | Yes, after a few seconds                    |
| `jobs/retry` on a task that has not finished yet                         | Yes, once it is final                       |
| `jobs/retry` on a task that succeeded                                    | No — create a new task                      |
| An upload ticket or uploaded file has expired                            | No — upload again                           |

## Writing the retry

Retry only what can succeed on a second try, wait for `Retry-After` when it is given, and back off exponentially otherwise:

```javascript title="JavaScript"
const RETRYABLE = new Set([429, 500, 503, 50301]);

async function call(path, init, attempts = 4) {
  for (let i = 0; i < attempts; i++) {
    const res = await fetch(`https://api.popnow.ai/api/v1${path}`, init);
    if (!res.headers.get('content-type')?.includes('json')) {
      throw new Error(`HTTP ${res.status}: ${(await res.text()).slice(0, 200)}`);
    }
    const body = await res.json();
    if (body.code === 200) return body.data;
    if (!RETRYABLE.has(body.code)) throw new Error(`${body.code} ${body.msg} (${body.request_id})`);
    const wait = Number(res.headers.get('retry-after')) * 1000 || 2 ** i * 1000 + Math.random() * 500;
    await new Promise((r) => setTimeout(r, wait));
  }
  throw new Error('out of retries');
}
```

```python title="Python"
import random, time, requests

RETRYABLE = {429, 500, 503, 50301}

def call(method, path, attempts=4, **kwargs):
    for i in range(attempts):
        res = requests.request(method, f"https://api.popnow.ai/api/v1{path}", timeout=60, **kwargs)
        try:
            body = res.json()
        except ValueError:
            raise RuntimeError(f"HTTP {res.status_code}: {res.text[:200]}")
        if body["code"] == 200:
            return body["data"]
        if body["code"] not in RETRYABLE:
            raise RuntimeError(f'{body["code"]} {body["msg"]} ({body.get("request_id")})')
        retry_after = res.headers.get("retry-after")
        time.sleep(float(retry_after) if retry_after else 2**i + random.random() / 2)
    raise RuntimeError("out of retries")
```

When retrying `createTask`, always send the **same** `Idempotency-Key`, so a request that actually succeeded is not run and charged twice.

## Debugging

1. Note the `request_id` and the `code`.
2. Look the task up in the API console's logs, by task ID or `request_id`.
3. Still stuck? [Contact support](https://popnow.ai/contact) with the `request_id`, the time (UTC) and the `code`. Never send your API key.
