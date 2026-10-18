# Authentication

> The key format, where to keep a key, per-key restrictions, rotation and what to do if a key leaks.

Online version: <https://popnow.ai/docs/authentication>

Every request to the API carries one API key in the `Authorization` header:

```http
Authorization: Bearer sk-popnow-3f9c0a…
```

There is no other way to authenticate: keys in the URL query string are never accepted, and your popnow\.ai login does not work on the API.

One exception: the [OpenAI-compatible routes](openai-videos.md) under `/v1` also read the key from an `x-api-key` header, so OpenAI-style clients work unchanged. The native `/api/v1` routes only read `Authorization`.

## What a key looks like

A key is `sk-popnow-` followed by 48 lowercase hexadecimal characters. The API console only ever shows the first few characters after you create it, so a key you lose cannot be recovered — create a new one instead.

## Create a key

1. Sign in at [popnow.ai](https://popnow.ai) and open the [API console](https://popnow.ai/api/console/keys).
2. Choose **Create key** and give it a name that says where it will live, such as `production-backend`.
3. Copy the key immediately. It is shown once.

You can hold several keys at once — one per environment or per service is a good habit, because you can then revoke one without touching the others. All keys spend from the same credit balance.

## Where to keep it

* In an environment variable or your platform's secret store (`POPNOW_API_KEY`), not in source code.
* Never in a browser, a mobile app or any other code that runs on someone else's device. Anyone who can read the key can spend your credits. Put your own server in between and let it call PopNow.
* Not in logs. If you log request headers, drop `Authorization` first.

## Restrict what a key can do

Each key can carry its own limits, set in the API console:

| Restriction    | What it does                                                      | Error when it blocks a request |
| -------------- | ----------------------------------------------------------------- | ------------------------------ |
| Allowed models | The key can call only the models you list                         | `40301`                        |
| IP allowlist   | Requests must come from these addresses or ranges                 | `40302`                        |
| Spend caps     | Daily, monthly and lifetime limits for this key, shown in credits | `40202`                        |

By default a key has no restrictions and no caps. Give production keys the narrowest set that still works.

## Tasks belong to the key that created them

`recordInfo`, `retry`, `purge`, the task list and usage only see tasks created **with the same key**. A task created with another key on your account answers `404`, exactly like a task that does not exist. Generations you start on the website are not visible to any key either. For an account-wide view, use the API console.

## Rotation

To replace a key without downtime:

1. Create the new key.
2. Deploy it everywhere the old one was used.
3. Watch the old key's last-used time in the console stop moving.
4. Revoke the old key.

## If a key leaks

1. **Revoke it now** in the API console. Revocation takes effect on the next request.
2. **Create a replacement** and deploy it.
3. **Check what it was used for**: the console's logs and usage show every task the key created.
4. **Tighten the replacement** with an IP allowlist and a spend cap.

Contact [support](https://popnow.ai/contact) if you see spending you did not make.

## What a failure looks like

All three authentication problems return HTTP `401` with `code: 401`; `msg` tells them apart:

| `msg` says                         | What happened                                      | What to do                                                                                      |
| ---------------------------------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Missing credentials                | No `Authorization` header arrived                  | Check that the header is set and that the environment variable is loaded in the running process |
| API key format is not recognized   | Something arrived, but it is not a PopNow key      | Make sure it starts with `sk-popnow-`; you may have pasted a different value                    |
| Credentials are invalid or expired | The key does not exist, was revoked or has expired | Create a new key; retrying will never succeed                                                   |

A valid key can still be refused with `403` — for example when the account's email address is not verified yet (`40310`). See [Errors](errors.md#permissions).
