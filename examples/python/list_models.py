"""List every model your key can call, with its price in credits.

Usage: python3 list_models.py [image|video|audio]
Standard library only (Python 3.8+).
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = os.environ.get("POPNOW_API_BASE", "https://api.popnow.ai") + "/api/v1"
# Send a descriptive User-Agent: some networks block the default "Python-urllib" one.
UA = "popnow-api-examples/1.0 (python)"


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
        # Error responses carry the same {code, msg, data, request_id} envelope.
        envelope = json.load(err)
    if envelope.get("code") != 200:
        raise RuntimeError(f"{envelope.get('code')} {envelope.get('msg')} (request_id {envelope.get('request_id')})")
    return envelope["data"]


def main():
    query = {"modality": sys.argv[1]} if len(sys.argv) > 1 else {}
    data = api("GET", "/models" + ("?" + urllib.parse.urlencode(query) if query else ""))
    for item in data["items"]:
        print(f"{item['model']:<60} {item['modality']:<6} {item['credits']}")
    print(f"{data['total']} models", file=sys.stderr)


if __name__ == "__main__":
    main()
