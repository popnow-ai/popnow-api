// Turn an image into a 5-second video, poll until ready, and download it.
// Usage: node image-to-video.mjs [image_url_or_popnow_uri] [prompt]   (Node.js 18+, no dependencies)
// For a local file, run upload-file.mjs first and pass the popnow://f/... URI it prints.
import { writeFile } from 'node:fs/promises';

const API = `${process.env.POPNOW_API_BASE ?? 'https://api.popnow.ai'}/api/v1`;

/** Call the PopNow API and return `data`; throws on any non-200 business code. */
async function api(path, { method = 'GET', body, headers = {} } = {}) {
  const res = await fetch(API + path, {
    method,
    headers: {
      Authorization: `Bearer ${process.env.POPNOW_API_KEY}`,
      'Content-Type': 'application/json',
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  // Errors use the same {code, msg, data, request_id} envelope as successes.
  const envelope = await res.json();
  if (envelope.code !== 200) throw new Error(`${envelope.code} ${envelope.msg} (request_id ${envelope.request_id})`);
  return envelope.data;
}

const FINAL = new Set(['succeeded', 'failed', 'expired', 'canceled']);

/** Final state, and no output file is still being copied into storage. */
function isDone(task) {
  const assets = task.output?.assets ?? [];
  return FINAL.has(task.state) && !assets.some((a) => a.pending && !a.unavailable);
}

/** Poll recordInfo with backoff until the task is done. */
async function waitFor(taskId, { delayMs = 3000, maxDelayMs = 15000 } = {}) {
  for (;;) {
    await new Promise((r) => setTimeout(r, delayMs));
    const task = await api(`/jobs/recordInfo?taskId=${encodeURIComponent(taskId)}`);
    if (isDone(task)) return task;
    console.error(`  ${task.state}...`);
    delayMs = Math.min(delayMs * 1.5, maxDelayMs);
  }
}

const image = process.argv[2] ?? 'https://media.popnow.ai/movie/lighthouse.webp';
const prompt = process.argv[3] ?? 'Waves roll in slowly, the camera drifts toward the lighthouse';

// One idempotency key per piece of work; reuse it if you retry this exact request.
const idempotencyKey = crypto.randomUUID();
const created = await api('/jobs/createTask', {
  method: 'POST',
  headers: { 'Idempotency-Key': idempotencyKey },
  body: {
    model: 'alibaba/wan-3.0/image-to-video',
    input: { image_url: image, prompt, resolution: '480p', duration_seconds: 5 },
  },
});
console.error(`created ${created.taskId}, holding ${created.estimatedCredits} credits`);

const task = await waitFor(created.taskId, { delayMs: 5000 });
if (task.state !== 'succeeded') throw new Error(`${task.state}: ${task.errorCode} ${task.errorMessage} (nothing was charged)`);

const file = await fetch(task.output.assets[0].url);
await writeFile('video.mp4', Buffer.from(await file.arrayBuffer()));
console.log(`saved video.mp4 (${task.credits} credits)`);
