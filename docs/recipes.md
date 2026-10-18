# Recipes

> Copy-and-run Python and Node.js recipes for the PopNow AI image, video and text-to-speech API - batch images from a CSV, photo to video, voiceovers line by line, and a Slack alert when a video is ready.

Online version: <https://popnow.ai/docs/recipes>

Four small scripts for the jobs people automate first. Each one is complete: install `requests` (or use Node 18+), set `POPNOW_API_KEY`, run it. They share the same three helpers (call, wait, save), so once you have read one, the others are a few lines each. The [Recipes page on popnow.ai](https://popnow.ai/api/workflows) builds the same scripts for any model you pick.

| Recipe                                       | Model                                        | Cost per item                     |
| -------------------------------------------- | -------------------------------------------- | --------------------------------- |
| [Batch images from a CSV](#batch-images-from-a-csv)     | `alibaba/z-image-turbo/text-to-image`        | 2 credits per image               |
| [Photo to video](#photo-to-video)            | `minimax/h3/image-to-video`                  | 28 credits for 5 s at 768p        |
| [A voiceover per line](#a-voiceover-per-line)           | `google/gemini-3.8-flash-tts/text-to-speech` | about 1 credit per 20 s of speech |
| [Slack alert when a video is ready](#slack-alert-when-a-video-is-ready) | `minimax/h3/image-to-video`                  | 28 credits for 5 s at 768p        |

Swap the model for any other on [Models](https://popnow.ai/docs/models); keep the `input` fields to the ones that model's schema lists.

## The helpers

Every Python recipe ends with these. `create` sends a task with an idempotency key, `wait` polls with backoff until the task is final and its files are copied, `save` downloads the first file.

```python title="helpers.py"
import os, time
import requests

BASE = "https://api.popnow.ai/api/v1"
HEADERS = {"Authorization": f"Bearer {os.environ['POPNOW_API_KEY']}"}

def call(method, path, **kwargs):
    headers = {**HEADERS, **kwargs.pop("headers", {})}
    body = requests.request(method, BASE + path, headers=headers, timeout=60, **kwargs).json()
    if body["code"] != 200:
        raise RuntimeError(f'{body["code"]} {body["msg"]}')
    return body["data"]

def create(payload, key):
    return call("POST", "/jobs/createTask", json=payload, headers={"Idempotency-Key": key})["taskId"]

def wait(task_id):
    delay = 2.0
    while True:
        time.sleep(delay)
        task = call("GET", "/jobs/recordInfo", params={"taskId": task_id})
        assets = (task.get("output") or {}).get("assets") or []
        copying = any(a.get("pending") and not a.get("unavailable") for a in assets)
        if task["state"] in ("succeeded", "failed", "canceled", "expired") and not copying:
            return task
        delay = min(delay * 1.5, 15.0)

def save(task, path):
    if task["state"] != "succeeded":
        raise RuntimeError(f'{task["state"]}: {task.get("errorMessage", "no detail")}')
    url = task["output"]["assets"][0]["url"]
    with open(path, "wb") as f:
        f.write(requests.get(url, timeout=300).content)
```

## Batch images from a CSV

`prompts.csv` has a `prompt` column; each row becomes one image in `out/`. All tasks are submitted first and collected afterwards, so they render in parallel. The idempotency key is derived from the row, so rerunning after a crash never pays twice for a row that already went through.

```python title="batch_images.py"
import csv, hashlib, pathlib
from helpers import create, wait, save

MODEL = "alibaba/z-image-turbo/text-to-image"

out = pathlib.Path("out")
out.mkdir(exist_ok=True)
with open("prompts.csv", newline="", encoding="utf-8") as f:
    rows = [r["prompt"] for r in csv.DictReader(f) if r.get("prompt")]

tasks = []
for i, prompt in enumerate(rows, start=1):
    key = "batch-" + hashlib.sha256(f"{i}:{prompt}".encode()).hexdigest()[:32]
    tasks.append((i, create({"model": MODEL, "input": {"prompt": prompt, "aspect_ratio": "1:1"}}, key)))

for i, task_id in tasks:
    save(wait(task_id), out / f"{i:03d}.png")
    print("saved", i)
```

The same in Node.js 18+, without any package:

```javascript title="batch_images.mjs"
import { createHash } from 'node:crypto';
import { readFile, writeFile, mkdir } from 'node:fs/promises';

const API = 'https://api.popnow.ai/api/v1';
const auth = { Authorization: `Bearer ${process.env.POPNOW_API_KEY}` };
const call = async (path, init = {}) => {
  const body = await fetch(API + path, { ...init, headers: { ...auth, ...init.headers } }).then((r) => r.json());
  if (body.code !== 200) throw new Error(`${body.code} ${body.msg}`);
  return body.data;
};

const prompts = (await readFile('prompts.txt', 'utf8')).split('\n').map((l) => l.trim()).filter(Boolean);
await mkdir('out', { recursive: true });

const ids = await Promise.all(prompts.map((prompt, i) => call('/jobs/createTask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'Idempotency-Key': 'batch-' + createHash('sha256').update(`${i}:${prompt}`).digest('hex').slice(0, 32) },
  body: JSON.stringify({ model: 'alibaba/z-image-turbo/text-to-image', input: { prompt, aspect_ratio: '1:1' } }),
}).then((d) => d.taskId)));

for (const [i, id] of ids.entries()) {
  let task;
  do {
    await new Promise((r) => setTimeout(r, 3000));
    task = await call(`/jobs/recordInfo?taskId=${id}`);
  } while (task.state === 'queued' || task.state === 'running');
  if (task.state !== 'succeeded') { console.error(i, task.state, task.errorMessage); continue; }
  const file = await fetch(task.output.assets[0].url).then((r) => r.arrayBuffer());
  await writeFile(`out/${String(i + 1).padStart(3, '0')}.png`, Buffer.from(file));
}
```

## Photo to video

Uploads a local photo, then asks an image-to-video model to bring it to life. Run it as `python photo_to_video.py photo.jpg`.

```python title="photo_to_video.py"
import mimetypes, sys, uuid
import requests
from helpers import call, create, wait, save

MODEL = "minimax/h3/image-to-video"

def upload(path):
    """Local file -> popnow:// reference you can put in any image, video or audio field."""
    data = open(path, "rb").read()
    kind = mimetypes.guess_type(path)[0] or "image/jpeg"
    ticket = call("POST", "/common/upload-url", json={"contentType": kind, "bytes": len(data)})
    requests.put(ticket["uploadUrl"], data=data, headers=ticket.get("headers", {}), timeout=120).raise_for_status()
    return call("POST", f'/files/{ticket["fileId"]}/commit')["uri"]

ref = upload(sys.argv[1])
task_input = {"image_url": ref, "prompt": "Gentle camera push-in, hair moving in the wind", "duration_seconds": 5, "resolution": "768p"}
task_id = create({"model": MODEL, "input": task_input}, str(uuid.uuid4()))
save(wait(task_id), "clip.mp4")
print("saved clip.mp4")
```

Testing the request without code first:

```bash
curl -X POST "https://api.popnow.ai/api/v1/jobs/createTask" \
  -H "Authorization: Bearer $POPNOW_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"model": "minimax/h3/image-to-video", "input": {"image_url": "https://media.popnow.ai/movie/lighthouse.webp", "prompt": "The waves roll in slowly", "duration_seconds": 5}}'
```

## A voiceover per line

`lines.txt` holds one line of script per line; each becomes its own audio file in `voice/`, all in the same voice. `voice_id` options include Kore, Puck, Charon and Aoede; the model's page lists them all, along with `style` and `accent`.

```python title="voiceover.py"
import hashlib, pathlib
from helpers import create, wait, save

MODEL = "google/gemini-3.8-flash-tts/text-to-speech"

out = pathlib.Path("voice")
out.mkdir(exist_ok=True)
lines = [l.strip() for l in open("lines.txt", encoding="utf-8") if l.strip()]

tasks = []
for i, line in enumerate(lines, start=1):
    key = "voice-" + hashlib.sha256(f"{i}:{line}".encode()).hexdigest()[:32]
    tasks.append((i, create({"model": MODEL, "input": {"text": line, "voice_id": "Kore", "style": "empathetic"}}, key)))

for i, task_id in tasks:
    task = wait(task_id)
    mime = ((task.get("output") or {}).get("assets") or [{}])[0].get("mime", "")
    ext = {"audio/mpeg": ".mp3", "audio/wav": ".wav", "audio/ogg": ".ogg"}.get(mime, ".audio")
    save(task, out / f"{i:03d}{ext}")
    print("saved", i)
```

## Slack alert when a video is ready

Instead of polling, pass `callBackUrl` when you create the task. A small Express server checks the signature on the raw body and posts the result to a Slack incoming webhook. Set `POPNOW_WEBHOOK_SECRET` (from the [API console](https://popnow.ai/api/console/webhooks)) and `SLACK_WEBHOOK_URL`.

```javascript title="notify.mjs (npm install express)"
import { createHash, createHmac, randomUUID, timingSafeEqual } from 'node:crypto';
import express from 'express';

const BASE = 'https://api.popnow.ai/api/v1';

// 1. Create the task with a callBackUrl that points at this server.
export async function createVideo() {
  const res = await fetch(BASE + '/jobs/createTask', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.POPNOW_API_KEY}`,
      'Content-Type': 'application/json',
      'Idempotency-Key': randomUUID(),
    },
    body: JSON.stringify({
      model: 'minimax/h3/image-to-video',
      input: { image_url: 'https://media.popnow.ai/movie/lighthouse.webp', prompt: 'The waves roll in slowly', duration_seconds: 5 },
      callBackUrl: 'https://your-server.example.com/hooks/popnow',
    }),
  });
  return (await res.json()).data.taskId;
}

// 2. Receive the finished task, check the signature on the raw body, then post to Slack.
const app = express();
app.post('/hooks/popnow', express.raw({ type: 'application/json' }), async (req, res) => {
  const timestamp = req.header('X-Webhook-Timestamp');
  const signature = req.header('X-Webhook-Signature') ?? '';
  const event = JSON.parse(req.body.toString('utf8'));
  const task = event.data;
  const digest = createHash('sha256').update(req.body).digest('hex');
  const expected = createHmac('sha256', process.env.POPNOW_WEBHOOK_SECRET)
    .update(`${task.taskId}.${timestamp}.${digest}`)
    .digest('base64');
  const ok = expected.length === signature.length && timingSafeEqual(Buffer.from(expected), Buffer.from(signature));
  if (!ok || Math.abs(Date.now() / 1000 - Number(timestamp)) > 300) return res.status(401).end();
  res.status(200).end(); // answer first; deliveries are retried until you return 2xx

  const text = task.state === 'succeeded'
    ? `Video ready: ${task.output.assets[0].url}`
    : `Task ${task.taskId} ${task.state}: ${task.errorMessage ?? 'no detail'}`;
  await fetch(process.env.SLACK_WEBHOOK_URL, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) });
});
app.listen(3000);
```

The link in the Slack message is signed and works for about 20 minutes; post the `taskId` too if people may open it later. [Webhooks](webhooks.md) covers retries and duplicate deliveries.

## Pricing and limits

Each recipe pays the model's normal price per item and nothing else; reading tasks and uploading files are free. Failed items cost nothing, and because each item has its own idempotency key, rerunning a script only creates the items that never went through. Before a large batch, price one item with [`jobs/quote`](https://popnow.ai/docs/billing#quote) and set a daily cap on the key ([Authentication](authentication.md)). Submitting hundreds of tasks at once is fine, within the [rate limits](limits.md).

## Common errors

| Error                                | Why                                                                     | Fix                                                    |
| ------------------------------------ | ----------------------------------------------------------------------- | ------------------------------------------------------ |
| `KeyError: 'POPNOW_API_KEY'`         | The variable is not set in this shell                                   | `export POPNOW_API_KEY="sk-popnow-..."`                |
| `RuntimeError: 400 …` naming a field | The model does not accept that field or value                           | Check the model's page; fields differ per model        |
| `RuntimeError: 40201 …`              | Not enough credits for the next task                                    | Top up; tasks already accepted keep running            |
| `RuntimeError: 429 …`                | Too many requests at once                                               | Submit in smaller groups and honour `Retry-After`      |
| `RuntimeError: failed: …`            | One item failed or was declined                                         | Nothing was charged for it; fix that row and rerun     |
| `RuntimeError: 40003 …` on commit    | The uploaded bytes do not match the ticket                              | Ask for a new ticket and upload again                  |
| Webhook returns `401`                | Signature computed on parsed JSON instead of raw bytes, or wrong secret | Use `express.raw`, and the secret from the API console |

### Is there an official Python or Node SDK?

Not yet. The API is plain REST with JSON, so these recipes use requests and the built-in fetch, and the OpenAPI file can generate a typed client.

### How many tasks can a batch run at once?

Many: submit them all, then collect. Keep within the rate limits on the Rate limits page and put a daily spend cap on the key you use for batches.

### What happens if my script crashes halfway through a batch?

Run it again. Each row uses the same idempotency key as before, so rows that were already accepted return their original task instead of being charged twice.

## Related

- [n8n workflow](https://popnow.ai/docs/n8n): The same loop without code.
- [Upload your own files](media.md): Tickets, PUT and commit in detail.
- [Idempotency](idempotency.md): Why every recipe sends a key.
- [Recipes on popnow.ai](https://popnow.ai/api/workflows): These scripts generated for any model.
