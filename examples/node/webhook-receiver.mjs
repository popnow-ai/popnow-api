// Minimal task-callback receiver that verifies the PopNow signature (Node.js 18+, no dependencies).
//   signature = base64( HMAC-SHA256( secret, "<taskId>.<timestamp>.<sha256_hex(raw_body)>" ) )
// Run:  POPNOW_WEBHOOK_SECRET=... node webhook-receiver.mjs   (listens on :3000)
// Then pass "callBackUrl": "https://<your public host>/hooks/popnow" to createTask.
// The URL must be public HTTPS, so expose this port through a tunnel or a reverse proxy.
import crypto from 'node:crypto';
import http from 'node:http';

const SECRET = process.env.POPNOW_WEBHOOK_SECRET;
if (!SECRET) throw new Error('Set POPNOW_WEBHOOK_SECRET');
const PORT = Number(process.env.PORT ?? 3000);
const seen = new Set(); // Use a table with a unique index on request_id in production.

/** Returns the parsed event when the signature and timestamp are valid, otherwise null. */
function verify(raw, timestamp, signature) {
  const ts = Number(timestamp);
  // Refuse anything older than five minutes, however valid its signature.
  if (!Number.isInteger(ts) || Math.abs(Date.now() / 1000 - ts) > 300) return null;
  let event;
  try { event = JSON.parse(raw.toString('utf8')); } catch { return null; }
  // Hash the exact bytes received, never a re-serialised object.
  const digest = crypto.createHash('sha256').update(raw).digest('hex');
  const expected = crypto.createHmac('sha256', SECRET).update(`${event.data?.taskId}.${ts}.${digest}`).digest('base64');
  const sig = String(signature ?? '');
  const ok = expected.length === sig.length && crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(sig));
  return ok ? event : null;
}

http.createServer((req, res) => {
  if (req.method !== 'POST' || req.url !== '/hooks/popnow') return res.writeHead(404).end();
  const chunks = [];
  req.on('data', (c) => chunks.push(c));
  req.on('end', () => {
    const event = verify(Buffer.concat(chunks), req.headers['x-webhook-timestamp'], req.headers['x-webhook-signature']);
    if (!event) return res.writeHead(401).end();

    // Acknowledge within 15 seconds; do slow work (downloads, notifications) elsewhere.
    res.writeHead(200).end();

    // request_id is the delivery ID and stays the same across retries: use it to drop duplicates.
    if (seen.has(event.request_id)) return;
    seen.add(event.request_id);
    const task = event.data;
    // code is 200 even for a failed task; the task outcome is in data.state.
    console.log(task.taskId, task.state, task.errorCode ?? task.output?.assets?.[0]?.url);
  });
}).listen(PORT, () => console.log(`listening on http://localhost:${PORT}/hooks/popnow`));
