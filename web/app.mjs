const token = document.querySelector('meta[name="demo-token"]').content;
const board = document.getElementById('board');
const search = document.getElementById('search');
const status = document.getElementById('status');
const more = document.getElementById('more');
let cursor = null;
let query = '';
let requestSerial = 0;
let loadedIds = new Set();

function drawPost(post) {
  const card = document.createElement('article');
  card.className = 'card';
  card.dataset.id = post.id;
  const title = document.createElement('h2');
  title.textContent = post.title;
  const summary = document.createElement('p');
  summary.textContent = post.summary;
  card.append(title, summary);
  const button = document.createElement('button');
  button.className = 'bookmark';
  button.type = 'button';
  const setBookmarkState = saved => {
    button.textContent = saved ? '★' : '☆';
    button.setAttribute('aria-pressed', String(saved));
    button.setAttribute('aria-label', saved ? 'Remove saved post' : 'Save post');
  };
  setBookmarkState(post.saved);
  button.addEventListener('click', async () => {
    const previous = post.saved;
    const next = !previous;
    button.disabled = true;
    let saved = false;
    try {
      const response = await fetch(`/api/bookmarks/${encodeURIComponent(post.id)}`, {
        method: 'PUT',
        headers: {
          authorization: `Bearer ${token}`,
          'content-type': 'application/json',
          'if-match': `"${post.version}"`,
        },
        body: JSON.stringify({ saved: next }),
      });
      if (!response.ok) throw new Error('bookmark write failed');
      const body = await response.json();
      post.version = body.version;
      post.saved = next;
      setBookmarkState(next);
      saved = true;
    } catch {
    } finally {
      if (!saved) {
        post.saved = false;
        setBookmarkState(false);
        status.textContent = 'Could not save bookmark.';
      }
      button.disabled = false;
    }
  });
  card.append(button);
  return card;
}

async function fetchPage(reset) {
  const serial = ++requestSerial;
  if (reset) loadedIds = new Set();
  status.textContent = 'Loading…';
  const params = new URLSearchParams({ q: query, limit: '8' });
  if (cursor && !reset) params.set('cursor', cursor);
  try {
    const response = await fetch(`/api/feed?${params}`, { headers: { authorization: `Bearer ${token}` } });
    if (!response.ok) throw new Error('feed request failed');
    const data = await response.json();
    if (serial !== requestSerial) return;
    if (reset) board.replaceChildren();
    for (const post of data.items) {
      if (loadedIds.has(post.id)) continue;
      loadedIds.add(post.id);
      board.append(drawPost(post));
    }
    cursor = data.nextCursor;
    more.hidden = !cursor;
    status.textContent = `${board.children.length} discussions`;
  } catch {
    if (serial === requestSerial) status.textContent = 'Could not load discussions.';
  }
}

search.addEventListener('input', () => {
  query = search.value;
  cursor = null;
  fetchPage(true);
});
more.addEventListener('click', () => fetchPage(false));
fetchPage(true);
