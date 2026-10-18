// Price a task before running it, then (with --create) create it at exactly that price.
// A quote creates nothing and holds nothing; it is valid for five minutes. Passing quoteId +
// expectedCredits to createTask guarantees the hold matches (an expired quote fails with 40901).
// Usage: node quote.mjs [--create]   (Node.js 18+, no dependencies)
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

const request = {
  model: 'alibaba/wan-3.0/image-to-video',
  input: {
    image_url: 'https://media.popnow.ai/movie/lighthouse.webp',
    prompt: 'Waves roll in slowly, the camera drifts toward the lighthouse',
    resolution: '480p',
    duration_seconds: 5,
  },
};

const quote = await api('/jobs/quote', { method: 'POST', body: request });
console.log(`${quote.model}: up to ${quote.maxCredits} credits ($${quote.maxCharge}), usually ${quote.expectedCredits}; expires ${quote.expiresAt}`);

if (process.argv.includes('--create')) {
  const task = await api('/jobs/createTask', {
    method: 'POST',
    headers: { 'Idempotency-Key': crypto.randomUUID() },
    body: { ...request, quoteId: quote.quoteId, expectedCredits: quote.expectedCredits },
  });
  console.log('created', task.taskId, 'holding', task.estimatedCredits, 'credits');
}
