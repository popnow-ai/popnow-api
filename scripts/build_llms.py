"""Build llms.txt and llms-full.txt at the repository root from docs/*.md.

Usage: python3 scripts/build_llms.py          (rewrite both files)
       python3 scripts/build_llms.py --check  (exit 1 if either file is out of date)
Standard library only.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
REPO = "https://github.com/popnow-ai/popnow-api"

# Reading order: getting started, core concepts, reliability, then integrations.
ORDER = [
    "quickstart",
    "authentication",
    "tasks",
    "media",
    "webhooks",
    "idempotency",
    "errors",
    "limits",
    "assets",
    "production-integration",
    "recipes",
    "openai-videos",
    "comfyui",
]

HEADER = """\
# PopNow API

> PopNow API is a REST API for AI video, image and music generation: one API key and one credit
> wallet give access to models such as Kling, Seedance, Wan, Vidu, MiniMax, Nano Banana, GPT Image,
> Flux and Suno. This repository holds the OpenAPI 3.1 spec, runnable examples and Markdown docs.

- Base URL: https://api.popnow.ai (native endpoints under /api/v1, OpenAI-compatible endpoints under /v1)
- Authentication: `Authorization: Bearer sk-popnow-...` (create keys at https://popnow.ai/api/console/keys)
- Envelope: every native JSON response is `{{code, msg, data, request_id}}`; `code: 200` means success
- Async flow: POST /api/v1/jobs/quote (optional price check) -> POST /api/v1/jobs/createTask -> GET /api/v1/jobs/recordInfo?taskId=... until state is succeeded, failed or expired (or receive a webhook via callBackUrl)
- Models and prices: GET /api/v1/models (1 credit = US$0.01; failed tasks are not charged)
- OpenAPI spec: {repo}/blob/main/openapi.yaml (also https://popnow.ai/docs/openapi.yaml)
- Website: https://popnow.ai - Docs: https://popnow.ai/docs - Pricing: https://popnow.ai/pricing - MCP server: https://popnow.ai/mcp
""".format(repo=REPO)


def read_doc(slug):
    text = (DOCS / f"{slug}.md").read_text(encoding="utf-8")
    title = text.splitlines()[0].lstrip("# ").strip()
    match = re.search(r"^> (.+)$", text, re.M)
    summary = match.group(1).strip() if match else ""
    return title, summary, text


def build():
    docs = [(slug, *read_doc(slug)) for slug in ORDER]

    index = [HEADER, "## Docs", ""]
    for slug, title, summary, _ in docs:
        index.append(f"- [{title}]({REPO}/blob/main/docs/{slug}.md): {summary}")
    index += [
        "",
        "## Examples",
        "",
        f"- [curl]({REPO}/tree/main/examples/curl): bash scripts for list models, quote, text-to-image, image-to-video, poll a task, upload a file and verify a webhook signature",
        f"- [Python]({REPO}/tree/main/examples/python): the same tasks with the standard library only, plus a webhook receiver",
        f"- [Node.js]({REPO}/tree/main/examples/node): the same tasks for Node.js 18+ with no dependencies, plus a webhook receiver",
        f"- [n8n]({REPO}/blob/main/examples/n8n/popnow-workflow.json): importable workflow that creates a task, polls it and returns the file URL",
        "",
        "## Optional",
        "",
        f"- [Full docs in one file]({REPO}/blob/main/llms-full.txt)",
        "- [Live documentation index](https://popnow.ai/docs/llms.txt)",
        "",
    ]

    full = [HEADER, "---", ""]
    for _, _, _, text in docs:
        full += [text.strip(), "", "---", ""]

    return "\n".join(index), "\n".join(full).rstrip("-\n") + "\n"


def main():
    outputs = dict(zip(("llms.txt", "llms-full.txt"), build()))
    if "--check" in sys.argv:
        stale = [name for name, text in outputs.items() if (ROOT / name).read_text(encoding="utf-8") != text]
        if stale:
            sys.exit("out of date: " + ", ".join(stale) + " (run python3 scripts/build_llms.py)")
        print("llms files are up to date")
        return
    for name, text in outputs.items():
        (ROOT / name).write_text(text, encoding="utf-8")
        print(f"wrote {name} ({len(text)} bytes)")


if __name__ == "__main__":
    main()
