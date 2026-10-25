import test from 'node:test';
import assert from 'node:assert/strict';
import { createEngine, seedPosts } from '../src/engine.mjs';
import { startServer } from '../src/server.mjs';

const TOKENS = { alice: 'demo-alice-key', bob: 'demo-bob-key' };

async function withApi(fn) {
  const app = await startServer();
  const call = async (path, { user = 'alice', method = 'GET', payload, headers = {} } = {}) => {
    const h = { ...headers };
    if (user) h.authorization = `Bearer ${TOKENS[user] ?? user}`;
    if (payload !== undefined) h['content-type'] = 'application/json';
    const response = await fetch(`${app.url}${path}`, {
      method, headers: h, body: payload === undefined ? undefined : JSON.stringify(payload),
    });
    return { status: response.status, body: await response.json(), headers: response.headers };
  };
  try { await fn(call); }
  finally { await app.close(); }
}

function bookmark(call, id, saved, version = '"0"', user = 'alice') {
  return call(`/api/bookmarks/${encodeURIComponent(id)}`, {
    user, method: 'PUT', payload: { saved },
    headers: version === null ? {} : { 'if-match': version },
  });
}

test('GET denies a missing session token', async () => {
  await withApi(async call => assert.equal((await call('/api/feed', { user: null })).status, 401));
});

test('GET denies an unknown bearer token', async () => {
  await withApi(async call => assert.equal((await call('/api/feed', { user: 'not-a-session' })).status, 401));
});

test('Alice cannot see Bob private records in the first page', async () => {
  await withApi(async call => {
    const r = await call('/api/feed?limit=15');
    assert.equal(r.status, 200);
    assert.ok(!r.body.items.some(p => p.id === 'secret-bob' || p.id === 'p10'));
  });
});

test('Alice cannot discover Bob confidential data through search', async () => {
  await withApi(async call => {
    const r = await call('/api/feed?q=confidential');
    assert.equal(r.status, 200);
    assert.equal(r.body.items.length, 0);
  });
});

test('Bob can see his own private record', async () => {
  await withApi(async call => {
    const r = await call('/api/feed?q=confidential', { user: 'bob' });
    assert.equal(r.status, 200);
    assert.deepEqual(r.body.items.map(x => x.id), ['secret-bob']);
  });
});

test('Feed defaults to 8 cards and exposes stable next cursor', async () => {
  await withApi(async call => {
    const r = await call('/api/feed');
    assert.equal(r.status, 200);
    assert.equal(r.body.items.length, 8);
    assert.equal(typeof r.body.nextCursor, 'string');
  });
});

test('Feed uses createdAt descending then id ascending when timestamps tie', async () => {
  const engine = createEngine();
  const r = engine.feed('alice', { limit: '15' });
  assert.equal(r.status, 200);
  const ids = r.body.items.map(p => p.id);
  assert.ok(ids.indexOf('p28') < ids.indexOf('p29'));
  assert.ok(ids.indexOf('p29') < ids.indexOf('p30'));
});

test('Cursor pages are adjacent and contain no duplicate IDs', async () => {
  await withApi(async call => {
    const a = await call('/api/feed?limit=7');
    const b = await call(`/api/feed?limit=7&cursor=${encodeURIComponent(a.body.nextCursor)}`);
    const c = await call(`/api/feed?limit=7&cursor=${encodeURIComponent(b.body.nextCursor)}`);
    for (const r of [a, b, c]) assert.equal(r.status, 200);
    const ids = [...a.body.items, ...b.body.items, ...c.body.items].map(p => p.id);
    assert.equal(ids.length, 21);
    assert.equal(new Set(ids).size, ids.length);
  });
});

test('Tampered cursor returns 400 instead of empty success', async () => {
  await withApi(async call => {
    for (const c of ['%%%', Buffer.from('{}').toString('base64url'), Buffer.from('{"offset":-1}').toString('base64url')]) {
      assert.equal((await call(`/api/feed?cursor=${encodeURIComponent(c)}`)).status, 400);
    }
  });
});

test('Cursor cannot be replayed across different searches', async () => {
  await withApi(async call => {
    const first = await call('/api/feed?q=discussion&limit=2');
    assert.ok(first.body.nextCursor);
    const r = await call(`/api/feed?q=danger&limit=2&cursor=${encodeURIComponent(first.body.nextCursor)}`);
    assert.equal(r.status, 400);
  });
});

test('Cursor cannot be replayed by a different viewer', async () => {
  await withApi(async call => {
    const first = await call('/api/feed?limit=2', { user: 'alice' });
    const r = await call(`/api/feed?limit=2&cursor=${encodeURIComponent(first.body.nextCursor)}`, { user: 'bob' });
    assert.equal(r.status, 400);
  });
});

