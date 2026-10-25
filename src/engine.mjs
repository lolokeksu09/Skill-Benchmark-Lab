/**
 * Benchmark-only local fixture. `demo-*` bearer credentials are test fixtures,
 * not production secrets; this server must not be deployed on the internet.
 */
import { createHmac, randomBytes } from 'node:crypto';

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

export function createEngine(posts = seedPosts()) {
  const items = posts.map(post => ({ ...post }));
  const bookmarks = new Map();
  const cursorSecret = randomBytes(32);

  function encodeCursor(data) {
    const unsigned = JSON.stringify(data);
    const sig = createHmac('sha256', cursorSecret).update(unsigned).digest('base64url');
    return Buffer.from(JSON.stringify({ ...data, sig }), 'utf8').toString('base64url');
  }

  function decodeCursor(cursor) {
    if (!/^[A-Za-z0-9_-]+$/.test(cursor)) throw new Error('invalid cursor');
    const raw = Buffer.from(cursor, 'base64url').toString('utf8');
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('invalid cursor');
    const { sig, ...data } = parsed;
    if (typeof sig !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(sig)) throw new Error('invalid cursor');
    const expected = createHmac('sha256', cursorSecret).update(JSON.stringify(data)).digest('base64url');
    if (sig !== expected || typeof data.viewer !== 'string' || typeof data.search !== 'string' ||
        typeof data.id !== 'string' || typeof data.createdAt !== 'string') throw new Error('invalid cursor');
    return data;
  }

  function feed(viewer, { q = '', limit = '8', cursor = '' } = {}) {
    if (!viewer) return { status: 401, body: { error: 'unauthorized' } };
    if (typeof limit !== 'string' || !/^(?:[1-9]|1[0-5])$/.test(limit)) {
      return { status: 400, body: { error: 'invalid limit' } };
    }
    const size = Number(limit);
    const search = String(q).trim().toLowerCase();
    let marker = null;
    if (cursor) {
      try { marker = decodeCursor(cursor); }
      catch { return { status: 400, body: { error: 'invalid cursor' } }; }
      if (marker.viewer !== viewer || marker.search !== search) {
        return { status: 400, body: { error: 'invalid cursor' } };
      }
    }
    const visible = items
      .filter(post => post.visibility === 'public' || post.owner === viewer)
      .filter(post => `${post.title} ${post.summary}`.toLowerCase().includes(search))
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt) || a.id.localeCompare(b.id));
    if (marker && !visible.some(post => post.id === marker.id && post.createdAt === marker.createdAt)) {
      return { status: 400, body: { error: 'invalid cursor' } };
    }
    const start = marker ? visible.findIndex(post => post.createdAt < marker.createdAt ||
      (post.createdAt === marker.createdAt && post.id > marker.id)) : 0;
    const page = visible.slice(marker ? start : 0, (marker ? start : 0) + size).map(post => {
      const state = bookmarks.get(`${viewer}:${post.id}`) ?? { saved: false, version: 0 };
      return { ...post, saved: state.saved, version: state.version };
    });
    const last = page.at(-1);
    return {
      status: 200,
      body: {
        items: page,
        nextCursor: last && ((marker ? start : 0) + page.length < visible.length)
          ? encodeCursor({ viewer, search, id: last.id, createdAt: last.createdAt }) : null,
      },
    };
  }

  function bookmark(viewer, id, payload, ifMatch) {
    if (!viewer) return { status: 401, body: { error: 'unauthorized' } };
    const post = items.find(entry => entry.id === id);
    if (!post || (post.visibility === 'private' && post.owner !== viewer)) {
      return { status: 404, body: { error: 'not found' } };
    }
    if (ifMatch === undefined) return { status: 428, body: { error: 'if-match required' } };
    if (!/^"[0-9]+"$/.test(ifMatch)) return { status: 412, body: { error: 'stale version' } };
    if (!payload || typeof payload !== 'object' || Array.isArray(payload) ||
        Object.keys(payload).length !== 1 || typeof payload.saved !== 'boolean') {
      return { status: 400, body: { error: 'invalid body' } };
    }
    const key = `${viewer}:${id}`;
    const old = bookmarks.get(key) ?? { saved: false, version: 0 };
    const expectedVersion = Number(ifMatch.slice(1, -1));
    if (!Number.isSafeInteger(expectedVersion) || expectedVersion !== old.version) {
      return { status: 412, body: { error: 'stale version' } };
    }
    const version = payload.saved === old.saved ? old.version : old.version + 1;
    const newState = { saved: payload.saved, version };
    bookmarks.set(key, newState);
    return { status: 200, headers: { ETag: `"${version}"` }, body: { id, ...newState } };
  }

  return { feed, bookmark };
}
