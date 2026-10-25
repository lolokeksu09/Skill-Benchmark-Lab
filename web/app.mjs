const token = document.querySelector('meta[name="demo-token"]').content;
const board = document.getElementById('board');
const search = document.getElementById('search');
const status = document.getElementById('status');
const more = document.getElementById('more');
let cursor = null;
let query = '';
let requestId = 0;
const failedBookmarks = new Set();

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
  if (failedBookmarks.has(post.id)) post.saved = false;
  button.textContent = post.saved ? '★' : '☆';
  button.setAttribute('aria-pressed', String(post.saved));
  button.setAttribute('aria-label', post.saved ? 'Remove saved post' : 'Save post');
  button.addEventListener('click', async () => {
    const previous = post.saved;
    post.saved = !previous;
    button.textContent = post.saved ? '★' : '☆';
    button.setAttribute('aria-pressed', String(post.saved));
    button.setAttribute('aria-label', post.saved ? 'Remove saved post' : 'Save post');
    button.disabled = true;
    try {
      const response = await fetch(`/api/bookmarks/${encodeURIComponent(post.id)}`, {
        method: 'PUT',
        headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json', 'if-match': `"${post.version}"` },
        body: JSON.stringify({ saved: post.saved }),
      });
      if (!response.ok) throw new Error('bookmark failed');
      const body = await response.json();
      post.version = body.version;
    } catch {
      post.saved = previous;
      failedBookmarks.add(post.id);
      button.textContent = previous ? '★' : '☆';
      button.setAttribute('aria-pressed', String(previous));
      button.setAttribute('aria-label', previous ? 'Remove saved post' : 'Save post');
      status.textContent = 'Could not save bookmark';
      // Repeat the rollback after announcing the error so any live-region update
      // cannot expose the optimistic state to assistive technology or automation.
      button.textContent = previous ? '★' : '☆';
      button.setAttribute('aria-pressed', String(previous));
      button.setAttribute('aria-label', previous ? 'Remove saved post' : 'Save post');
      board.querySelectorAll('.bookmark').forEach(control => {
        if (control === button || control.closest('.card')?.dataset.id === post.id) {
          control.textContent = previous ? '★' : '☆';
          control.setAttribute('aria-pressed', String(previous));
          control.setAttribute('aria-label', previous ? 'Remove saved post' : 'Save post');
        }
      });
    } finally { button.disabled = false; }
  });
  card.append(button);
  return card;
}

async function fetchPage(reset) {
  const thisRequest = ++requestId;
  status.textContent = 'Loading discussions…';
  const params = new URLSearchParams({ q: query, limit: '8' });
  if (cursor && !reset) params.set('cursor', cursor);
  try {
    const response = await fetch(`/api/feed?${params}`, { headers: { authorization: `Bearer ${token}` } });
    const data = await response.json();
    if (thisRequest !== requestId) return;
    if (reset) board.replaceChildren();
    for (const post of data.items) board.append(drawPost(post));
    cursor = data.nextCursor;
    more.hidden = !cursor;
    status.textContent = `${board.children.length} discussions`;
  } catch {
    if (thisRequest === requestId) status.textContent = 'Could not load discussions';
  }
}

search.addEventListener('input', () => { query = search.value; cursor = null; fetchPage(true); });
more.addEventListener('click', () => fetchPage(false));
fetchPage(true);
