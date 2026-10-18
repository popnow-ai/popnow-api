# OpenAI Videos compatibility

> Call PopNow video models with the request and response shapes of the OpenAI Videos API.

Online version: <https://popnow.ai/docs/openai-videos>

If your code already speaks the OpenAI Videos API, you can point it at PopNow and keep most of it. The compatible endpoints live under `https://api.popnow.ai/v1` and share keys, limits, validation and credits with the native API.

| OpenAI-style call             | Does                                        |
| ----------------------------- | ------------------------------------------- |
| `POST /v1/videos`             | Create a video task                         |
| `GET /v1/videos/{id}`         | Read its state                              |
| `GET /v1/videos/{id}/content` | Redirect (`302`) to the finished file       |
| `GET /v1/models`              | List callable models in OpenAI's list shape |

Only video, image and audio models are listed; chat and text endpoints are not part of the PopNow API.

## Create a video

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

How the fields map onto the model's own input:

| OpenAI field            | Becomes                                                                               |
| ----------------------- | ------------------------------------------------------------------------------------- |
| `model`                 | A video model ID from `/v1/models`                                                    |
| `prompt`                | `prompt`                                                                              |
| `input_reference`       | `image_url` / `image_urls` (an HTTPS URL or a `popnow://` upload)                     |
| `seconds`               | `duration_seconds`                                                                    |
| `size` (`WIDTHxHEIGHT`) | `resolution` and/or `aspect_ratio`, or `width` / `height` when the model takes pixels |

A field the chosen model does not support is rejected with `400`, never silently dropped. For settings OpenAI's shape has no field for, use the native [createTask](tasks.md).

## Read and download

States map as `queued` → `queued`, `running` → `in_progress`, `succeeded` → `completed`, and `failed` / `expired` → `failed` with an `error` object. `GET /v1/videos/{id}/content` answers `302` to a short-lived signed link — follow redirects in your client — `409` while the video is still being made, and `404` if it failed.

The returned objects never contain prices. Read the cost with the native [`recordInfo`](tasks.md#read-a-task), using the same ID.

## Errors

Errors use OpenAI's `{ "error": { "message", "type", "param", "code" } }` shape with the same HTTP status the native API would return. A content refusal is HTTP `400` with `code: "content_rejected"`, so you can tell it apart from a parameter error (`invalid_request` or `unsupported_parameter`, with `param` naming the field).
