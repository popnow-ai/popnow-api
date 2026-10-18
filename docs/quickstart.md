# Quickstart

> Create an API key, send your first request and download the result in about five minutes.

Online version: <https://popnow.ai/docs/quickstart>

This page takes you from nothing to a generated image with one key and one request. Everything after that — video, audio, webhooks, uploads — is the same request with a different `model` and `input`.

## Before you start

* **A PopNow account.** Sign up at [popnow.ai](https://popnow.ai). The API spends the same credits as the website; buy a [credit pack](https://popnow.ai/pricing). There is no separate API plan.
* **A terminal with `curl`.** The examples use bash. On Windows, use WSL or Git Bash.

## 1. Create an API key

Open the [API console](https://popnow.ai/api/console/keys) and choose **Create key**. Copy the key straight away: the full value is shown only once. Then put it in an environment variable so it never lands in your code:

```bash
export POPNOW_API_KEY="sk-popnow-..."
```

Every key starts with `sk-popnow-` and spends the credits in your account. Keep it on your server; [Authentication](authentication.md) explains restrictions, rotation and what to do if a key leaks.

## 2. Send a task

Paste this into the same terminal. It asks a fast image model for one picture and costs a couple of credits:

```bash
export POPNOW_API_KEY="sk-popnow-..."   # your key from the API console

curl -X POST "https://api.popnow.ai/api/v1/jobs/createTask?wait=60" \
  -H "Authorization: Bearer $POPNOW_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
  "model": "alibaba/z-image-turbo/text-to-image",
  "input": {
    "prompt": "A small red fox curled up in a teacup, soft morning light, studio photo"
  }
}'
```

What each part does:

* **`model`** is the model ID — which model runs and which job it does. Every model's ID is on [Models](https://popnow.ai/docs/models).
* **`input`** is checked against that model's own input schema. Unknown fields are rejected, so typos fail fast instead of being ignored.
* **`Idempotency-Key`** makes a retry safe: send the same key again after a timeout and you get the original task back instead of a second charge. See [Idempotency](idempotency.md).
* **`?wait=60`** keeps the connection open for up to 60 seconds, so a quick image comes back in this same response.

## 3. Read the result

A finished task looks like this:

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "taskId": "job_01JH8Z4Q5W2N7R3K9M6P1C0VXD",
    "model": "alibaba/z-image-turbo/text-to-image",
    "state": "succeeded",
    "output": {
      "assets": [
        {
          "url": "https://…signed-link…",
          "expiresAt": "2026-10-16T09:20:00Z",
          "mime": "image/png",
          "width": 1024,
          "height": 1024
        }
      ]
    },
    "credits": 2,
    "cost": "0.02",
    "settled": true
  },
  "request_id": "req_…"
}
```

* `state` is `succeeded`. A task that could not finish says `failed` and carries an `errorCode`; see [Errors](errors.md#task-failure-codes).
* `output.assets[0].url` is a signed link to the file. It works for about 20 minutes, needs no API key, and you can always get a fresh one by reading the task again.
* `credits` is what the task was charged, in whole credits (1 credit = $0.01). `cost` carries the same amount as a US dollar string.

If the model needs more than 60 seconds — every video model does — the response is a `202` with `state: "queued"` and a `taskId` instead. Ask for the task until it is final:

```bash
curl "https://api.popnow.ai/api/v1/jobs/recordInfo?taskId=job_..." \
  -H "Authorization: Bearer $POPNOW_API_KEY"
```

Check every few seconds until `state` is `succeeded`, `failed` or `expired`. In production, pass a `callBackUrl` and let a [webhook](webhooks.md) tell you instead.

## The same request in code

```javascript title="JavaScript (Node.js 18+)"
const API = 'https://api.popnow.ai/api/v1';
const headers = {
  Authorization: `Bearer ${process.env.POPNOW_API_KEY}`,
  'Content-Type': 'application/json',
};

const created = await fetch(`${API}/jobs/createTask`, {
  method: 'POST',
  headers: { ...headers, 'Idempotency-Key': crypto.randomUUID() },
  body: JSON.stringify({
    model: 'alibaba/z-image-turbo/text-to-image',
    input: { prompt: 'A small red fox curled up in a teacup, soft morning light' },
  }),
}).then((r) => r.json());
if (created.code !== 200) throw new Error(`${created.code} ${created.msg}`);

// Poll until the task reaches a final state.
let task;
do {
  await new Promise((r) => setTimeout(r, 3000));
  const res = await fetch(`${API}/jobs/recordInfo?taskId=${created.data.taskId}`, { headers });
  task = (await res.json()).data;
} while (task.state === 'queued' || task.state === 'running');

console.log(task.state, task.output?.assets?.[0]?.url);
```

```python title="Python (requests)"
import os, time, uuid, requests

API = "https://api.popnow.ai/api/v1"
headers = {"Authorization": f"Bearer {os.environ['POPNOW_API_KEY']}"}

created = requests.post(
    f"{API}/jobs/createTask",
    headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
    json={
        "model": "alibaba/z-image-turbo/text-to-image",
        "input": {"prompt": "A small red fox curled up in a teacup, soft morning light"},
    },
    timeout=30,
).json()
if created["code"] != 200:
    raise RuntimeError(f'{created["code"]} {created["msg"]}')

# Poll until the task reaches a final state.
while True:
    time.sleep(3)
    task = requests.get(
        f"{API}/jobs/recordInfo",
        headers=headers,
        params={"taskId": created["data"]["taskId"]},
        timeout=30,
    ).json()["data"]
    if task["state"] not in ("queued", "running"):
        break

print(task["state"], task.get("output", {}).get("assets", [{}])[0].get("url"))
```

## The response envelope

Every JSON response has the same four fields:

```json
{ "code": 200, "msg": "success", "data": { }, "request_id": "req_…" }
```

`code` is a business code, not an HTTP status: `200` means success, anything else is an error listed on [Errors](errors.md). Branch on `code`, never on the wording of `msg`. Quote `request_id` when you contact support.

## Next

- [Pick a model](https://popnow.ai/docs/models): Every model ID, its parameters and its price in credits.
- [How tasks work](tasks.md): States, polling, wait, retries and the task list.
- [Upload your own files](media.md): Send reference images, video and audio.
- [Get notified](webhooks.md): Receive the result instead of polling.
