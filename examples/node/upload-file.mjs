// Upload a local image, video or audio file and print the popnow:// URI to use in task input.
// Three calls: ask for an upload ticket, PUT the bytes, commit.
// Usage: node upload-file.mjs photo.png image/png   (Node.js 18+, no dependencies)
import { readFile } from 'node:fs/promises';

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

const [path, contentType] = process.argv.slice(2);
if (!path || !contentType) throw new Error('usage: node upload-file.mjs <file> <content-type>');
const bytes = await readFile(path);

// 1. Ticket: declare the exact size and type; the server chooses the storage path.
const ticket = await api('/common/upload-url', { method: 'POST', body: { contentType, bytes: bytes.length } });

// 2. PUT the bytes with every header from the ticket and no Authorization header.
const put = await fetch(ticket.uploadUrl, { method: ticket.method, headers: ticket.headers, body: bytes });
if (!put.ok) throw new Error(`upload failed with HTTP ${put.status}`);

// 3. Commit: verifies size, type and file signature, then returns the URI.
const file = await api(`/files/${ticket.fileId}/commit`, { method: 'POST' });
console.log(file.uri);
console.error(`expires ${file.expiresAt}; use it soon, or save it to your asset library`);
