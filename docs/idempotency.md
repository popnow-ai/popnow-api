# Idempotency

> Retry after a timeout without generating twice or paying twice.

Online version: <https://popnow.ai/docs/idempotency>

An **idempotency key** is a label you attach to one piece of work, such as "render the video for order 8814". If the same labelled request reaches PopNow twice, the work is done once.

```http
POST /api/v1/jobs/createTask
Idempotency-Key: order-8814-render-1
```

## Why you want it

A timeout leaves you guessing: maybe the request never arrived, maybe it arrived and only the answer was lost. Without a key, you either give up (and the user waits for nothing) or retry (and maybe generate and pay twice). With a key, retrying is always safe: you get either a new task or the one created a moment ago.

## How it behaves

* A repeat with the same key, from the same API key, returns **the original task** in its current state — no second task, no second hold, no second charge.
* The key is tied to what you sent: `model`, the whole `input` and `callBackUrl`. Field order and whitespace do not matter, but any real change does. A changed request with an old key returns `409`; give it a new key.
* A key is remembered for **24 hours** from first use. After that the same key creates a new, billed task, so stop automatic retries well before then.
* Keys are up to 128 characters and only need to be unique within your account. Another API key on your account cannot reuse one: it gets `409` without the original task ID.

| Endpoint                       | A repeat with the same key…                                                |
| ------------------------------ | -------------------------------------------------------------------------- |
| `POST /api/v1/jobs/createTask` | returns the original task                                                  |
| `POST /api/v1/jobs/retry`      | returns the task that retry created (the key is scoped to the source task) |
| `POST /v1/videos`              | returns the original task                                                  |
| `POST /api/v1/assets`          | returns the asset already saved (the header is required here)              |

Read endpoints and upload/download link endpoints ignore the header. `jobs/purge` needs none: repeating it is already harmless.

## Choosing keys

* **One key per piece of work**, not per HTTP attempt. Every retry must reuse it.
* Derive it from something you already store: `order-8814-render-1` can be recomputed after a crash; a random UUID cannot unless you save it first.
* If you use a UUID, generate it **before** the first attempt and keep it next to the job it belongs to.

> **Never generate the key inside the retry loop**
>
> ```javascript
> // Wrong: a new key per attempt defeats the whole mechanism
> for (let i = 0; i < 3; i++) await createTask(body, crypto.randomUUID());
>
> // Right: one key, created once
> const key = crypto.randomUUID();
> for (let i = 0; i < 3; i++) await createTask(body, key);
> ```

## Conflicts

All of these return `code: 409`:

| What happened                                             | Retry?                                                                 |
| --------------------------------------------------------- | ---------------------------------------------------------------------- |
| Two requests with the same key arrived at the same moment | Yes — wait a few hundred milliseconds and resend with the **same** key |
| The key was already used for a different request          | No — the request changed, so it needs a new key                        |
| Another API key on your account already used this key     | No — retry with the API key that made the first attempt                |

Your code should not branch on `msg`, so allow one or two `409` retries and then surface the error to a person.

## Full example

```javascript title="JavaScript"
const RETRYABLE = new Set([429, 500, 503, 50301]); // business codes from the body

async function createTaskOnce(body, idempotencyKey) {
  for (let attempt = 0; attempt < 4; attempt++) {
    try {
      const res = await fetch('https://api.popnow.ai/api/v1/jobs/createTask', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${process.env.POPNOW_API_KEY}`,
          'Content-Type': 'application/json',
          'Idempotency-Key': idempotencyKey,
        },
        body: JSON.stringify(body),
      });
      const json = await res.json();
      if (json.code === 200) return json.data; // a new task, or the original one
      if (!RETRYABLE.has(json.code)) throw new Error(`${json.code} ${json.msg} (${json.request_id})`);
    } catch (err) {
      if (!(err instanceof TypeError)) throw err; // network error: safe to retry with the same key
    }
    await new Promise((r) => setTimeout(r, 2 ** attempt * 500 + Math.random() * 300));
  }
  throw new Error('createTask did not succeed after 4 attempts');
}

const task = await createTaskOnce(
  { model: 'alibaba/z-image-turbo/text-to-image', input: { prompt: 'A paper boat on a calm lake' } },
  'order-8814-render-1',
);
```
