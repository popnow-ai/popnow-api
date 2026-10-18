"""Read a task until it reaches a final state and print the result.

Usage: python3 poll_job.py job_...
Standard library only (Python 3.8+).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

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


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python3 poll_job.py <taskId>")
    task_id = sys.argv[1]
    delay = 3.0
    while True:
        task = api("GET", "/jobs/recordInfo?" + urllib.parse.urlencode({"taskId": task_id}))
        assets = (task.get("output") or {}).get("assets") or []
        copying = any(a.get("pending") and not a.get("unavailable") for a in assets)
        # Treat any state you do not recognise as "not final yet".
        if task["state"] in FINAL and not copying:
            break
        print(f"{task['state']}, next check in {delay:.0f}s", file=sys.stderr)
        time.sleep(delay)
        delay = min(delay * 1.5, 15.0)

    print(json.dumps({
        "taskId": task["taskId"],
        "state": task["state"],
        "credits": task.get("credits"),
        "settled": task.get("settled"),
        "errorCode": task.get("errorCode"),
        "errorMessage": task.get("errorMessage"),
        "assets": [{"url": a.get("url"), "mime": a.get("mime"), "expiresAt": a.get("expiresAt")} for a in assets],
    }, indent=2))


if __name__ == "__main__":
    main()
