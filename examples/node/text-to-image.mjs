// Generate one image and save it. ?wait=60 usually returns the finished image in the same request.
// Usage: node text-to-image.mjs "A paper boat on a calm lake" [out.png]   (Node.js 18+, no dependencies)
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

const prompt = process.argv[2] ?? 'A small red fox curled up in a teacup, soft morning light';
const out = process.argv[3] ?? 'image.png';

let task = await api('/jobs/createTask?wait=60', {
  method: 'POST',
  headers: { 'Idempotency-Key': crypto.randomUUID() },
  body: { model: 'alibaba/z-image-turbo/text-to-image', input: { prompt, aspect_ratio: '1:1' } },
});
if (!isDone(task)) task = await waitFor(task.taskId);
if (task.state !== 'succeeded') throw new Error(`${task.state}: ${task.errorCode} ${task.errorMessage}`);

// Signed link, valid for about 20 minutes. Do not send the API key to it.
const file = await fetch(task.output.assets[0].url);
await writeFile(out, Buffer.from(await file.arrayBuffer()));
console.log(`saved ${out} (${task.credits} credits, task ${task.taskId})`);
