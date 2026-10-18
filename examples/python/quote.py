"""Price a task before running it, then create it at exactly that price.

The quote validates the input like createTask but creates nothing and holds nothing.
It is valid for five minutes; passing quoteId + expectedCredits to createTask guarantees
the held amount matches what you showed (an expired or changed quote fails with 40901).

Usage: python3 quote.py [--create]
Standard library only (Python 3.8+).
"""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

API = os.environ.get("POPNOW_API_BASE", "https://api.popnow.ai") + "/api/v1"
# Send a descriptive User-Agent: some networks block the default "Python-urllib" one.
UA = "popnow-api-examples/1.0 (python)"

REQUEST = {
    "model": "alibaba/wan-3.0/image-to-video",
    "input": {
        "image_url": "https://media.popnow.ai/movie/lighthouse.webp",
        "prompt": "Waves roll in slowly, the camera drifts toward the lighthouse",
        "resolution": "480p",
        "duration_seconds": 5,
    },
}


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
    quote = api("POST", "/jobs/quote", REQUEST)
    print(f"{quote['model']}: up to {quote['maxCredits']} credits (${quote['maxCharge']}), "
          f"usually {quote['expectedCredits']}; quote expires {quote['expiresAt']}")

    if "--create" in sys.argv:
        task = api(
            "POST",
            "/jobs/createTask",
            {**REQUEST, "quoteId": quote["quoteId"], "expectedCredits": quote["expectedCredits"]},
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )
        print("created", task["taskId"], "holding", task["estimatedCredits"], "credits")


if __name__ == "__main__":
    main()
