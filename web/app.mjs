const token = document.querySelector('meta[name="demo-token"]').content;
const board = document.getElementById('board');
const search = document.getElementById('search');
const status = document.getElementById('status');
const more = document.getElementById('more');
let cursor = null;
let query = '';
let requestSerial = 0;

function setBookmarkButton(button, saved) {
  button.textContent = saved ? '★' : '☆';
  button.setAttribute('aria-pressed', String(saved));
  button.setAttribute('aria-label', saved ? 'Remove saved post' : 'Save post');
}

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
  setBookmarkButton(button, post.saved);
  button.addEventListener('click', async () => {
    const previousSaved = post.saved;
    const previousVersion = post.version;
    post.saved = !previousSaved;
    setBookmarkButton(button, post.saved);
    button.disabled = true;
    try {
      const response = await fetch(`/api/bookmarks/${encodeURIComponent(post.id)}`, {
        method: 'PUT',
        headers: {
          authorization: `Bearer ${token}`,
          'content-type': 'application/json',
          'if-match': `"${previousVersion}"`,
        },
        body: JSON.stringify({ saved: post.saved }),
      });
      let body = null;
      try { body = await response.json(); } catch { /* handled below */ }
      if (!response.ok || !body || typeof body.saved !== 'boolean' || !Number.isSafeInteger(body.version)) {
        throw new Error('bookmark rejected');
      }
      post.saved = body.saved;
      post.version = body.version;
      setBookmarkButton(button, post.saved);
    } catch {
      post.saved = previousSaved;
      post.version = previousVersion;
      setBookmarkButton(button, post.saved);
      status.textContent = 'Could not save bookmark. Please try again.';
    } finally {
      button.disabled = false;
    }
  });
  card.append(button);
  return card;
}

async function fetchPage(reset) {
  const serial = ++requestSerial;
  if (reset) query = search.value;
  const params = new URLSearchParams({ q: query, limit: '8' });
  if (cursor && !reset) params.set('cursor', cursor);
  status.textContent = 'Loading discussions…';
  more.disabled = true;
  try {
    const response = await fetch(`/api/feed?${params}`, { headers: { authorization: `Bearer ${token}` } });
    const data = await response.json();
    if (!response.ok || !data || !Array.isArray(data.items) || !(data.nextCursor === null || typeof data.nextCursor === 'string')) {
      throw new Error('feed rejected');
    }
    if (serial !== requestSerial) return;
    if (reset) board.replaceChildren();
    for (const post of data.items) board.append(drawPost(post));
    cursor = data.nextCursor;
    more.hidden = !cursor;
    status.textContent = `${board.children.length} discussions`;
  } catch {
    if (serial === requestSerial) status.textContent = 'Could not load discussions. Please try again.';
  } finally {
    if (serial === requestSerial) more.disabled = false;
  }
}

search.addEventListener('input', () => {
  cursor = null;
  fetchPage(true);
});
more.addEventListener('click', () => fetchPage(false));
fetchPage(true);
