"""Upload a local image, video or audio file and print the popnow:// URI to use in task input.

Three calls: ask for an upload ticket, PUT the bytes, commit.
Usage: python3 upload_file.py photo.png
Standard library only (Python 3.8+).
"""
import json
import mimetypes
import os
import sys
import urllib.error
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
        envelope = json.load(err)
    if envelope.get("code") != 200:
        raise RuntimeError(f"{envelope.get('code')} {envelope.get('msg')} (request_id {envelope.get('request_id')})")
    return envelope["data"]


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python3 upload_file.py <file> [content-type]")
    path = sys.argv[1]
    content_type = sys.argv[2] if len(sys.argv) > 2 else mimetypes.guess_type(path)[0]
    if not content_type:
        sys.exit("could not guess the content type; pass it as the second argument (e.g. image/png)")
    with open(path, "rb") as f:
        data = f.read()

    # 1. Ticket: the server picks the storage path; you declare the exact size and type.
    ticket = api("POST", "/common/upload-url", {"contentType": content_type, "bytes": len(data)})

    # 2. PUT the bytes with every header from the ticket and no Authorization header.
    put = urllib.request.Request(ticket["uploadUrl"], data=data, method=ticket["method"], headers={**ticket["headers"], "User-Agent": UA})
    with urllib.request.urlopen(put, timeout=600) as res:
        if not 200 <= res.status < 300:
            sys.exit(f"upload failed with HTTP {res.status}")

    # 3. Commit: verifies size, type and file signature, then returns the URI.
    committed = api("POST", f"/files/{ticket['fileId']}/commit")
    print(committed["uri"])
    print(f"expires {committed['expiresAt']}; use it soon, or save it to your asset library", file=sys.stderr)


if __name__ == "__main__":
    main()
