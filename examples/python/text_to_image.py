"""Generate one image and save it to disk.

`?wait=60` keeps the connection open until the task is done, so a fast image model
usually answers in this same request. If not, we fall back to polling.

Usage: python3 text_to_image.py "A paper boat on a calm lake" [out.png]
Standard library only (Python 3.8+).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

API = os.environ.get("POPNOW_API_BASE", "https://api.popnow.ai") + "/api/v1"
# Send a descriptive User-Agent: some networks block the default "Python-urllib" one.
UA = "popnow-api-examples/1.0 (python)"
FINAL = ("succeeded", "failed", "expired", "canceled")


def api(method, path, body=None, headers=None):
    """Call the PopNow API and return `data`, raising on any non-200 business code."""
    req = urllib.request.Request(
        API + path,
        method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={
            "Authorization": "Bearer " + os.environ["POPNOW_API_KEY"],
            "Content-Type": "application/json",
            "User-Agent": UA,
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as res:
            envelope = json.load(res)
    except urllib.error.HTTPError as err:
        envelope = json.load(err)
    if envelope.get("code") != 200:
        raise RuntimeError(f"{envelope.get('code')} {envelope.get('msg')} (request_id {envelope.get('request_id')})")
    return envelope["data"]


def is_done(task):
    """Final state, and no output file is still being copied into storage."""
    assets = (task.get("output") or {}).get("assets") or []
    copying = any(a.get("pending") and not a.get("unavailable") for a in assets)
    return task["state"] in FINAL and not copying


def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else "A small red fox curled up in a teacup, soft morning light"
    out = sys.argv[2] if len(sys.argv) > 2 else "image.png"

    task = api(
        "POST",
        "/jobs/createTask?wait=60",
        {"model": "alibaba/z-image-turbo/text-to-image", "input": {"prompt": prompt, "aspect_ratio": "1:1"}},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    while not is_done(task):
        time.sleep(3)
        task = api("GET", "/jobs/recordInfo?taskId=" + task["taskId"])

    if task["state"] != "succeeded":
        sys.exit(f"{task['state']}: {task.get('errorCode')} {task.get('errorMessage')}")

    # Signed link, valid for about 20 minutes. Do not send the API key to it.
    url = task["output"]["assets"][0]["url"]
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=300) as res, open(out, "wb") as f:
        f.write(res.read())
    print(f"saved {out} ({task['credits']} credits, task {task['taskId']})")


if __name__ == "__main__":
    main()
