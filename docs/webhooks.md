# Webhooks

> Receive finished tasks at your own URL, verify the signature, and handle retries and duplicates.

Online version: <https://popnow.ai/docs/webhooks>

A webhook lets PopNow tell you when a task is done, so you do not have to keep asking. There are two kinds:

|           | Task callback                      | Account endpoint                                            |
| --------- | ---------------------------------- | ----------------------------------------------------------- |
| Set up    | `callBackUrl` on each `createTask` | Once, in the API console                                    |
| Sent for  | That one task                      | Every task on the account that matches the events you chose |
| Signature | `X-Webhook-Signature` (below)      | Standard Webhooks headers ([see below](#account-endpoints)) |

Most integrations only need the task callback.

## 1. Get your signing secret

Every delivery is signed with your account's webhook signing secret. Open the **Webhooks** page of the [API console](https://popnow.ai/api/console/webhooks), generate (or rotate) the secret and store it on your server as `POPNOW_WEBHOOK_SECRET`. It is shown only once. Rotating takes effect immediately, including for deliveries still being retried, so update your receivers right after.

## 2. Pass `callBackUrl`

```json
{
  "model": "alibaba/wan-3.0/image-to-video",
  "input": { "image_url": "https://media.popnow.ai/movie/lighthouse.webp" },
  "callBackUrl": "https://your-app.example.com/hooks/popnow"
}
```

The URL must be public **HTTPS** on port 443 (or no port), without a username or password, and resolve only to public addresses — checked when you create the task and again when we connect. `http://localhost` cannot work; use a tunnel such as ngrok while developing, or poll. An invalid URL returns `400` with `msg: "Invalid callback URL"`.

## 3. What arrives

When the task reaches a final state, PopNow sends one `POST`:

```http
POST /hooks/popnow HTTP/1.1
Content-Type: application/json
User-Agent: PopNow-Webhook/1
X-Webhook-Timestamp: 1787045531
X-Webhook-Signature: 9tXk3…=
X-Webhook-Payload-Version: 2
```

The body is exactly what `recordInfo` would return for the task:

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "taskId": "job_01JH8Z4Q5W2N7R3K9M6P1C0VXD",
    "model": "alibaba/wan-3.0/image-to-video",
    "state": "succeeded",
    "output": { "assets": [{ "url": "https://…", "mime": "video/mp4", "durationSeconds": 5 }] },
    "credits": 225,
    "cost": "0.225",
    "settled": true
  },
  "request_id": "whd_01JH8Z…"
}
```

* `code` is `200` even for a failed task: it describes the delivery, not the task. Read `data.state`.
* `request_id` is the **delivery ID**. It stays the same across retries, so use it to ignore duplicates.
* The signed links in `output` expire after about 20 minutes. Store the `taskId`, not the link.

## 4. Verify the signature

```text
signature = base64( HMAC-SHA256( secret, "<taskId>.<timestamp>.<sha256_hex(raw_body)>" ) )
```

`taskId` is `data.taskId` from the body, `timestamp` is the `X-Webhook-Timestamp` header, and the last part is the SHA-256 of the **raw** request body in lowercase hex. Hash the bytes you received, not a re-serialised object: key order and whitespace would change the result.

```javascript title="Node.js (Express)"
import crypto from 'node:crypto';
import express from 'express';

const app = express();
const SECRET = process.env.POPNOW_WEBHOOK_SECRET;

// express.raw keeps the exact bytes; express.json would throw them away.
app.post('/hooks/popnow', express.raw({ type: 'application/json', limit: '10mb' }), (req, res) => {
  const ts = Number(req.headers['x-webhook-timestamp']);
  const sig = String(req.headers['x-webhook-signature'] ?? '');
  // Refuse anything older than five minutes, however valid its signature.
  if (!Number.isInteger(ts) || Math.abs(Date.now() / 1000 - ts) > 300) return res.status(401).end();

  let event;
  try { event = JSON.parse(req.body.toString('utf8')); } catch { return res.status(400).end(); }
  const digest = crypto.createHash('sha256').update(req.body).digest('hex');
  const expected = crypto.createHmac('sha256', SECRET)
    .update(`${event.data?.taskId}.${ts}.${digest}`).digest('base64');
  const ok = expected.length === sig.length && crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(sig));
  if (!ok) return res.status(401).end();

  res.status(200).end();          // acknowledge first…
  enqueue(event.request_id, event.data); // …then do the work
});
```

```python title="Python (Flask)"
import hashlib, hmac, base64, json, os, time
from flask import Flask, request, abort

