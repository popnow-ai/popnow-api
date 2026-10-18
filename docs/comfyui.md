# ComfyUI node for cloud generation

> Run cloud AI image, video and audio models inside ComfyUI with one custom node file and the PopNow API. No GPU or model downloads; install steps, inputs, pricing and error fixes.

Online version: <https://popnow.ai/docs/comfyui>

One small custom node puts every PopNow image, video and audio model into a ComfyUI graph. It sends the job to the cloud, waits, and hands the result to the next node: an `IMAGE` for image models, a saved file for video and audio. Nothing is downloaded to your GPU, so video models that need far more memory than a laptop has run fine from a laptop.

This page matches the [ComfyUI page on popnow.ai](https://popnow.ai/api/comfyui), which fills in the node's defaults for the model you pick.

## Install in four steps

### Save the node file

Save the code below as `custom_nodes/popnow_api.py` inside your ComfyUI folder. It uses only `requests`, Pillow, NumPy and PyTorch, which ComfyUI already ships.

### Set your API key

Create a key in the [API console](https://popnow.ai/api/console/keys) and set it in the environment you start ComfyUI from:

```bash
export POPNOW_API_KEY="sk-popnow-..."
python main.py
```

On Windows portable builds, add `set POPNOW_API_KEY=sk-popnow-...` to the `.bat` file that starts ComfyUI.

### Restart and add the node

Restart ComfyUI, double-click the canvas, search for **PopNow** and add **PopNow Generate**.

### Queue

Type a model ID and a prompt, connect the `image` output to a Preview or Save node, and queue the prompt.

## The node

Read it before you run it; it is short on purpose.

**custom_nodes/popnow_api.py**

```python title="custom_nodes/popnow_api.py"
"""PopNow API node for ComfyUI.

Save as ComfyUI/custom_nodes/popnow_api.py, set POPNOW_API_KEY, restart ComfyUI.
Runs any PopNow image, video or audio model in the cloud and returns the result.
Docs: https://popnow.ai/docs/comfyui
"""
import io
import json
import os
import time
import uuid

import numpy as np
import requests
import torch
from PIL import Image

import folder_paths

BASE = "https://api.popnow.ai/api/v1"
TERMINAL = ("succeeded", "failed", "canceled", "expired")

def _headers(extra=None):
    key = os.environ.get("POPNOW_API_KEY")
    if not key:
        raise RuntimeError("Set POPNOW_API_KEY before starting ComfyUI")
    return {"Authorization": f"Bearer {key}", **(extra or {})}

def _call(method, path, **kwargs):
    headers = _headers(kwargs.pop("headers", None))
    body = requests.request(method, BASE + path, headers=headers, timeout=60, **kwargs).json()
    if body.get("code") != 200:
        raise RuntimeError(f'PopNow {body.get("code")}: {body.get("msg")}')
    return body["data"]

def _upload(image):
    """IMAGE tensor -> PNG -> upload -> popnow:// reference."""
    arr = (image[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    data = buf.getvalue()
    ticket = _call("POST", "/common/upload-url", json={"contentType": "image/png", "bytes": len(data)})
    requests.put(ticket["uploadUrl"], data=data, headers=ticket.get("headers", {}), timeout=120).raise_for_status()
    return _call("POST", f'/files/{ticket["fileId"]}/commit')["uri"]

class PopNowGenerate:
    CATEGORY = "PopNow"
    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("image", "url", "path")
    FUNCTION = "run"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("STRING", {"default": "google/nano-banana-2.1/text-to-image"}),
                "prompt": ("STRING", {"multiline": True, "default": "A lighthouse on a cliff at dusk, warm window light"}),
                "options": ("STRING", {"multiline": True, "default": '{"aspect_ratio": "16:9", "resolution": "1k"}'}),
            },
            "optional": {
                "image": ("IMAGE",),
                "image_field": ("STRING", {"default": "image_url"}),
            },
        }

    def run(self, model, prompt, options, image=None, image_field="image_url"):
        task_input = json.loads(options or "{}")
        if prompt.strip():
            task_input.setdefault("prompt", prompt)
        if image is not None:
            ref = _upload(image)
            task_input[image_field] = [ref] if image_field.endswith("s") else ref

        task_id = _call(
            "POST",
            "/jobs/createTask",
            headers={"Idempotency-Key": str(uuid.uuid4())},
            json={"model": model, "input": task_input},
        )["taskId"]

        delay = 2.0
        while True:
            time.sleep(delay)
            task = _call("GET", "/jobs/recordInfo", params={"taskId": task_id})
            assets = (task.get("output") or {}).get("assets") or []
            copying = any(a.get("pending") and not a.get("unavailable") for a in assets)
            if task["state"] in TERMINAL and not copying:
                break
            delay = min(delay * 1.5, 15.0)
        if task["state"] != "succeeded" or not assets:
            raise RuntimeError(f'PopNow {task["state"]}: {task.get("errorMessage", "no detail")}')

        asset = assets[0]
        content = requests.get(asset["url"], timeout=300).content
        mime = asset.get("mime", "")
        if mime.startswith("image/"):
            pil = Image.open(io.BytesIO(content)).convert("RGB")
            tensor = torch.from_numpy(np.asarray(pil).astype(np.float32) / 255.0)[None,]
            return (tensor, asset["url"], "")

        ext = {"video/mp4": ".mp4", "video/webm": ".webm", "audio/mpeg": ".mp3", "audio/wav": ".wav"}.get(mime, ".bin")
        path = os.path.join(folder_paths.get_output_directory(), f"popnow_{task_id}{ext}")
        with open(path, "wb") as f:
            f.write(content)
        # Video and audio: a small blank IMAGE keeps the graph valid; use the path output.
        return (torch.zeros((1, 64, 64, 3)), asset["url"], path)

NODE_CLASS_MAPPINGS = {"PopNowGenerate": PopNowGenerate}
NODE_DISPLAY_NAME_MAPPINGS = {"PopNowGenerate": "PopNow Generate"}
```

## Inputs and outputs

| Input              | What to put in it                                                                                                           |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| `model`            | A model ID from [Models](https://popnow.ai/docs/models), for example `google/nano-banana-2.1/text-to-image` or `minimax/h3/image-to-video`   |
| `prompt`           | What to make. Leave it empty for models that take no prompt                                                                 |
| `options`          | The model's other fields as JSON, such as `{"resolution": "2k"}` or `{"duration_seconds": 5}`. Each model's page lists them |
| `image` (optional) | An `IMAGE` from another node. It is uploaded for you and placed in the field named by `image_field`                         |
| `image_field`      | Which field gets the image: `image_url` for most video models, `image_urls` for image editing                               |

| Output  | Contains                                                                           |
| ------- | ---------------------------------------------------------------------------------- |
| `image` | The result as an `IMAGE` for image models; a blank placeholder for video and audio |
| `url`   | The signed file URL, valid for about 20 minutes                                    |
| `path`  | For video and audio: where the file was saved in ComfyUI's output folder           |

## Common setups

| Goal                | `model`                                | `options`                                       | `image_field` |
| ------------------- | -------------------------------------- | ----------------------------------------------- | ------------- |
| Text to image       | `google/nano-banana-2.1/text-to-image` | `{"aspect_ratio": "16:9", "resolution": "1k"}`  | —             |
| Edit a local render | `google/nano-banana-2.1/edit`          | `{"resolution": "2k"}`                          | `image_urls`  |
| Animate a still     | `minimax/h3/image-to-video`            | `{"duration_seconds": 5, "resolution": "768p"}` | `image_url`   |
| Upscale a frame     | `popnow/image-upscaler-v1/upscale`     | `{}`                                            | `image_url`   |
| Cut out the subject | `popnow/background-remover-v1/edit`    | `{}`                                            | `image_url`   |

A typical hybrid graph: make a start frame with a local checkpoint, animate it in the cloud with an image-to-video model, then load the saved MP4 back with a video loader node and upscale or interpolate it locally.

## What the node does under the hood

The node is a thin wrapper over three REST calls; the same calls in other languages:

```bash
curl -X POST "https://api.popnow.ai/api/v1/jobs/createTask" \
  -H "Authorization: Bearer $POPNOW_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"model": "google/nano-banana-2.1/text-to-image", "input": {"prompt": "A lighthouse on a cliff at dusk, warm window light", "aspect_ratio": "16:9", "resolution": "1k"}}'

curl "https://api.popnow.ai/api/v1/jobs/recordInfo?taskId=job_..." \
  -H "Authorization: Bearer $POPNOW_API_KEY"
```

```javascript title="JavaScript"
const API = 'https://api.popnow.ai/api/v1';
const auth = { Authorization: `Bearer ${process.env.POPNOW_API_KEY}` };
const created = await fetch(`${API}/jobs/createTask`, {
  method: 'POST',
  headers: { ...auth, 'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID() },
  body: JSON.stringify({
    model: 'google/nano-banana-2.1/text-to-image',
    input: { prompt: 'A lighthouse on a cliff at dusk, warm window light', aspect_ratio: '16:9', resolution: '1k' },
  }),
}).then((r) => r.json());
console.log(created.data.taskId);
```

Uploading the input image is the three-step flow on [Media](media.md#upload-a-file); the result is a `popnow://f/…` reference that only works with keys on your own account.

## Pricing

Each run costs the model's normal price in credits; the node adds nothing. Nano Banana 2.1 at 1K is 8 credits per image, MiniMax H3 at 768p is 28 credits for 5 seconds. Failed runs are not charged. Prices for every model are on its page and in [Credits and refunds](https://popnow.ai/docs/credits-and-refunds); use [`jobs/quote`](https://popnow.ai/docs/billing#quote) for an exact figure.

## Common errors

| ComfyUI shows                                | Why                                                                      | Fix                                                               |
| -------------------------------------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| `Set POPNOW_API_KEY before starting ComfyUI` | The variable is not in ComfyUI's environment                             | Set it in the same shell or `.bat` file, then restart             |
| `PopNow 401: …`                              | Key missing, mistyped or revoked                                         | Create a new key in the API console                               |
| `PopNow 400: …` naming a field               | `options` has a field the model does not accept, or a value out of range | Check the model's page; unknown fields are rejected               |
| `PopNow 40201: …`                            | Not enough credits                                                       | Top up, or lower the resolution or length                         |
| `PopNow failed: …`                           | The model could not finish or declined the request                       | Nothing was charged; change the prompt or settings                |
| `JSONDecodeError`                            | `options` is not valid JSON                                              | Use double quotes: `{"resolution": "2k"}`                         |
| Node not in the search list                  | The file is not in `custom_nodes`, or ComfyUI was not restarted          | Check the path and restart; look for import errors in the console |

### Is this an official package on the ComfyUI registry?

No. It is a single file published here and on popnow\.ai. Copy it, read it, and update it from this page when the API changes.

### Does it work with ComfyUI Desktop and portable builds?

Yes. It works anywhere you can add a custom node and set an environment variable: portable, Desktop and self-hosted servers.

### Do I need a GPU?

No. Generation runs on PopNow's side; your machine only sends the request and receives the file.

### How do I get video frames back into the graph?

The node saves the video to ComfyUI's output folder and returns its path. Load it with a video loader node to get frames.

## Related

- [Blender add-on](https://popnow.ai/docs/blender): Clay renders to AI images and video inside Blender.
- [n8n](https://popnow.ai/docs/n8n): The same calls as a no-code workflow.
- [Models](https://popnow.ai/docs/models): Every model ID, its fields and its price.
- [ComfyUI on popnow.ai](https://popnow.ai/api/comfyui): The node with defaults for any model.
