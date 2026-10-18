<p align="center">
  <a href="https://popnow.ai">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="assets/popnow-wordmark-light.png">
      <source media="(prefers-color-scheme: light)" srcset="assets/popnow-wordmark.png">
      <img alt="PopNow" src="assets/popnow-wordmark.png" width="280">
    </picture>
  </a>
</p>

<h1 align="center">PopNow API — AI Video, Image &amp; Music Generation REST API (OpenAPI 3.1)</h1>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <a href="openapi.yaml"><img alt="OpenAPI 3.1" src="https://img.shields.io/badge/OpenAPI-3.1-6BA539.svg"></a>
  <a href="examples"><img alt="Examples: curl, Python, Node.js, n8n" src="https://img.shields.io/badge/examples-curl%20%7C%20Python%20%7C%20Node.js%20%7C%20n8n-orange.svg"></a>
  <a href="https://popnow.ai"><img alt="Website: popnow.ai" src="https://img.shields.io/badge/site-popnow.ai-ff5a5f.svg"></a>
</p>

**The PopNow API is a REST API that generates AI videos, images, music and speech from one API key and one credit wallet, with models such as Kling, Seedance, Wan, Vidu, MiniMax, Nano Banana, GPT Image, Flux and Suno.**

This repository contains the official [OpenAPI 3.1 spec](openapi.yaml), copy-paste examples in curl, Python and Node.js, an importable n8n workflow, and the API guides in plain Markdown. The API uses the same models, prices and credits as the [PopNow website](https://popnow.ai). Make it pop.

## Quickstart

1. **Get a key.** Sign in at [popnow.ai](https://popnow.ai), open the [API console](https://popnow.ai/api/console/keys), choose **Create key** and copy it (it is shown once).

   ```bash
   export POPNOW_API_KEY="sk-popnow-..."
   ```

2. **Create a task.** This asks a fast image model for one picture (about 2 credits) and waits up to 60 seconds for it:

   ```bash
   curl -X POST "https://api.popnow.ai/api/v1/jobs/createTask?wait=60" \
     -H "Authorization: Bearer $POPNOW_API_KEY" \
     -H "Content-Type: application/json" \
     -H "Idempotency-Key: $(uuidgen)" \
     -d '{"model": "alibaba/z-image-turbo/text-to-image", "input": {"prompt": "A small red fox curled up in a teacup, soft morning light", "aspect_ratio": "1:1"}}'
   ```

3. **Read the result.** `data.state` is `succeeded` and `data.output.assets[0].url` is a signed link to the file (valid for about 20 minutes, no key needed). Slower jobs — every video model — return `202` with `state: "queued"`; poll until the task is final:

   ```bash
   curl "https://api.popnow.ai/api/v1/jobs/recordInfo?taskId=job_..." \
     -H "Authorization: Bearer $POPNOW_API_KEY"
   ```

Full walkthrough: [docs/quickstart.md](docs/quickstart.md).

## What's in this repo

| Path | What it is |
| --- | --- |
| [`openapi.yaml`](openapi.yaml) | OpenAPI 3.1 contract for every public endpoint (tasks, models, account, media, assets, OpenAI-compatible) |
| [`examples/curl/`](examples/curl) | Bash scripts (curl + jq) |
| [`examples/python/`](examples/python) | Python 3.8+ scripts using only the standard library |
| [`examples/node/`](examples/node) | Node.js 18+ ES modules with no dependencies |
| [`examples/n8n/popnow-workflow.json`](examples/n8n/popnow-workflow.json) | n8n workflow: create a task, wait, poll, output the file URL |
| [`docs/`](docs) | The API guides as Markdown |
| [`llms.txt`](llms.txt), [`llms-full.txt`](llms-full.txt) | LLM-friendly index and full text of the docs (rebuild with `python3 scripts/build_llms.py`) |

### Examples

| Task | curl | Python | Node.js |
| --- | --- | --- | --- |
| List models and prices | [list-models.sh](examples/curl/list-models.sh) | [list_models.py](examples/python/list_models.py) | [list-models.mjs](examples/node/list-models.mjs) |
| Quote a price before running | [quote.sh](examples/curl/quote.sh) | [quote.py](examples/python/quote.py) | [quote.mjs](examples/node/quote.mjs) |
| Text to image | [text-to-image.sh](examples/curl/text-to-image.sh) | [text_to_image.py](examples/python/text_to_image.py) | [text-to-image.mjs](examples/node/text-to-image.mjs) |
| Image to video | [image-to-video.sh](examples/curl/image-to-video.sh) | [image_to_video.py](examples/python/image_to_video.py) | [image-to-video.mjs](examples/node/image-to-video.mjs) |
| Poll a task | [poll-job.sh](examples/curl/poll-job.sh) | [poll_job.py](examples/python/poll_job.py) | [poll-job.mjs](examples/node/poll-job.mjs) |
| Upload a local file | [upload-file.sh](examples/curl/upload-file.sh) | [upload_file.py](examples/python/upload_file.py) | [upload-file.mjs](examples/node/upload-file.mjs) |
| Receive a webhook | [webhook-verify.sh](examples/curl/webhook-verify.sh) (offline check) | [webhook_receiver.py](examples/python/webhook_receiver.py) | [webhook-receiver.mjs](examples/node/webhook-receiver.mjs) |

Every example reads `POPNOW_API_KEY` from the environment (and `POPNOW_WEBHOOK_SECRET` for webhooks). Set `POPNOW_API_BASE` to point them at another host.

## Supported models

The live list, with each model's input schema and price in credits, is `GET /api/v1/models` (`?modality=video`, `?task=image-to-video`, `?includeSchema=1`). A model ID has the form `<publisher>/<model>/<task>`. Some examples from the catalog:

| Family | Example model IDs | Tasks |
| --- | --- | --- |
| Kling | `kling/3.0/image-to-video`, `kling/3.0/text-to-video` | text-to-video, image-to-video, reference-to-video, character animation |
| Seedance | `bytedance/seedance-2.0/image-to-video`, `bytedance/seedance-2.0-fast/text-to-video` | text-to-video, image-to-video, reference-to-video, video extend |
| Wan | `alibaba/wan-3.0/image-to-video`, `alibaba/wan-3.0/text-to-video` | text-to-video, image-to-video, video extend, image generation |
| Vidu | `vidu/q3/image-to-video`, `vidu/q3-turbo/video-extend` | image-to-video, video extend |
| MiniMax | `minimax/h3/image-to-video`, `minimax/h3/text-to-video` | text-to-video, image-to-video, video extend |
| Nano Banana | `google/nano-banana-2.1/text-to-image`, `google/nano-banana-2.1/edit` | text-to-image, image editing |
| GPT Image | `openai/gpt-image-2/text-to-image`, `openai/gpt-image-2/edit` | text-to-image, image editing |
| Flux | `black-forest-labs/flux-2-pro/text-to-image`, `black-forest-labs/flux-2-pro/edit` | text-to-image, image editing, LoRA |
| Z-Image, Qwen Image | `alibaba/z-image-turbo/text-to-image`, `alibaba/qwen-image-3.0/edit` | text-to-image, image editing |
| Suno | `suno/v6/text-to-audio` | music generation |
| Speech | `google/gemini-3.8-flash-tts/text-to-speech`, `alibaba/qwen-3-tts/text-to-speech` | text-to-speech |

The catalog changes as models are added; always check `GET /api/v1/models` before hard-coding an ID.

## How the API works

```text
POST /api/v1/jobs/quote        (optional)  price check, nothing is held
POST /api/v1/jobs/createTask   -> 202 { taskId, state: "queued", estimatedCredits }
GET  /api/v1/jobs/recordInfo   -> { state: "succeeded" | "failed" | "expired", output.assets[].url }
     or receive the same record at your callBackUrl (signed webhook)
```

- **Base URL:** `https://api.popnow.ai`. Native endpoints live under `/api/v1`; OpenAI-compatible ones under `/v1`.
- **Authentication:** `Authorization: Bearer sk-popnow-...` on every request. Keep keys on your server. See [docs/authentication.md](docs/authentication.md).
- **Envelope:** every native JSON response is `{ "code", "msg", "data", "request_id" }`. `code: 200` is success; branch on `code`, never on `msg`. Quote `request_id` to support.
- **Credits:** 1 credit = US$0.01, the same wallet and prices as popnow.ai. Credit packs, no subscription. `createTask` holds the maximum price; the final charge is never higher, and failed or expired tasks are not charged. See [pricing](https://popnow.ai/pricing).
- **Idempotency:** send an `Idempotency-Key` on `createTask` and reuse it on every retry, so a timeout never generates or charges twice. See [docs/idempotency.md](docs/idempotency.md).
- **Files:** pass a public HTTPS URL, a small Base64 data URI, or upload first and pass `popnow://f/fil_...`. See [docs/media.md](docs/media.md).
- **Webhooks:** add `callBackUrl` and verify `X-Webhook-Signature` (HMAC-SHA256). See [docs/webhooks.md](docs/webhooks.md).

## Error handling

Errors use the same envelope with a business `code`. The ones worth retrying (with backoff, honouring `Retry-After`, and the **same** `Idempotency-Key`) are `429`, `500`, `503` and `50301`. Everything else means "fix the request" or "a person needs to act":

| `code` | Meaning | What to do |
| --- | --- | --- |
| `400` | Invalid request or `input`; `msg` names the field | Fix it, do not retry |
| `401` | Missing, malformed or revoked key | Check the `Authorization` header |
| `40201` | Not enough credits for this task's hold | Buy credits, then send again |
| `40202` | A key spend cap was reached | Raise the cap in the API console |
| `40301` / `40302` | Key not allowed to call this model / IP not allowed | Adjust the key's restrictions |
| `409` / `40901` | Idempotency conflict / quote expired or price changed | See [docs/errors.md](docs/errors.md) |
| `429` | Too many requests | Wait `Retry-After` seconds and retry |

A task that fails after it was accepted has `state: "failed"` with a stable `errorCode` (for example `content_rejected` or `invalid_asset`) and a readable `errorMessage`. Full list: [docs/errors.md](docs/errors.md). Rate limits: [docs/limits.md](docs/limits.md).

## OpenAI-compatible `/v1` endpoints

If your code already speaks the OpenAI Videos API, point it at `https://api.popnow.ai/v1`. These endpoints share keys, limits, validation and credits with the native API but return OpenAI-shaped objects and errors.

| Call | Does |
| --- | --- |
| `POST /v1/videos` | Create a video task |
| `GET /v1/videos/{id}` | Read its state (`queued`, `in_progress`, `completed`, `failed`) |
| `GET /v1/videos/{id}/content` | `302` redirect to the finished file |
| `GET /v1/models` | List callable models in OpenAI's list shape |

```bash
curl -X POST "https://api.popnow.ai/v1/videos" \
  -H "Authorization: Bearer $POPNOW_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "model": "alibaba/wan-3.0/image-to-video",
    "prompt": "Waves roll in slowly, the camera drifts toward the lighthouse",
    "input_reference": "https://media.popnow.ai/movie/lighthouse.webp",
    "seconds": "5",
    "size": "1280x720"
  }'
```

With the official OpenAI Python SDK, only `base_url` and the key change:

```python
import os
from openai import OpenAI

client = OpenAI(base_url="https://api.popnow.ai/v1", api_key=os.environ["POPNOW_API_KEY"])
for model in client.models.list():
    print(model.id)
```

Only video, image and audio models are offered; there are no chat or text endpoints. Prices are not in the OpenAI-shaped objects — read them with the native `recordInfo` using the same ID. Details: [docs/openai-videos.md](docs/openai-videos.md).

## Import into Postman, Insomnia or a code generator

The spec is a standard OpenAPI 3.1 document, so most API tools can import it directly:

- **Postman:** *Import* → *Link* → `https://raw.githubusercontent.com/popnow-ai/popnow-api/main/openapi.yaml` (or drop in the downloaded `openapi.yaml`). Set a collection variable for the key and use *Bearer Token* auth.
- **Insomnia:** *Create* → *Import* → *From URL* with the same link, then add a Bearer token in the environment.
- **Code generators** (openapi-generator, oapi-codegen, openapi-typescript, ...): point them at `openapi.yaml`.

The same file is published at <https://popnow.ai/docs/openapi.yaml>, and an interactive reference is at <https://popnow.ai/docs/api-reference>. Each model's own `input` schema is not inlined in the spec; fetch it with `GET /api/v1/models/{model}`.

## Docs

| Guide | Covers |
| --- | --- |
| [Quickstart](docs/quickstart.md) | Key, first request, reading the result |
| [Authentication](docs/authentication.md) | Key format, restrictions, rotation, leaks |
| [Tasks](docs/tasks.md) | States, `wait`, polling, task list, retry, purge |
| [Media](docs/media.md) | URLs, inline images, uploads, downloads |
| [Webhooks](docs/webhooks.md) | Callbacks, signatures, retries, account endpoints |
| [Idempotency](docs/idempotency.md) | Safe retries without double charges |
| [Errors](docs/errors.md) | Every business code and whether to retry |
| [Rate limits](docs/limits.md) | Request limits and response headers |
| [Assets and LoRA files](docs/assets.md) | Long-term asset library, characters, LoRA weights |
| [Recipes](docs/recipes.md) | Batch images from CSV, photo to video, voiceovers, Slack alerts |
| [Production checklist](docs/production-integration.md) | What to check before launch |
| [ComfyUI](docs/comfyui.md) | A custom node that runs PopNow models in a ComfyUI graph |
| [OpenAI Videos compatibility](docs/openai-videos.md) | The `/v1` endpoints |

The canonical, always-current docs are at <https://popnow.ai/docs>.

## FAQ

### How do I generate a video from an image with an API?

Send `POST /api/v1/jobs/createTask` with an image-to-video model such as `alibaba/wan-3.0/image-to-video` and an `input` containing `image_url` and `prompt`, then poll `GET /api/v1/jobs/recordInfo?taskId=...` until `state` is `succeeded` and download `output.assets[0].url`. See [examples/python/image_to_video.py](examples/python/image_to_video.py).

### Which AI video and image models does the PopNow API support?

Video models include Kling, Seedance, Wan, Vidu and MiniMax; image models include Nano Banana, GPT Image, Flux, Qwen Image and Z-Image; audio includes Suno music and several text-to-speech models. `GET /api/v1/models` returns the live list with prices.

### How much does the PopNow API cost?

You pay per generation in credits (1 credit = US$0.01) from the same wallet as the website, with no subscription or separate API plan. Each model's price is in `GET /api/v1/models`, `POST /api/v1/jobs/quote` prices a specific request, and failed or expired tasks are not charged. Credit packs: <https://popnow.ai/pricing>.

### Can I use the OpenAI SDK with PopNow?

Yes, for video generation and model listing. Set `base_url` to `https://api.popnow.ai/v1` and use your `sk-popnow-...` key. Chat and text endpoints are not offered.

### How do I upload a local image or video to use as input?

Call `POST /api/v1/common/upload-url` with the content type and byte size, `PUT` the bytes to the returned `uploadUrl` with the returned headers, then `POST /api/v1/files/{fileId}/commit` and pass the returned `popnow://f/...` URI in the model's media field. See [examples/node/upload-file.mjs](examples/node/upload-file.mjs).

### How do I verify PopNow webhook signatures?

Compute `base64(HMAC-SHA256(secret, "<taskId>.<X-Webhook-Timestamp>.<sha256_hex(raw_body)>"))` over the raw request body and compare it with `X-Webhook-Signature` in constant time; reject timestamps older than five minutes. See [examples/python/webhook_receiver.py](examples/python/webhook_receiver.py).

### Is there an MCP server for ChatGPT, Claude or Cursor?

Yes. PopNow runs a remote MCP server at `https://api.popnow.ai/mcp` (Streamable HTTP, OAuth or a Bearer API key) with tools for images, video, music, speech, effects and job status. Setup: <https://popnow.ai/mcp> and [popnow-mcp](https://github.com/popnow-ai/popnow-mcp).

### Can I use the API from n8n without code?

Yes. Import [examples/n8n/popnow-workflow.json](examples/n8n/popnow-workflow.json), create a Header Auth credential with `Authorization: Bearer sk-popnow-...`, and select it in the two HTTP Request nodes.

## Links

- Website: <https://popnow.ai>
- Docs: <https://popnow.ai/docs>
- API reference: <https://popnow.ai/docs/api-reference>
- Pricing: <https://popnow.ai/pricing>
- MCP server: <https://popnow.ai/mcp>
- Other PopNow repos:
  [popnow-mcp](https://github.com/popnow-ai/popnow-mcp) ·
  [popnow-skills](https://github.com/popnow-ai/popnow-skills) ·
  [popnow-python](https://github.com/popnow-ai/popnow-python) ·
  [popnow-js](https://github.com/popnow-ai/popnow-js) ·
  [popnow-blender](https://github.com/popnow-ai/popnow-blender)

## License

Everything in this repository — the OpenAPI spec, the examples, the docs and the scripts — is provided under the [MIT License](LICENSE). Using the PopNow service itself is governed by the [PopNow terms](https://popnow.ai/terms). The PopNow name and logo are not covered by the license.
