/**
 * Benchmark-only local fixture. `demo-*` bearer credentials are test fixtures,
 * not production secrets; this server must not be deployed on the internet.
 */
export const DEMO_TOKENS = Object.freeze({
  'demo-alice-key': 'alice',
  'demo-bob-key': 'bob',
});

export function seedPosts() {
  const posts = [];
  for (let i = 1; i <= 30; i++) {
    const id = `p${String(i).padStart(2, '0')}`;
    const owner = i % 2 === 0 ? 'alice' : 'bob';
    posts.push({
      id,
      owner,
      visibility: i % 10 === 0 ? 'private' : 'public',
      title: `Discussion ${i}: community update`,
      summary: `Highlights from week ${i}.`,
      createdAt: new Date(Date.UTC(2026, 9, 1, 0, 0, Math.floor((i - 1) / 3))).toISOString(),
    });
  }
  posts.push({
    id: 'p-xss', owner: 'bob', visibility: 'public',
    title: '<img src=x onerror="window.__pwned=1"> danger',
    summary: '<svg onload="window.__pwned=2"></svg>',
    createdAt: '2026-10-03T01:00:00.000Z',
  });
  posts.push({
    id: 'secret-bob', owner: 'bob', visibility: 'private',
    title: 'Bob confidential planning', summary: 'Not for Alice',
    createdAt: '2026-10-04T00:00:00.000Z',
  });
  return posts;
}

function encodeCursor(viewer, query, offset) {
  return Buffer.from(JSON.stringify({ viewer, query, offset }), 'utf8').toString('base64url');
}

function decodeCursor(cursor) {
  if (typeof cursor !== 'string' || !/^[A-Za-z0-9_-]+$/.test(cursor)) return null;
  try {
    const value = JSON.parse(Buffer.from(cursor, 'base64url').toString('utf8'));
    if (!value || typeof value !== 'object' || Array.isArray(value) ||
        typeof value.viewer !== 'string' || typeof value.query !== 'string' ||
        !Number.isSafeInteger(value.offset) || value.offset < 0) return null;
    return value;
  } catch { return null; }
}

export function createEngine(posts = seedPosts()) {
  const items = posts.map(post => ({ ...post }));
  const bookmarks = new Map(); // key: `${viewer}:${postId}` => {saved, version}

  function feed(viewer, { q = '', limit = '8', cursor = '' } = {}) {
    if (!viewer) return { status: 401, body: { error: 'unauthorized' } };
    if (typeof limit !== 'string' || !/^(?:0|[1-9][0-9]*)$/.test(limit)) return { status: 400, body: { error: 'invalid limit' } };
    const size = Number(limit);
    if (!Number.isSafeInteger(size) || size < 1 || size > 15) return { status: 400, body: { error: 'invalid limit' } };
    const search = String(q).trim().toLowerCase();
    let offset = 0;
    if (cursor) {
      const decoded = decodeCursor(cursor);
      if (!decoded || decoded.viewer !== viewer || decoded.query !== search) return { status: 400, body: { error: 'invalid cursor' } };
      offset = decoded.offset;
    }
    const visible = items
      .filter(post => post.visibility === 'public' || post.owner === viewer)
      .filter(post => `${post.title} ${post.summary}`.toLowerCase().includes(search))
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt) || a.id.localeCompare(b.id));
    if (offset > visible.length) return { status: 400, body: { error: 'invalid cursor' } };
    const page = visible.slice(offset, offset + size).map(post => {
      const state = bookmarks.get(`${viewer}:${post.id}`) ?? { saved: false, version: 0 };
      return { ...post, saved: state.saved, version: state.version };
    });
    return {
      status: 200,
      body: { items: page, nextCursor: offset + size < visible.length ? encodeCursor(viewer, search, offset + size) : null },
    };
  }

  function bookmark(viewer, id, payload, ifMatch) {
    if (!viewer) return { status: 401, body: { error: 'unauthorized' } };
    const post = items.find(entry => entry.id === id);
    if (!post || (post.visibility === 'private' && post.owner !== viewer)) return { status: 404, body: { error: 'not found' } };
    if (!payload || typeof payload !== 'object' || Array.isArray(payload) ||
        Object.keys(payload).length !== 1 || typeof payload.saved !== 'boolean') {
      return { status: 400, body: { error: 'invalid payload' } };
    }
    if (typeof ifMatch !== 'string') return { status: 428, body: { error: 'if-match required' } };
    const match = /^"([0-9]+)"$/.exec(ifMatch);
    if (!match || !Number.isSafeInteger(Number(match[1]))) return { status: 400, body: { error: 'invalid if-match' } };
    const key = `${viewer}:${id}`;
    const old = bookmarks.get(key) ?? { saved: false, version: 0 };
    const expectedVersion = Number(match[1]);
    if (expectedVersion !== old.version) return { status: 412, body: { error: 'stale version' } };
    const newState = { saved: payload.saved, version: old.version + (payload.saved === old.saved ? 0 : 1) };
    bookmarks.set(key, newState);
    return { status: 200, headers: { ETag: `"${newState.version}"` }, body: { id, ...newState } };
  }

  return { feed, bookmark };
}
