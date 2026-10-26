// Independent V5 observations. Candidates and frozen V4 tests are read-only.
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { createHmac } from 'node:crypto';
import { runInNewContext } from 'node:vm';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const sha = process.env.V5_SHA, alias = process.env.V5_ALIAS;
if (!/^[0-9a-f]{40}$/.test(sha || '') || !/^[A-E]$/.test(alias || '')) throw new Error('V5_SHA / V5_ALIAS required');
const root = resolve('candidate');
const actualSha = execFileSync('git', ['-C', root, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
if (actualSha !== sha) throw new Error('Candidate SHA mismatch: ' + actualSha);
const { createEngine } = await import(pathToFileURL(resolve(root, 'src/engine.mjs')).href);
const { startServer } = await import(pathToFileURL(resolve(root, 'src/server.mjs')).href);
const cases = {};
const observe = async (name, fn) => {
  try { cases[name] = await fn(); }
  catch (err) { cases[name] = { probeError: String(err?.stack || err) }; }
};
await observe('privacy_control', () => {
  const e = createEngine();
  return {
    visibleIds: e.feed('alice', { q: 'confidential' }).body?.items?.map(x => x.id),
    forbiddenWrite: e.bookmark('alice', 'secret-bob', { saved: true }, '"0"').status,
  };
});
await observe('parallel_bookmark_cas', async () => {
  const s = await startServer();
  try {
    const request = (saved) => fetch(s.url + '/api/bookmarks/p01', {
      method: 'PUT',
      headers: {
        authorization: 'Bearer demo-alice-key',
        'content-type': 'application/json',
        'if-match': '"0"',
      },
      body: JSON.stringify({ saved }),
    });
    // Exercise the actual HTTP boundary with overlapping requests; direct synchronous
    // engine calls inside Promise.all would only test sequential stale-version handling.
    const responses = await Promise.all([request(true), request(false)]);
    const statuses = responses.map(response => response.status).sort((a, b) => a - b);
    return {
      statuses,
      expectation: 'two overlapping authenticated HTTP PUTs with one If-Match version yield one 200 and one 412',
    };
  } finally {
    await s.close();
  }
});
await observe('constructed_out_of_range_cursor', () => {
  const e = createEngine();
  const token = e.feed('alice', { limit: '2' }).body?.nextCursor;
  if (!token) throw new Error('No first page cursor');
  let mutated;
  if (token.includes('.')) {
    const data = JSON.parse(Buffer.from(token.split('.')[0], 'base64url').toString('utf8'));
    data.id = 'v5-nonexistent-anchor';
    const raw = Buffer.from(JSON.stringify(data)).toString('base64url');
    mutated = raw + '.' + createHmac('sha256', 'community-feed-v4-cursor').update(raw).digest('base64url');
  } else {
    const data = JSON.parse(Buffer.from(token, 'base64url').toString('utf8'));
    data.offset = 1000000;
    mutated = Buffer.from(JSON.stringify(data)).toString('base64url');
  }
  const result = e.feed('alice', { limit: '2', cursor: mutated });
  return { status: result.status, returnedItems: result.body?.items?.length ?? null,
    expectation: '400 for nonexistent cursor position' };
});
await observe('unsafe_if_match_integer', () => {
  const result = createEngine().bookmark('alice', 'p01', { saved: true }, '"9007199254740993"');
  return { status: result.status, expectation: 'V5 defense: reject unsafe integer as 400' };
});
await observe('anonymous_invalid_json', async () => {
  const s = await startServer();
  try {
    const res = await fetch(s.url + '/api/bookmarks/p01',
      { method: 'PUT', headers: { 'content-type': 'application/json' }, body: '{' });
    return { status: res.status, body: await res.json(), expectation: '401 for unauthenticated API request' };
  } finally { await s.close(); }
});

function element(tag) {
  const handlers = new Map(), attrs = new Map();
  let children = [];
  return {
    tag, className: '', textContent: '', dataset: {}, hidden: false, disabled: false, value: '',
    get children() { return children; },
    append(...nodes) { children.push(...nodes); },
    replaceChildren(...nodes) { children = [...nodes]; },
    setAttribute(key, val) { attrs.set(key, String(val)); },
    getAttribute(key) { return attrs.get(key) ?? null; },
    addEventListener(key, fn) {
      if (!handlers.has(key)) handlers.set(key, []);
      handlers.get(key).push(fn);
    },
    click() {
      if (this.disabled) return;
      for (const fn of handlers.get('click') || []) fn({ type: 'click' });
    },
  };
}
async function mockClient() {
  const board = element('section'), search = element('input'), status = element('p'), more = element('button');
  const queue = [];
  const document = {
    querySelector(s) { return s === 'meta[name="demo-token"]' ? { content: 'demo-alice-key' } : null; },
    getElementById(id) { return { board, search, status, more }[id]; },
    createElement: element,
  };
  const fakeFetch = (url, options) => {
    let done;
    const pending = new Promise(resolvePromise => { done = resolvePromise; });
    queue.push({ url: String(url), options: options ?? {}, done });
    return pending;
  };
  const js = await readFile(resolve(root, 'web/app.mjs'), 'utf8');
  runInNewContext(js, { document, fetch: fakeFetch, URLSearchParams, AbortController, console },
    { filename: 'web/app.mjs', timeout: 2000 });
  const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };
  return { board, status, more, queue, flush };
}
const ok = value => ({ ok: true, status: 200, json: async () => value });
const post = { id: 'p01', title: 'Sample', summary: 'Safe', saved: false, version: 0 };
await observe('rapid_double_load_more', async () => {
  const c = await mockClient();
  if (c.queue.length !== 1) throw new Error('Initial feed request missing');
  c.queue[0].done(ok({ items: [{ ...post }], nextCursor: 'page2' }));
  await c.flush();
  if (c.more.hidden) throw new Error('Load more not visible');
  c.more.click();
  c.more.click();
  const subsequent = c.queue.filter(r => r.url.startsWith('/api/feed')).slice(1);
  for (const request of subsequent) request.done(ok({ items: [{ ...post, id: 'p02' }], nextCursor: null }));
  await c.flush();
  return { additionalFeedRequests: subsequent.length,
    renderedP02Cards: c.board.children.filter(card => card.dataset.id === 'p02').length,
    expectation: 'one request and one rendered p02 card after competing Load more clicks' };
});
await observe('malformed_200_bookmark', async () => {
  const c = await mockClient();
  c.queue[0].done(ok({ items: [{ ...post }], nextCursor: null }));
  await c.flush();
  const button = c.board.children[0]?.children?.at(-1);
  if (!button) throw new Error('Bookmark button missing');
  button.click();
  const first = c.queue.find(r => r.url.startsWith('/api/bookmarks/'));
  if (!first) throw new Error('Bookmark fetch missing');
  first.done(ok({ id: 'p01', saved: 'invalid', version: 'bad' }));
  await c.flush();
  const aria = button.getAttribute('aria-pressed'), announced = c.status.textContent.includes('Could not');
  button.click();
  const calls = c.queue.filter(r => r.url.startsWith('/api/bookmarks/'));
  return { ariaAfterMalformedResponse: aria,
    retryIfMatch: calls.at(-1)?.options?.headers?.['if-match'] ?? null,
    reportedError: announced, expectation: 'aria false, retry If-Match "0", error announcement' };
});
await observe('mismatched_200_bookmark_id', async () => {
  const c = await mockClient();
  c.queue[0].done(ok({ items: [{ ...post }], nextCursor: null }));
  await c.flush();
  const button = c.board.children[0]?.children?.at(-1);
  if (!button) throw new Error('Bookmark button missing');
  button.click();
  const first = c.queue.find(r => r.url.startsWith('/api/bookmarks/'));
  if (!first) throw new Error('Bookmark fetch missing');
  first.done(ok({ id: 'wrong-post', saved: true, version: 1 }));
  await c.flush();
  const aria = button.getAttribute('aria-pressed'), announced = c.status.textContent.includes('Could not');
  button.click();
  const calls = c.queue.filter(r => r.url.startsWith('/api/bookmarks/'));
  return { ariaAfterMismatchedId: aria,
    retryIfMatch: calls.at(-1)?.options?.headers?.['if-match'] ?? null,
    reportedError: announced, expectation: 'reject mismatched post id; aria false and retry If-Match "0"' };
});
const result = {
  schema: 'v5-observations-v1', alias, sha, actualSha, node: process.version,
  semantics: 'observations are evidence, not pass counts; assess relevance in report', cases,
};
await mkdir('audit/v5/results', { recursive: true });
await writeFile('audit/v5/results/' + alias + '.json', JSON.stringify(result, null, 2) + '\n');
console.log('V5_OBSERVATIONS ' + JSON.stringify(result));
if (Object.values(cases).some(v => v?.probeError)) process.exitCode = 2;
