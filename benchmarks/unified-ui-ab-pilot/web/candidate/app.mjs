const token = document.querySelector('meta[name="demo-token"]').content;
const board = document.getElementById('board');
const search = document.getElementById('search');
const status = document.getElementById('status');
const more = document.getElementById('more');
let cursor = null;
let query = '';
let requestId = 0;
let activeController = null;

function setBookmarkUI(button, post) {
  button.setAttribute('aria-pressed', String(Boolean(post.saved)));
  button.setAttribute('aria-label', (post.saved ? 'Remove saved discussion: ' : 'Save discussion: ') + post.title);
  button.textContent = post.saved ? '★' : '☆';
}
function drawPost(post) {
  const card = document.createElement('article');
  card.className = 'card';
  card.dataset.id = String(post.id);
  const heading = document.createElement('h2');
  heading.textContent = String(post.title);
  const summary = document.createElement('p');
  summary.textContent = String(post.summary);
  const button = document.createElement('button');
  button.className = 'bookmark';
  button.type = 'button';
  setBookmarkUI(button, post);
  button.addEventListener('click', async () => {
    if (button.disabled) return;
    const previousSaved = Boolean(post.saved);
    const previousVersion = post.version;
    post.saved = !previousSaved;
    setBookmarkUI(button, post);
    button.disabled = true;
    try {
      const response = await fetch('/api/bookmarks/' + encodeURIComponent(post.id), {
        method: 'PUT',
        headers: { authorization: 'Bearer ' + token, 'content-type': 'application/json', 'if-match': '"' + previousVersion + '"' },
        body: JSON.stringify({ saved: post.saved }),
      });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const body = await response.json();
      if (!body || !Number.isSafeInteger(body.version) || body.version < previousVersion) throw new Error('Invalid response');
      post.version = body.version;
      status.textContent = post.saved ? 'Discussion saved.' : 'Discussion removed from saved.';
    } catch (_) {
      post.saved = previousSaved;
      post.version = previousVersion;
      setBookmarkUI(button, post);
      status.textContent = 'Could not update saved discussion. Retry the button.';
    } finally { button.disabled = false; }
  });
  card.append(heading, summary, button);
  return card;
}

async function fetchPage(reset) {
  const ownId = ++requestId;
  if (activeController) activeController.abort();
  const controller = new AbortController();
  activeController = controller;
  more.disabled = true;
  status.textContent = reset ? 'Loading discussions…' : 'Loading more discussions…';
  const params = new URLSearchParams({ q: query.trim(), limit: '8' });
  if (!reset && cursor) params.set('cursor', cursor);
  try {
    const response = await fetch('/api/feed?' + params.toString(), { headers: { authorization: 'Bearer ' + token }, signal: controller.signal });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const data = await response.json();
    if (!data || !Array.isArray(data.items) || !(data.nextCursor == null || typeof data.nextCursor === 'string')) throw new Error('Invalid response');
    if (ownId !== requestId) return;
    if (reset) board.replaceChildren();
    const seen = new Set([...board.children].map(el => el.dataset.id));
    for (const post of data.items) {
      if (seen.has(String(post.id))) continue;
      board.append(drawPost(post));
      seen.add(String(post.id));
    }
    cursor = data.nextCursor;
    more.hidden = !cursor;
    status.textContent = board.children.length ? board.children.length + ' discussions' : 'No discussions match your search.';
  } catch (e) {
    if (ownId !== requestId) return;
    if (e.name !== 'AbortError') status.textContent = 'Could not load discussions. Your previous results are preserved; retry the search.';
  } finally {
    if (ownId === requestId) { more.disabled = false; activeController = null; }
  }
}
search.addEventListener('input', () => { query = search.value; fetchPage(true); });
more.addEventListener('click', () => { if (cursor) fetchPage(false); });
fetchPage(true);
