# Media

> Send reference images, video and audio by URL, inline or by upload, and download the files a task produces.

Online version: <https://popnow.ai/docs/media>

Many models take files as input — a photo to animate, a clip to extend, a voice sample, a song. There are four ways to hand one over, and one way to get results back.

## Four ways to send a file

| You have                     | Send it as                                                | Best for                                                      |
| ---------------------------- | --------------------------------------------------------- | ------------------------------------------------------------- |
| A public HTTPS link          | The URL itself, e.g. `"image_url": "https://…/photo.jpg"` | Files you already host                                        |
| A small image in memory      | A data URI, e.g. `"image_url": "data:image/png;base64,…"` | Quick tests, images under 1 MiB                               |
| A local file                 | An upload, then `"image_url": "popnow://f/fil_…"`         | Anything else, including video and audio                      |
| A file in your asset library | `"image_url": "popnow://a/ast_…"`                         | Files you reuse across many tasks. See [Assets](assets.md) |

Whichever you choose, the file goes in the field the model's schema declares for it (`image_url`, `image_urls`, `video_url`, `audio_url` …).

### Public links

The link must return **the file itself** and stay reachable without login while the task runs. A share page from a cloud drive or social network returns a web page, not the file, and the task fails with `invalid_asset`; download the file and upload it instead.

### Inline images

Images can be sent as a standard Base64 data URI with its MIME type: JPEG, PNG, WebP or GIF, at most 1 MiB decoded and 8,192 pixels per side each, up to 16 images per request, and the whole JSON body under 2 MiB. Bare Base64, SVG and inline video or audio are not accepted. Inline images are stored as uploads on your account, so the task's `input` shows a `popnow://` URI instead of echoing the bytes back.

## Upload a file

Uploading takes three calls: ask for an upload ticket, `PUT` the bytes, then commit.

### Ask for a ticket

```bash
FILE=reference.png
CONTENT_TYPE=image/png
BYTES=$(wc -c < "$FILE" | tr -d ' ')

TICKET=$(curl -s -X POST "https://api.popnow.ai/api/v1/common/upload-url" \
  -H "Authorization: Bearer $POPNOW_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"contentType\": \"$CONTENT_TYPE\", \"bytes\": $BYTES}")
UPLOAD_URL=$(echo "$TICKET" | jq -r .data.uploadUrl)
FILE_ID=$(echo "$TICKET" | jq -r .data.fileId)
```

The response carries `fileId`, `uploadUrl`, the exact `headers` to send, `expiresAt` (about 20 minutes away) and `maxBytes`. There is no file name: storage paths are always chosen by the server.

### PUT the bytes

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X PUT "$UPLOAD_URL" \
  -H "Content-Type: $CONTENT_TYPE" \
  -H "Content-Length: $BYTES" \
  --data-binary @"$FILE"
```

Send every header from the ticket exactly as given — both are part of the signature — and **no** `Authorization` header. In a browser, leave out `Content-Length` and send a `File` or `Blob` of exactly the declared size; the browser sets it for you.

### Commit

```bash
curl -s -X POST "https://api.popnow.ai/api/v1/files/$FILE_ID/commit" \
  -H "Authorization: Bearer $POPNOW_API_KEY"
```

Commit checks the size, the type and the file signature, and returns the URI to use:

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "fileId": "fil_01k3m8x9q2z4v7n5p6r8s0t1w3",
    "status": "ready",
    "uri": "popnow://f/fil_01k3m8x9q2z4v7n5p6r8s0t1w3",
    "contentType": "image/png",
    "bytes": 402118,
    "width": 1024,
    "height": 1024,
    "expiresAt": "2026-10-17T09:12:00Z"
  },
  "request_id": "req_…"
}
```

Put `uri` in the model's field, for example `"image_url": "popnow://f/fil_…"`. A `popnow://` URI only works with keys on your own account. Committing twice is safe.

### Upload limits

| Type         | `contentType`                                        | Largest file | Longest duration |
| ------------ | ---------------------------------------------------- | ------------ | ---------------- |
| Image        | `image/jpeg`, `image/png`, `image/webp`, `image/gif` | 10 MiB       | —                |
| Video        | `video/mp4`, `video/webm`                            | 90 MiB       | 600 seconds      |
| Audio        | `audio/mpeg`, `audio/wav`                            | 90 MiB       | 600 seconds      |
| LoRA weights | `application/octet-stream` (a `.safetensors` file)   | 2 GiB        | —                |

A model can accept less than this; its schema says so per field. Uploaded files are temporary — the commit response's `expiresAt` tells you when the file is removed — so upload shortly before you create the task. To keep a file for repeated use, save it to your [asset library](assets.md).

If a commit answers `40003`, the bytes you sent do not match the ticket (different size, type or content). Ask for a new ticket and upload again.

## Download results

A finished task lists its files in `output.assets`, each with a ready-to-use `url`:

```bash
curl -L -o result.mp4 "$(curl -s "https://api.popnow.ai/api/v1/jobs/recordInfo?taskId=$TASK_ID" \
  -H "Authorization: Bearer $POPNOW_API_KEY" | jq -r '.data.output.assets[0].url')"
```

* The link is signed and works for about **20 minutes** (`expiresAt`). Do not store it; store the `taskId` and read the task again for a fresh link.
* Do not attach your API key when downloading. The link itself is the permission, and anyone holding it can download the file until it expires.
* To mint a link without reading the whole task, call `POST /api/v1/common/download-url` with `{ "taskId": "…" }` (and optionally the asset's `key`).

The files themselves are kept until the time in the task's `retention.outputsExpireAt`, or until you [purge](tasks.md#delete-a-tasks-content) the task. Copy anything you need beyond that to your own storage or your asset library.
