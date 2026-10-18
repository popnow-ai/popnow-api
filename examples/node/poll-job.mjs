// Read a task until it is final and print the result.
// Usage: node poll-job.mjs job_...   (Node.js 18+, no dependencies)
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

const taskId = process.argv[2];
if (!taskId) throw new Error('usage: node poll-job.mjs <taskId>');

let task = await api(`/jobs/recordInfo?taskId=${encodeURIComponent(taskId)}`);
if (!isDone(task)) task = await waitFor(taskId);
console.log(JSON.stringify({
  taskId: task.taskId,
  state: task.state,
  credits: task.credits,
  settled: task.settled,
  errorCode: task.errorCode,
  errorMessage: task.errorMessage,
  assets: (task.output?.assets ?? []).map(({ url, mime, expiresAt }) => ({ url, mime, expiresAt })),
}, null, 2));
