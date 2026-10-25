const token = document.querySelector('meta[name="demo-token"]').content;
const board = document.getElementById('board');
const search = document.getElementById('search');
const status = document.getElementById('status');
const more = document.getElementById('more');
let cursor = null;
let query = '';
let requestSerial = 0;
let activeRequest;
let loading = false;

function setBookmarkState(button, saved) {
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
  setBookmarkState(button, post.saved);
  button.addEventListener('click', async () => {
    if (button.disabled) return;
    const previous = post.saved;
    const next = !previous;
    post.saved = next;
    setBookmarkState(button, next);
    button.disabled = true;
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
      if (!response.ok) throw new Error('bookmark failed');
      const body = await response.json();
      post.version = body.version;
    } catch {
      post.saved = previous;
      setBookmarkState(button, previous);
      status.textContent = 'Could not save bookmark';
    } finally {
      button.disabled = false;
    }
  });
  card.append(button);
  return card;
}

async function fetchPage(reset) {
  if (loading && !reset) return;
  if (reset) {
    requestSerial += 1;
    activeRequest?.abort();
    activeRequest = new AbortController();
    cursor = null;
  }
  const serial = requestSerial;
  loading = true;
  more.disabled = true;
  status.textContent = 'Loading discussions…';
  const params = new URLSearchParams({ q: query, limit: '8' });
  if (cursor && !reset) params.set('cursor', cursor);
  try {
    const response = await fetch(`/api/feed?${params}`, {
      headers: { authorization: `Bearer ${token}` },
      signal: activeRequest?.signal,
    });
    if (!response.ok) throw new Error('feed failed');
    const data = await response.json();
    if (serial !== requestSerial) return;
    if (reset) board.replaceChildren();
    const existing = new Set([...board.children].map(card => card.dataset.id));
    for (const post of data.items) {
      if (!existing.has(post.id)) board.append(drawPost(post));
    }
    cursor = data.nextCursor;
    more.hidden = !cursor;
    status.textContent = `${board.children.length} discussions`;
  } catch (error) {
    if (error.name !== 'AbortError' && serial === requestSerial) status.textContent = 'Could not load discussions';
  } finally {
    if (serial === requestSerial) {
      loading = false;
      more.disabled = false;
    }
  }
}

search.addEventListener('input', () => {
  query = search.value;
  fetchPage(true);
});
more.addEventListener('click', () => fetchPage(false));
fetchPage(true);
