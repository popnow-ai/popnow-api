# Production checklist

> What to check before real users depend on your integration — keys, retries, webhooks, storage, costs and monitoring.

Online version: <https://popnow.ai/docs/production-integration>

A demo needs one request. A product needs to survive timeouts, duplicate webhooks, expired links and a key that leaks. Go through this list before launch.

## Keys

* [ ] The key lives in your server's secret store, never in a browser or app bundle.
* [ ] Each environment and each service has its own key, so one can be revoked alone.
* [ ] Production keys are limited to the models you use and have a daily spend cap.
* [ ] You know how to rotate a key without downtime ([Authentication](authentication.md#rotation)).

## Creating tasks

* [ ] Every `createTask` sends an `Idempotency-Key` derived from your own job ID, generated once, reused on every retry.
* [ ] Only `429`, `500`, `503` and `50301` are retried, with backoff and `Retry-After` ([Errors](errors.md#writing-the-retry)).
* [ ] `400`, `40004` and other "fix the request" errors are shown or logged, not retried.
* [ ] If you show prices, you quote first and pass `quoteId` and `expectedCredits`, and handle `40901`.
* [ ] A low balance (`40201`) reaches a person — an alert, an email, a banner — before users notice.

## Getting results

* [ ] Tasks carry a `callBackUrl`; your endpoint verifies the signature and rejects stale timestamps.
* [ ] The webhook handler answers `2xx` quickly and does the work in the background.
* [ ] Duplicate deliveries are ignored by `request_id`.
* [ ] A periodic sweep reads tasks whose webhook never arrived.
* [ ] Your code treats any state other than `succeeded`, `failed`, `expired` and `canceled` as "still running".

## Files

* [ ] Finished files are copied into your own storage (or your asset library) instead of linking to the signed URL, which expires in about 20 minutes.
* [ ] You store `taskId`s, not signed links.
* [ ] Your download code does not send the API key to the signed URL.
* [ ] Reference files are public HTTPS links to the file itself, uploads, or assets — not share pages.

## Costs

* [ ] You know each model's price unit (per image, per second, per request) and the settings that raise it.
* [ ] Previews and tests use the cheapest resolution and shortest duration.
* [ ] A spend cap stops runaway loops before they empty the balance.
* [ ] You check `credits` and `settled` rather than assuming the estimate was charged.

## Monitoring

* [ ] You log `request_id`, `taskId`, `code` and `errorCode` for every failure.
* [ ] You watch the share of `failed` tasks per model; a sudden rise usually means a prompt, input or model change.
* [ ] You track time from `createTask` to the webhook per model, and alert on outliers.
* [ ] Someone on your team knows where the API console's logs and usage pages are.

## Content

PopNow is a general-audience service. Models apply their own content rules, and requests they decline fail with `content_rejected`. If your users write prompts, tell them in your own interface why a request was declined instead of showing a raw error, and let them change it.
