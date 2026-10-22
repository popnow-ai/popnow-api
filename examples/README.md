# PopNow API examples

Runnable examples for the [PopNow API](../README.md). Each one reads your key from `POPNOW_API_KEY`:

```bash
export POPNOW_API_KEY="sk-popnow-..."   # from https://popnow.ai/api/console/keys
```

| Folder | Requirements | Run |
| --- | --- | --- |
| [`curl/`](curl) | bash, curl, jq (and `uuidgen`, `openssl` where noted) | `./curl/text-to-image.sh "a paper boat on a calm lake"` |
| [`python/`](python) | Python 3.8+, standard library only | `python3 python/image_to_video.py` |
| [`node/`](node) | Node.js 18+, no dependencies | `node node/list-models.mjs video` |
| [`n8n/`](n8n) | n8n 1.x | Paste `popnow-workflow.json` onto the canvas, then pick a Header Auth credential with `Authorization: Bearer sk-popnow-...` |

Generations spend credits from your account (the text-to-image examples cost about 10 credits; the image-to-video examples use 480p and 5 seconds to keep the price low). Run `quote` first to see a price without spending anything. Failed or expired tasks are not charged.

Webhook receivers also need `POPNOW_WEBHOOK_SECRET` (generate it on the Webhooks page of the [API console](https://popnow.ai/api/console/webhooks)) and a public HTTPS URL that forwards to them.