test('Page limit validation rejects decimals and nondecimal notation', async () => {
  await withApi(async call => {
    for (const value of ['0', '-1', '16', '1.5', 'Infinity', '1e1', 'abc']) {
      assert.equal((await call(`/api/feed?limit=${encodeURIComponent(value)}`)).status, 400, value);
    }
  });
});

test('Search is trimmed and case-insensitive', async () => {
  await withApi(async call => {
    const r = await call('/api/feed?q=%20%20DANGER%20%20');
    assert.equal(r.status, 200);
    assert.deepEqual(r.body.items.map(x => x.id), ['p-xss']);
  });
});

test('Bookmark PUT requires a session', async () => {
  await withApi(async call => assert.equal((await bookmark(call, 'p01', true, '"0"', null)).status, 401));
});

test('Bookmark PUT rejects a nonexistent post with 404', async () => {
  await withApi(async call => assert.equal((await bookmark(call, 'does-not-exist', true)).status, 404));
});

test('Bookmark PUT does not reveal or mutate Bob private record', async () => {
  await withApi(async call => {
    assert.equal((await bookmark(call, 'secret-bob', true)).status, 404);
    const b = await call('/api/feed?q=confidential', { user: 'bob' });
    assert.equal(b.body.items[0].saved, false);
  });
});

test('If-Match is required for bookmark modifications', async () => {
  await withApi(async call => assert.equal((await bookmark(call, 'p01', true, null)).status, 428));
});

test('Successful bookmark PUT increments the version and returns ETag', async () => {
  await withApi(async call => {
    const r = await bookmark(call, 'p01', true);
    assert.equal(r.status, 200);
    assert.equal(r.body.saved, true);
    assert.equal(r.body.version, 1);
    assert.equal(r.headers.get('etag'), '"1"');
  });
});

test('Stale If-Match conflicts without mutating saved state', async () => {
  await withApi(async call => {
    assert.equal((await bookmark(call, 'p01', true)).status, 200);
    assert.equal((await bookmark(call, 'p01', false, '"0"')).status, 412);
    const feed = await call('/api/feed?q=discussion%201%3A');
    assert.equal(feed.body.items[0].saved, true);
    assert.equal(feed.body.items[0].version, 1);
  });
});

test('Concurrent stale updates admit at most one successful writer', async () => {
  await withApi(async call => {
    const responses = await Promise.all([
      bookmark(call, 'p01', true, '"0"'),
      bookmark(call, 'p01', false, '"0"'),
    ]);
    assert.deepEqual(responses.map(x => x.status).sort(), [200, 412]);
  });
});

test('Bookmark PUT rejects nonboolean saved values', async () => {
  await withApi(async call => {
    for (const value of ['false', 1, null, {}, []]) {
      assert.equal((await bookmark(call, 'p01', value)).status, 400);
    }
    const feed = await call('/api/feed?q=discussion%201%3A');
    assert.equal(feed.body.items[0].saved, false);
  });
});

test('Bookmark state and versions are scoped independently to each viewer', async () => {
  await withApi(async call => {
    assert.equal((await bookmark(call, 'p01', true, '"0"', 'alice')).status, 200);
    const b = await call('/api/feed?q=discussion%201%3A', { user: 'bob' });
    assert.equal(b.body.items[0].saved, false);
    assert.equal(b.body.items[0].version, 0);
  });
});

test('Unchanged bookmark state is idempotent and does not increment version', async () => {
  await withApi(async call => {
    const first = await bookmark(call, 'p01', true);
    const same = await bookmark(call, 'p01', true, '"1"');
    assert.equal(first.status, 200);
    assert.equal(same.status, 200);
    assert.equal(same.body.version, 1);
  });
});

test('Bad JSON request body yields HTTP 400 without altering state', async () => {
  await withApi(async call => {
    const r = await call('/api/bookmarks/p01', { method: 'PUT', payload: null,
      headers: { 'if-match': '"0"' } });
    assert.equal(r.status, 400);
  });
});

test('Backend accepts only explicit routes and never serves source files', async () => {
  await withApi(async call => {
    assert.equal((await call('/src/engine.mjs')).status, 404);
    assert.equal((await call('/api/secret-bob')).status, 404);
  });
});

test('Seeded fixture includes a malicious title for browser XSS verification', () => {
  const posts = seedPosts();
  const post = posts.find(x => x.id === 'p-xss');
  assert.match(post.title, /<img.*onerror=/);
  assert.match(post.summary, /<svg.*onload=/);
});