app = Flask(__name__)
SECRET = os.environ["POPNOW_WEBHOOK_SECRET"].encode()

@app.post("/hooks/popnow")
def popnow_hook():
    raw = request.get_data()  # the exact bytes
    ts = request.headers.get("X-Webhook-Timestamp", "")
    sig = request.headers.get("X-Webhook-Signature", "")
    if not ts.isdigit() or abs(time.time() - int(ts)) > 300:
        abort(401)
    event = json.loads(raw)
    digest = hashlib.sha256(raw).hexdigest()
    message = f'{event["data"]["taskId"]}.{ts}.{digest}'.encode()
    expected = base64.b64encode(hmac.new(SECRET, message, hashlib.sha256).digest()).decode()
    if not hmac.compare_digest(expected, sig):
        abort(401)
    enqueue(event["request_id"], event["data"])  # do the slow work elsewhere
    return "", 200
```

`X-Webhook-Payload-Version` is `2` for every new integration. Version `1` is an older format kept for existing receivers; if you ever see it, the task ID is the top-level `task_id`.

## Respond quickly

Any **2xx** within 15 seconds counts as received. Anything else — another status, a timeout, a refused connection — is retried. Acknowledge first and do the slow work (downloading, transcoding, notifying users) in a background job.

## Retries and duplicates

A failed delivery is retried 7 more times, after 10 s, 30 s, 2 min, 10 min, 30 min, 2 h and 6 h. Each retry is signed again with a fresh timestamp, so always check the timestamp against the current time rather than the first attempt. After the last retry the delivery is marked failed in the API console, where you can send it again by hand.

The same task can therefore arrive more than once. Make your handler idempotent: store `request_id` with a unique index, and when you see one again, answer `200` and do nothing.

If your server was down for longer than the retry window, list recent tasks with [`GET /api/v1/jobs`](tasks.md#the-task-list) and read any you missed with `recordInfo`.

## Account endpoints

An account endpoint is a URL registered once in the API console together with the events it wants. It receives events for every task on the account, so you never pass `callBackUrl` again.

| Event            | Sent when                                                                   |
| ---------------- | --------------------------------------------------------------------------- |
| `task.completed` | Any of the four below. Subscribe to this unless you need to tell them apart |
| `task.succeeded` | A task finished successfully                                                |
| `task.failed`    | A task failed; the hold was released                                        |
| `task.expired`   | A task passed its deadline; the hold was released                           |
| `task.canceled`  | Kept for old records only                                                   |

Deliveries follow the [Standard Webhooks](https://www.standardwebhooks.com/) format, so off-the-shelf libraries work:

```text
webhook-id: msg_01k3m8x9q2z4v7n5p6r8s0t1w3
webhook-timestamp: 1787045531
webhook-signature: v1,base64( HMAC-SHA256( key, "<webhook-id>.<webhook-timestamp>.<raw_body>" ) )
```

Two differences from the task callback: the **body itself** is signed (no SHA-256 step), and the HMAC key is the Base64-decoded part of the secret after `whsec_` — not the secret string. During a secret rotation the header can hold two space-separated signatures; accept the request if either matches. `webhook-id` stays the same across retries: use it to ignore duplicates. The event's `data.object` is the task record at the moment the event was created.

With an off-the-shelf Standard Webhooks library the check is one call:

```python title="Python (pip install standardwebhooks)"
import os
from flask import Flask, request
from standardwebhooks.webhooks import Webhook

app = Flask(__name__)
wh = Webhook(os.environ["POPNOW_ENDPOINT_SECRET"])  # the whsec_… secret of this endpoint

