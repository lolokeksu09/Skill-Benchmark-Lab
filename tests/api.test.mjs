import test from 'node:test';
import { spawn } from 'node:child_process';
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


// V4 regressions: each withApi call creates an independent HTTP server.
test('All keyset pages enumerate the full authorized feed without overlaps or gaps', async () => {
  await withApi(async call => {
    const expected = seedPosts().filter(p => p.visibility === 'public' || p.owner === 'alice');
    let cursor = null;
    const items = [];
    for (let iteration = 0; iteration < 20; iteration++) {
      const path = '/api/feed?limit=3' + (cursor ? '&cursor=' + encodeURIComponent(cursor) : '');
      const r = await call(path);
      assert.equal(r.status, 200);
      items.push(...r.body.items);
      cursor = r.body.nextCursor;
      if (cursor === null) break;
      assert.ok(iteration < 19, 'cursor must eventually terminate');
    }
    const ids = items.map(p => p.id);
    assert.equal(ids.length, expected.length);
    assert.equal(new Set(ids).size, expected.length);
    assert.deepEqual([...ids].sort(), expected.map(p => p.id).sort());
    for (let i = 1; i < items.length; i++) {
      const prev = items[i - 1], curr = items[i];
      assert.ok(prev.createdAt > curr.createdAt || (
        prev.createdAt === curr.createdAt && prev.id.localeCompare(curr.id) < 0
      ), 'stable descending timestamp and ascending tied ID');
    }
  });
});

test('Bob can bookmark his private post, Alice cannot mutate it or infer its state', async () => {
  await withApi(async call => {
    const allowed = await bookmark(call, 'secret-bob', true, '"0"', 'bob');
    assert.equal(allowed.status, 200);
    assert.equal(allowed.body.saved, true);
    const denied = await bookmark(call, 'secret-bob', false, '"1"', 'alice');
    assert.equal(denied.status, 404);
    const own = await call('/api/feed?q=confidential', { user: 'bob' });
    assert.equal(own.body.items[0].saved, true);
    assert.equal(own.body.items[0].version, 1);
  });
});

test('Bookmark payload containing extra properties is rejected without mutation', async () => {
  await withApi(async call => {
    const r = await call('/api/bookmarks/p01', {
      method: 'PUT', payload: { saved: true, elevated: true },
      headers: { 'if-match': '"0"' },
    });
    assert.equal(r.status, 400);
    const feed = await call('/api/feed?q=discussion%201%3A');
    assert.equal(feed.body.items[0].saved, false);
    assert.equal(feed.body.items[0].version, 0);
  });
});

test('A stale no-op bookmark write is rejected rather than bypassing If-Match', async () => {
  await withApi(async call => {
    assert.equal((await bookmark(call, 'p01', true, '"0"')).status, 200);
    const stale = await bookmark(call, 'p01', true, '"0"');
    assert.equal(stale.status, 412);
    const feed = await call('/api/feed?q=discussion%201%3A');
    assert.equal(feed.body.items[0].version, 1);
  });
});

test('Malformed If-Match values return 400 and do not mutate data', async () => {
  await withApi(async call => {
    for (const value of ['W/"0"', '0', '"nope"', '"0" and more', '"-1"']) {
      const r = await bookmark(call, 'p01', true, value);
      assert.equal(r.status, 400, value);
    }
    const feed = await call('/api/feed?q=discussion%201%3A');
    assert.equal(feed.body.items[0].saved, false);
    assert.equal(feed.body.items[0].version, 0);
  });
});

test('Two same-state simultaneous writes at one version admit exactly one winner', async () => {
  await withApi(async call => {
    const responses = await Promise.all([
      bookmark(call, 'p01', true, '"0"'),
      bookmark(call, 'p01', true, '"0"'),
    ]);
    assert.deepEqual(responses.map(r => r.status).sort(), [200, 412]);
    const feed = await call('/api/feed?q=discussion%201%3A');
    assert.equal(feed.body.items[0].saved, true);
    assert.equal(feed.body.items[0].version, 1);
  });
});

test('Malformed percent-encoding in bookmark ID is a 400 JSON response, not a server crash', async () => {
  // An intentionally broken async HTTP handler can leave a socket hanging.
  // Exercise it in a child process with a bounded request so baseline
  // sensitivity can finish without hanging the whole Node test runner.
  const child = spawn(process.execPath, ['src/server.mjs'], {
    cwd: process.cwd(), env: { ...process.env, PORT: '0' },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  try {
    const base = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('server startup timed out')), 5000);
      child.stdout.once('data', chunk => {
        const m = String(chunk).match(/http:\/\/127\.0\.0\.1:\d+/);
        clearTimeout(timeout);
        if (m) resolve(m[0]);
        else reject(new Error('server did not report listening URL'));
      });
      child.once('error', error => { clearTimeout(timeout); reject(error); });
      child.once('exit', code => { clearTimeout(timeout); reject(new Error('server exited early: ' + code)); });
    });
    const response = await fetch(base + '/api/bookmarks/%E0%A4%A', {
      method: 'PUT',
      headers: {
        authorization: 'Bearer demo-alice-key',
        'content-type': 'application/json',
        'if-match': '"0"',
      },
      body: JSON.stringify({ saved: true }),
      signal: AbortSignal.timeout(2500),
    });
    assert.equal(response.status, 400);
    const body = await response.json();
    assert.match(String(body.error), /invalid/i);
    const healthy = await fetch(base + '/api/feed', {
      headers: { authorization: 'Bearer demo-alice-key' },
      signal: AbortSignal.timeout(2500),
    });
    assert.equal(healthy.status, 200, 'server must remain available');
  } finally {
    child.kill();
  }
});
