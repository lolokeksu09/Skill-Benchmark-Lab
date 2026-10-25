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

function encodeCursor(offset) {
  return Buffer.from(JSON.stringify({ offset }), 'utf8').toString('base64url');
}

export function createEngine(posts = seedPosts()) {
  const items = posts.map(post => ({ ...post }));
  const bookmarks = new Map(); // key: `${viewer}:${postId}` => {saved, version}

  function feed(viewer, { q = '', limit = '8', cursor = '' } = {}) {
    if (!viewer) return { status: 401, body: { error: 'unauthorized' } };
    const size = Number(limit);
    if (!Number.isInteger(size) || size < 1 || size > 15) return { status: 400, body: { error: 'invalid limit' } };
    let offset = 0;
    if (cursor) {
      try { offset = JSON.parse(Buffer.from(cursor, 'base64url').toString()).offset; }
      catch { return { status: 400, body: { error: 'invalid cursor' } }; }
    }
    const search = String(q).trim().toLowerCase();
    const visible = items
      .filter(post => post.visibility === 'public' || post.owner === viewer || post.visibility === 'private')
      .filter(post => `${post.title} ${post.summary}`.toLowerCase().includes(search))
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
    const page = visible.slice(offset, offset + size).map(post => {
      const state = bookmarks.get(`${viewer}:${post.id}`) ?? { saved: false, version: 0 };
      return { ...post, saved: state.saved, version: state.version };
    });
    return {
      status: 200,
      body: { items: page, nextCursor: offset + size < visible.length ? encodeCursor(offset + size) : null },
    };
  }

  function bookmark(viewer, id, payload, ifMatch) {
    if (!viewer) return { status: 401, body: { error: 'unauthorized' } };
    const post = items.find(entry => entry.id === id);
    if (!post) return { status: 404, body: { error: 'not found' } };
    const key = `${viewer}:${id}`;
    const old = bookmarks.get(key) ?? { saved: false, version: 0 };
    const newState = { saved: Boolean(payload?.saved), version: old.version };
    bookmarks.set(key, newState);
    return { status: 200, headers: { ETag: `"${newState.version}"` }, body: { id, ...newState } };
  }

  return { feed, bookmark };
}