@app.post("/hooks/popnow-events")
def events():
    event = wh.verify(request.get_data(), dict(request.headers))  # raises if the signature is wrong
    task = event["data"]["object"]
    print(event["type"], task["taskId"], task["state"])
    return "", 200
```

```javascript title="Node.js (npm install standardwebhooks)"
import express from 'express';
import { Webhook } from 'standardwebhooks';

const wh = new Webhook(process.env.POPNOW_ENDPOINT_SECRET);
const app = express();
app.post('/hooks/popnow-events', express.raw({ type: 'application/json' }), (req, res) => {
  let event;
  try { event = wh.verify(req.body.toString('utf8'), req.headers); } catch { return res.status(401).end(); }
  res.status(200).end();
  console.log(event.type, event.data.object.taskId, event.data.object.state);
});
app.listen(3000);
```

### Manage endpoints in the console

The **Webhooks** page of the [API console](https://popnow.ai/api/console/webhooks) holds both kinds of setup:

* **Endpoints:** up to 16 per account, each with its own URL, description, event list and `whsec_` secret. Rotate a secret at any time; for a grace period you choose (up to 7 days) both the old and the new secret sign each delivery, so receivers can switch without dropping events. Account endpoint deliveries carry `User-Agent: PopNow-Webhook/2`.
* **Deliveries:** every attempt for both kinds, with the HTTP status your server returned and when the next retry is due. A delivery that used up its retries can be sent again by hand.
* **Signing secret** for task callbacks (`POPNOW_WEBHOOK_SECRET`), generated and rotated on the same page.

## Task states in a webhook

A webhook only fires when a task reaches a **final** state; `queued` and `running` are never delivered.

| `data.state` | Meaning                                                                    | Credits                            |
| ------------ | -------------------------------------------------------------------------- | ---------------------------------- |
| `succeeded`  | Files are in `output.assets`                                               | The actual price, at most the hold |
| `failed`     | The model could not finish or declined the request; `errorCode` says which | Nothing; the hold is released      |
| `expired`    | The task passed its deadline                                               | Nothing; the hold is released      |

`canceled` exists only on old records. The full lifecycle, `wait` and polling are on [Tasks](tasks.md#states); refunds of failed tasks are on [Credits and refunds](https://popnow.ai/docs/credits-and-refunds#failed-tasks).

## Troubleshooting

| Symptom                                      | Likely cause                                                                   | Fix                                                                                                  |
| -------------------------------------------- | ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| `400` “Invalid callback URL” on `createTask` | `http://`, a port other than 443, credentials in the URL, or a private address | Use a public HTTPS URL; tunnel while developing                                                      |
| Nothing arrives                              | Your server returned non-2xx or timed out; deliveries are still being retried  | Check the delivery log in the console; answer within 15 seconds                                      |
| Signature never matches                      | You hashed parsed JSON instead of the raw bytes, or used the wrong secret      | Keep the raw body (`express.raw`, `request.get_data()`), and use the secret for this kind of webhook |
| Signature stopped matching today             | The secret was rotated                                                         | Update `POPNOW_WEBHOOK_SECRET` or the endpoint secret on your server                                 |
| The same task arrives twice                  | A retry after a slow or failed acknowledgement                                 | Store `request_id` (task callback) or `webhook-id` (endpoint) and ignore repeats                     |
| The file link in the body returns `403`      | Signed links last about 20 minutes                                             | Read the task again with `recordInfo` for a fresh link                                               |

### Do I need webhooks, or can I poll?

Either works. Polling recordInfo every few seconds is fine for scripts; webhooks are better for production because you hear about every task without keeping connections open.

### Which secret signs which webhook?

Task callbacks set with callBackUrl are signed with the account's webhook signing secret. Account endpoints each have their own whsec\_ secret and use the Standard Webhooks format.

### How long does PopNow retry a failed delivery?

Seven retries over about nine hours: after 10 seconds, 30 seconds, 2 minutes, 10 minutes, 30 minutes, 2 hours and 6 hours. After that the delivery can be resent by hand from the console.

### Do webhooks cost credits?

No. Deliveries, retries and reading tasks are free; only the generation itself is charged.
