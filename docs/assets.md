# Assets and LoRA files

> Keep files in your asset library and reuse them by URI, read your characters, and bring your own LoRA weights.

Online version: <https://popnow.ai/docs/assets>

Uploads and task results are temporary. When you want to reuse a file across many tasks — a product photo, a character's face, a voice sample — save it to your **asset library**. When a model accepts custom style weights, bring your own **LoRA** file.

## The asset library

A saved asset gets a stable URI, `popnow://a/ast_…`, that you can put in any matching media field of any model, for as long as you keep the asset:

```json
{ "model": "google/nano-banana-2.1/edit",
  "input": { "prompt": "Put this mug on a wooden café table, morning light",
             "image_urls": ["popnow://a/ast_01k3m8x9q2z4v7n5p6r8s0t1w3"] } }
```

The URI is a reference, not a download link: it only works in generation requests made with keys on your account. Assets stay until you delete them.

### Save a file

`POST /api/v1/assets` copies a file into the library. Choose one source; the `Idempotency-Key` header is required, and saving the same source again returns the existing asset.

| `source`      | Also send                                  | Saves                                                                               |
| ------------- | ------------------------------------------ | ----------------------------------------------------------------------------------- |
| `task_output` | `taskId` and the output's `key` or `index` | A file one of your succeeded tasks produced                                         |
| `upload`      | `fileId`                                   | A committed [upload](media.md#upload-a-file)                                            |
| `url`         | `url`                                      | A public `http`/`https` file (JPEG, PNG, WebP, GIF, MP4, WebM, MP3, WAV, FLAC, Ogg) |

```bash
curl -X POST "https://api.popnow.ai/api/v1/assets" \
  -H "Authorization: Bearer $POPNOW_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: save-$TASK_ID-0" \
  -d "{\"source\": \"task_output\", \"taskId\": \"$TASK_ID\", \"index\": 0, \"name\": \"Hero shot\"}"
```

The response is the asset: `id`, `uri`, `name`, `kind` (`image`, `video` or `audio`), size and dimensions, the `model` that generated it, and a private `previewUrl` valid for about 20 minutes. Store the `uri`, never the preview link.

### List, rename and delete

| Call                          | Does                                                                                                                                                                             |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /api/v1/assets`          | One page of assets. Filter with `kind`, `source`, `favorite`, `q` (name search), `collectionId`, `entityId`; sort with `sort=recent\|oldest\|name\|size`; continue with `cursor` |
| `GET /api/v1/assets/{id}`     | One asset with a fresh preview link                                                                                                                                              |
| `PATCH /api/v1/assets/{id}`   | Change `name` and/or `favorite`                                                                                                                                                  |
| `DELETE /api/v1/assets/{id}`  | Delete it; its URI stops working in new requests                                                                                                                                 |
| `GET /api/v1/assets/entities` | Your characters: named sets of images arranged in the website, each image with its own URI                                                                                       |
| `GET /api/v1/assets/usage`    | Your storage plan, what you use, its limits and what the next plan unlocks                                                                                                       |

### Storage plans

Storage opens with your first credit purchase and grows with what you have bought over time; it never shrinks, and saved assets always stay usable. `GET /api/v1/assets/usage` shows the numbers for your account.

### Errors

Asset library errors add a machine-readable `data.reason` to the usual envelope:

| `data.reason`          | HTTP | Meaning                                                                      |
| ---------------------- | ---- | ---------------------------------------------------------------------------- |
| `asset_library_locked` | 400  | The library opens after your first credit purchase                           |
| `asset_library_full`   | 400  | Your plan's space or item count is used up — delete assets or move up a plan |
| `asset_file_too_large` | 400  | The file is above your plan's per-file limit                                 |
| `asset_daily_limit`    | 429  | Today's number of new assets is reached; wait for `Retry-After` (00:00 UTC)  |
| `asset_storage_full`   | 503  | Storage is temporarily full on our side; try again later                     |

Treat a reason you do not recognise like an absent one. Reading the library is limited to 60 requests per minute and saving to 30 per minute.

## Bring your own LoRA

Models whose ID ends in `-lora` accept a `loras` array — up to three weights files, each with a `path` and a `scale` (0 to 4):

```json
{ "model": "alibaba/qwen-image-2.1-lora/text-to-image",
  "input": { "prompt": "A cozy reading nook in watercolor style",
             "loras": [{ "path": "popnow://f/fil_01k3m8x9q2z4v7n5p6r8s0t1w3", "scale": 1 }] } }
```

`path` can be a public direct link to a `.safetensors` file, or a file you uploaded or imported:

* **Upload** it like any other file with `contentType: application/octet-stream` (a `.safetensors` file up to 2 GiB; the ticket is valid for two hours). Commit checks that it is a complete safetensors file.
* **Import it from a link** when the file needs a sign-in, for example a private Hugging Face repository:

```bash
curl -X POST "https://api.popnow.ai/api/v1/files/import" \
  -H "Authorization: Bearer $POPNOW_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "your-name/your-lora-repo", "token": "hf_..."}'
```

`url` accepts a Hugging Face repo ID (`owner/repo`, when it holds exactly one `.safetensors` file), a Hugging Face repo or file page, or any direct HTTPS link. `token` is optional — a Hugging Face access token or a Civitai API key — and is used only for this one download, never stored. The response matches a [commit](media.md#commit): put its `uri` in `loras[].path`.

A LoRA must match the base model it was trained for; weights for a different base usually fail or have no effect. You are responsible for having the right to use the weights you bring.
