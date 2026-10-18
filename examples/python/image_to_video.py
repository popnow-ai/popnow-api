"""Turn an image into a 5-second video, poll until it is ready, and download it.

Usage: python3 image_to_video.py [image_url_or_popnow_uri] [prompt]
Tip: for a local file, run upload_file.py first and pass the popnow://f/... URI it prints.
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


def wait(task_id, deadline_s=900):
    """Poll recordInfo with backoff until the task is final and its files are copied."""
    delay, started = 5.0, time.time()
    while True:
        time.sleep(delay)
        task = api("GET", "/jobs/recordInfo?taskId=" + task_id)
        assets = (task.get("output") or {}).get("assets") or []
        copying = any(a.get("pending") and not a.get("unavailable") for a in assets)
        if task["state"] in FINAL and not copying:
            return task
        if time.time() - started > deadline_s:
            raise TimeoutError(f"{task_id} still {task['state']}; check it later with poll_job.py")
        print(f"  {task['state']}...", file=sys.stderr)
        delay = min(delay * 1.5, 15.0)


def main():
    image = sys.argv[1] if len(sys.argv) > 1 else "https://media.popnow.ai/movie/lighthouse.webp"
    prompt = sys.argv[2] if len(sys.argv) > 2 else "Waves roll in slowly, the camera drifts toward the lighthouse"

    # One idempotency key per piece of work: reuse it if you retry this exact request.
    key = str(uuid.uuid4())
    created = api(
        "POST",
        "/jobs/createTask",
        {
            "model": "alibaba/wan-3.0/image-to-video",
            "input": {"image_url": image, "prompt": prompt, "resolution": "480p", "duration_seconds": 5},
        },
        headers={"Idempotency-Key": key},
    )
    print(f"created {created['taskId']}, holding {created['estimatedCredits']} credits", file=sys.stderr)

    task = wait(created["taskId"])
    if task["state"] != "succeeded":
        sys.exit(f"{task['state']}: {task.get('errorCode')} {task.get('errorMessage')} (nothing was charged)")

    url = task["output"]["assets"][0]["url"]
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=600) as res, open("video.mp4", "wb") as f:
        f.write(res.read())
    print(f"saved video.mp4 ({task['credits']} credits)")


if __name__ == "__main__":
    main()
