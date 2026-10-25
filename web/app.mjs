const token = document.querySelector('meta[name="demo-token"]').content;
const board = document.getElementById('board');
const search = document.getElementById('search');
const status = document.getElementById('status');
const more = document.getElementById('more');
let cursor = null;
let query = '';
let requestSerial = 0;
let controller = null;
let loadingMore = false;

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
      if (!response.ok) throw new Error('bookmark request failed');
      const body = await response.json();
      if (typeof body.saved !== 'boolean' || !Number.isInteger(body.version)) throw new Error('invalid bookmark response');
      post.saved = body.saved;
      post.version = body.version;
      setBookmarkButton(button, post.saved);
    } catch {
      post.saved = previousSaved;
      post.version = previousVersion;
      setBookmarkButton(button, post.saved);
      status.textContent = 'Could not save post.';
    } finally {
      button.disabled = false;
    }
  });
  card.append(button);
  return card;
}

async function fetchPage(reset) {
  if (!reset && (loadingMore || !cursor)) return;
  if (reset) {
    requestSerial += 1;
    controller?.abort();
    cursor = null;
  }
  const serial = requestSerial;
  const requestController = new AbortController();
  controller = requestController;
  if (!reset) loadingMore = true;
  status.textContent = 'Loading discussions…';
  const params = new URLSearchParams({ q: query, limit: '8' });
  if (cursor && !reset) params.set('cursor', cursor);
  try {
    const response = await fetch(`/api/feed?${params}`, {
      headers: { authorization: `Bearer ${token}` },
      signal: requestController.signal,
    });
    if (!response.ok) throw new Error('feed request failed');
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
    if (error.name !== 'AbortError' && serial === requestSerial) status.textContent = 'Could not load discussions.';
  } finally {
    if (serial === requestSerial) {
      loadingMore = false;
      if (controller === requestController) controller = null;
    }
  }
}

search.addEventListener('input', () => {
  query = search.value;
  fetchPage(true);
});
more.addEventListener('click', () => fetchPage(false));
fetchPage(true);
