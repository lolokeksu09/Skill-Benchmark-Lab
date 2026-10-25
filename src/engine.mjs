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

function encodeCursor(cursor) {
  return Buffer.from(JSON.stringify(cursor), 'utf8').toString('base64url');
}

function decodeCursor(value) {
  if (!/^[A-Za-z0-9_-]+$/.test(value)) return null;
  try {
    const decoded = Buffer.from(value, 'base64url').toString('utf8');
    const parsed = JSON.parse(decoded);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
    if (typeof parsed.viewer !== 'string' || typeof parsed.search !== 'string' ||
        typeof parsed.createdAt !== 'string' || typeof parsed.id !== 'string') return null;
    return parsed;
  } catch { return null; }
}

export function createEngine(posts = seedPosts()) {
  const items = posts.map(post => ({ ...post }));
  const bookmarks = new Map(); // key: `${viewer}:${postId}` => {saved, version}

  function feed(viewer, { q = '', limit = '8', cursor = '' } = {}) {
    if (!viewer) return { status: 401, body: { error: 'unauthorized' } };
    if (typeof limit !== 'string' || !/^(?:0|[1-9]\d*)$/.test(limit)) return { status: 400, body: { error: 'invalid limit' } };
    const size = Number(limit);
    if (!Number.isInteger(size) || size < 1 || size > 15) return { status: 400, body: { error: 'invalid limit' } };
    const search = String(q).trim().toLowerCase();
    let cursorState = null;
    if (cursor) {
      cursorState = decodeCursor(cursor);
      if (!cursorState || cursorState.viewer !== viewer || cursorState.search !== search) {
        return { status: 400, body: { error: 'invalid cursor' } };
      }
    }
    const visible = items
      .filter(post => post.visibility === 'public' || post.owner === viewer)
      .filter(post => `${post.title} ${post.summary}`.toLowerCase().includes(search))
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt) || a.id.localeCompare(b.id));
    const start = cursorState
      ? visible.findIndex(post => post.createdAt === cursorState.createdAt && post.id === cursorState.id) + 1
      : 0;
    if (cursorState && start === 0) return { status: 400, body: { error: 'invalid cursor' } };
    const page = visible.slice(start, start + size).map(post => {
      const state = bookmarks.get(`${viewer}:${post.id}`) ?? { saved: false, version: 0 };
      return { ...post, saved: state.saved, version: state.version };
    });
    return {
      status: 200,
      body: { items: page, nextCursor: start + size < visible.length && page.length
        ? encodeCursor({ viewer, search, createdAt: page.at(-1).createdAt, id: page.at(-1).id }) : null },
    };
  }

  function bookmark(viewer, id, payload, ifMatch) {
    if (!viewer) return { status: 401, body: { error: 'unauthorized' } };
    const post = items.find(entry => entry.id === id);
    if (!post || (post.visibility === 'private' && post.owner !== viewer)) return { status: 404, body: { error: 'not found' } };
    if (!payload || typeof payload !== 'object' || Array.isArray(payload) || typeof payload.saved !== 'boolean') {
      return { status: 400, body: { error: 'invalid payload' } };
    }
    if (ifMatch === undefined) return { status: 428, body: { error: 'if-match required' } };
    const key = `${viewer}:${id}`;
    const old = bookmarks.get(key) ?? { saved: false, version: 0 };
    if (!/^"\d+"$/.test(ifMatch)) return { status: 400, body: { error: 'invalid if-match' } };
    const expected = Number(ifMatch.slice(1, -1));
    if (!Number.isSafeInteger(expected) || expected !== old.version) return { status: 412, body: { error: 'stale version' } };
    const newState = { saved: payload.saved, version: old.version + (payload.saved === old.saved ? 0 : 1) };
    bookmarks.set(key, newState);
    return { status: 200, headers: { ETag: `"${newState.version}"` }, body: { id, ...newState } };
  }

  return { feed, bookmark };
}
