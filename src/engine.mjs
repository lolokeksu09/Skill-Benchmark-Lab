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

export function createEngine(posts = seedPosts()) {
  const items = posts.map(post => ({ ...post }));
  const bookmarks = new Map(); // key: `${viewer}:${postId}` => {saved, version}

  function feed(viewer, { q = '', limit = '8', cursor = '' } = {}) {
    if (!viewer) return { status: 401, body: { error: 'unauthorized' } };
    if (typeof limit !== 'string' || !/^(?:[1-9]|1[0-5])$/.test(limit)) return { status: 400, body: { error: 'invalid limit' } };
    const size = Number(limit);
    const search = String(q).trim().toLowerCase();
    let after = null;
    if (cursor) {
      try {
        const decoded = JSON.parse(Buffer.from(cursor, 'base64url').toString('utf8'));
        if (!decoded || decoded.v !== 1 || decoded.viewer !== viewer || decoded.search !== search
          || typeof decoded.createdAt !== 'string' || typeof decoded.id !== 'string') throw new Error('invalid cursor');
        after = { createdAt: decoded.createdAt, id: decoded.id };
      } catch { return { status: 400, body: { error: 'invalid cursor' } }; }
    }
    const visible = items
      .filter(post => post.visibility === 'public' || post.owner === viewer)
      .filter(post => `${post.title} ${post.summary}`.toLowerCase().includes(search))
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt) || a.id.localeCompare(b.id));
    const start = after ? visible.findIndex(post => post.createdAt === after.createdAt && post.id === after.id) + 1 : 0;
    if (after && start === 0) return { status: 400, body: { error: 'invalid cursor' } };
    const page = visible.slice(start, start + size).map(post => {
      const state = bookmarks.get(`${viewer}:${post.id}`) ?? { saved: false, version: 0 };
      return { ...post, saved: state.saved, version: state.version };
    });
    const last = page.at(-1);
    return {
      status: 200,
      body: { items: page, nextCursor: last && start + page.length < visible.length
        ? encodeCursor({ v: 1, viewer, search, createdAt: last.createdAt, id: last.id }) : null },
    };
  }

  function bookmark(viewer, id, payload, ifMatch) {
    if (!viewer) return { status: 401, body: { error: 'unauthorized' } };
    const post = items.find(entry => entry.id === id);
    if (!post || (post.visibility === 'private' && post.owner !== viewer)) return { status: 404, body: { error: 'not found' } };
    if (!payload || typeof payload !== 'object' || Array.isArray(payload) || typeof payload.saved !== 'boolean'
      || Object.keys(payload).some(key => key !== 'saved')) return { status: 400, body: { error: 'invalid body' } };
    if (typeof ifMatch !== 'string') return { status: 428, body: { error: 'if-match required' } };
    const match = /^"(\d+)"$/.exec(ifMatch);
    if (!match) return { status: 400, body: { error: 'invalid if-match' } };
    const key = `${viewer}:${id}`;
    const old = bookmarks.get(key) ?? { saved: false, version: 0 };
    if (Number(match[1]) !== old.version) return { status: 412, body: { error: 'stale version' } };
    const newState = { saved: payload.saved, version: old.version + (payload.saved === old.saved ? 0 : 1) };
    bookmarks.set(key, newState);
    return { status: 200, headers: { ETag: `"${newState.version}"` }, body: { id, ...newState } };
  }

  return { feed, bookmark };
}
