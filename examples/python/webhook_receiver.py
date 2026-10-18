"""Minimal task-callback receiver that verifies the PopNow signature.

    signature = base64( HMAC-SHA256( secret, "<taskId>.<timestamp>.<sha256_hex(raw_body)>" ) )

Run:   POPNOW_WEBHOOK_SECRET=... python3 webhook_receiver.py   (listens on :8000)
Then pass "callBackUrl": "https://<your public host>/hooks/popnow" to createTask.
The URL must be public HTTPS, so expose this port through a tunnel or a reverse proxy.
Standard library only (Python 3.8+).
"""
import base64
import hashlib
import hmac
import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

SECRET = os.environ["POPNOW_WEBHOOK_SECRET"].encode()
PORT = int(os.environ.get("PORT", "8000"))
SEEN = set()  # Use a database table with a unique index on request_id in production.


def verify(raw, timestamp, signature):
    """Return the parsed event if the signature and timestamp are valid, else None."""
    if not timestamp.isdigit() or abs(time.time() - int(timestamp)) > 300:
        return None  # Refuse anything older than five minutes, however valid its signature.
    try:
        event = json.loads(raw)
        task_id = event["data"]["taskId"]
    except (ValueError, KeyError, TypeError):
        return None
    # Hash the exact bytes received, never a re-serialised object.
    message = f"{task_id}.{timestamp}.{hashlib.sha256(raw).hexdigest()}".encode()
    expected = base64.b64encode(hmac.new(SECRET, message, hashlib.sha256).digest()).decode()
    return event if hmac.compare_digest(expected, signature) else None


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/hooks/popnow":
            self.send_response(404)
            self.end_headers()
            return
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        event = verify(raw, self.headers.get("X-Webhook-Timestamp", ""), self.headers.get("X-Webhook-Signature", ""))
        if event is None:
            self.send_response(401)
            self.end_headers()
            return

        # Acknowledge within 15 seconds; do slow work (downloads, notifications) elsewhere.
        self.send_response(200)
        self.end_headers()

        delivery_id = event["request_id"]  # Same across retries: use it to drop duplicates.
        if delivery_id in SEEN:
            return
        SEEN.add(delivery_id)
        task = event["data"]
        # code is 200 even for a failed task; the task outcome is in data.state.
        url = ((task.get("output") or {}).get("assets") or [{}])[0].get("url")
        print(task["taskId"], task["state"], task.get("errorCode") or url)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"listening on http://0.0.0.0:{PORT}/hooks/popnow")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
