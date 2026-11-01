// List every model your key can call, with its USD price.
// Usage: node list-models.mjs [image|video|audio]   (Node.js 18+, no dependencies)
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

const modality = process.argv[2];
const data = await api('/models' + (modality ? `?modality=${encodeURIComponent(modality)}` : ''));
for (const m of data.items) {
  // `usd` is a rate snapshot with string amounts; jobs/quote gives the exact price of one request.
  const price = m.usd?.perUnit !== undefined ? `$${m.usd.perUnit} ${m.usd.unit ?? ''}` : `see GET /api/v1/models/${m.model}`;
  console.log(m.model.padEnd(60), m.modality.padEnd(6), price);
}
console.error(`${data.total} models`);
