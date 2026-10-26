import test from 'node:test';
import { strict as assert } from 'node:assert';
import { startServer } from '../src/server.mjs';

const TOKEN = { alice: 'demo-alice-key', bob: 'demo-bob-key' };

async function withApi(run) {
  const app = await startServer();
  const call = async (path, { user = 'alice', method = 'GET', body, headers = {} } = {}) => {
    const requestHeaders = { ...headers };
    if (user) requestHeaders.authorization = `Bearer ${TOKEN[user] ?? user}`;
    if (body !== undefined) requestHeaders['content-type'] = 'application/json';
    const response = await fetch(`${app.url}${path}`, {
      method,
      headers: requestHeaders,
      body: body === undefined ? undefined : typeof body === 'string' ? body : JSON.stringify(body),
    });
    const text = await response.text();
    let json = null;
    try { json = JSON.parse(text); } catch {}
    return { status: response.status, body: json, headers: response.headers, text };
  };
  try { await run(call); }
  finally { await app.close(); }
}

function recorder() {
  const failures = [];
  return {
    check(condition, message) { if (!condition) failures.push(message); },
    equal(actual, expected, message) {
      if (actual !== expected) failures.push(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
    },
    finish() { assert.deepEqual(failures, [], failures.join('\n')); },
  };
}

test('V6-1 auth, private data, malformed JSON and server recovery', async () => {
  await withApi(async call => {
    const r = recorder();
    r.equal((await call('/api/feed', { user: null })).status, 401, 'anonymous feed must be denied');

    const alice = await call('/api/feed?limit=15');
    r.equal(alice.status, 200, 'Alice feed should load');
    r.check(!alice.body?.items?.some(post => post.id === 'secret-bob'), 'Alice feed leaked Bob private record');

    const hiddenSearch = await call('/api/feed?q=confidential');
    r.equal(hiddenSearch.body?.items?.length, 0, 'private search should not reveal Bob record');
    const bob = await call('/api/feed?q=confidential', { user: 'bob' });
    r.check(bob.body?.items?.some(post => post.id === 'secret-bob'), 'Bob must see his own private record');

    const privateWrite = await call('/api/bookmarks/secret-bob', {
      method: 'PUT', body: { saved: true }, headers: { 'if-match': '"0"' },
    });
    r.equal(privateWrite.status, 404, 'Alice must not mutate Bob private record');

    const initial = await call('/api/bookmarks/p28', {
      method: 'PUT', body: { saved: true }, headers: { 'if-match': '"0"' },
    });
    r.equal(initial.status, 200, 'setup bookmark save should succeed');
    const malformed = await call('/api/bookmarks/p28', {
      method: 'PUT', body: '{', headers: { 'if-match': '"1"' },
    });
    r.equal(malformed.status, 400, 'authenticated malformed JSON must be rejected');
    const after = await call('/api/feed?q=discussion%2028');
    const saved = after.body?.items?.find(post => post.id === 'p28');
    r.check(saved?.saved === true, 'malformed JSON changed saved state');
    r.equal((await call('/api/feed')).status, 200, 'server must remain responsive after malformed JSON');
    r.finish();
  });
});

test('V6-2 complete pagination and strict cursor/limit contract', async () => {
  await withApi(async call => {
    const r = recorder();
    let cursor = '';
    const ids = [];
    let terminal = false;
    for (let page = 0; page < 20; page++) {
      const path = `/api/feed?limit=7${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`;
      const response = await call(path);
      if (response.status !== 200 || !Array.isArray(response.body?.items)) {
        r.check(false, `page ${page + 1} did not return a valid feed page (HTTP ${response.status})`);
        break;
      }
      ids.push(...response.body.items.map(post => post.id));
      cursor = response.body.nextCursor;
      if (!cursor) { terminal = true; break; }
    }
    r.check(terminal, 'pagination did not terminate within 20 pages');
    r.equal(new Set(ids).size, ids.length, 'pagination returned duplicate IDs');
    r.check(!ids.includes('secret-bob'), 'pagination exposed another viewer private record');

    for (const limit of ['0', '16', '1e1']) {
      r.equal((await call(`/api/feed?limit=${encodeURIComponent(limit)}`)).status, 400, `invalid limit ${limit}`);
    }
    const impossible = Buffer.from(JSON.stringify({ offset: 9999 })).toString('base64url');
    r.equal((await call(`/api/feed?cursor=${impossible}`)).status, 400, 'impossible cursor must be rejected');

    const first = await call('/api/feed?q=discussion&limit=2');
    const replay = await call(`/api/feed?q=danger&limit=2&cursor=${encodeURIComponent(first.body?.nextCursor ?? '')}`);
    r.equal(replay.status, 400, 'cursor must be bound to the query');
    r.finish();
  });
});

test('V6-3 concurrent bookmark compare-and-swap is atomic at the HTTP boundary', async () => {
  await withApi(async call => {
    const r = recorder();
    const feed = await call('/api/feed?q=discussion%2028');
    const post = feed.body?.items?.find(item => item.id === 'p28');
    r.check(Boolean(post), 'fixture post p28 must be visible');
    const version = post?.version ?? 0;
    const etag = `"${version}"`;
    const results = await Promise.all([
      call('/api/bookmarks/p28', { method: 'PUT', body: { saved: true }, headers: { 'if-match': etag } }),
      call('/api/bookmarks/p28', { method: 'PUT', body: { saved: true }, headers: { 'if-match': etag } }),
    ]);
    r.equal(results.filter(result => result.status === 200).length, 1, 'exactly one CAS write must succeed');
    r.equal(results.filter(result => result.status === 412).length, 1, 'exactly one stale CAS write must fail');
    const success = results.find(result => result.status === 200);
    r.equal(success?.headers.get('etag'), `"${success?.body?.version}"`, 'ETag must match returned version');
    const finalFeed = await call('/api/feed?q=discussion%2028');
    const finalPost = finalFeed.body?.items?.find(item => item.id === 'p28');
    r.check(finalPost?.saved === true, 'successful write must remain saved');
    r.equal(finalPost?.version, version + 1, 'version must increment exactly once');
    r.finish();
  });
});
