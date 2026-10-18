# Contributing

Thanks for helping improve the PopNow API examples and docs.

- **Bugs in an example or a doc:** open an issue with the file, what you ran, and what happened. Include the `request_id` from the response if there was one. Never paste an API key.
- **Pull requests** are welcome for fixes and new examples. Keep examples dependency-free (curl + jq, the Python standard library, plain Node.js 18+), read the key from `POPNOW_API_KEY`, and send an `Idempotency-Key` on every `createTask`.
- **The spec and the docs** mirror the live API. `openapi.yaml` and `docs/` are refreshed from the published versions at <https://popnow.ai/docs/openapi.yaml> and <https://popnow.ai/docs>; if you find a mismatch with the live API, an issue is the fastest way to get it fixed.
- After editing anything in `docs/`, run `python3 scripts/build_llms.py` so `llms.txt` and `llms-full.txt` stay in sync (`--check` verifies it).
- Questions about your account, billing or a specific task go to [PopNow support](https://popnow.ai/contact), not to GitHub issues.

By contributing you agree that your contribution is licensed under the MIT License of this repository.
