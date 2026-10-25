const token = document.querySelector('meta[name="demo-token"]').content;
const board = document.getElementById('board');
const search = document.getElementById('search');
const status = document.getElementById('status');
const more = document.getElementById('more');
let cursor = null;
let query = '';
let requestSerial = 0;

function drawPost(post) {
  const card = document.createElement('article');
  card.className = 'card';
  card.dataset.id = post.id;
  const heading = document.createElement('h2');
  heading.textContent = post.title;
  const summary = document.createElement('p');
  summary.textContent = post.summary;
  card.append(heading, summary);
  const button = document.createElement('button');
  button.className = 'bookmark';
  button.type = 'button';
  const updateButton = () => {
    button.textContent = post.saved ? '★' : '☆';
    button.setAttribute('aria-pressed', String(post.saved));
    button.setAttribute('aria-label', post.saved ? 'Remove saved post' : 'Save post');
  };
  updateButton();
  button.addEventListener('click', async () => {
    if (button.disabled) return;
    const previousSaved = post.saved;
    const previousVersion = post.version;
    post.saved = !post.saved;
    updateButton();
    button.disabled = true;
    try {
      const response = await fetch(`/api/bookmarks/${encodeURIComponent(post.id)}`, {
        method: 'PUT', headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json', 'if-match': `"${previousVersion}"` },
        body: JSON.stringify({ saved: post.saved }),
      });
      if (!response.ok) throw new Error('bookmark rejected');
      const body = await response.json();
      post.version = body.version;
    } catch {
      post.saved = previousSaved;
      post.version = previousVersion;
      status.textContent = 'Could not save post';
      updateButton();
    } finally { button.disabled = false; }
  });
  card.append(button);
  return card;
}

async function fetchPage(reset) {
  const serial = ++requestSerial;
  const requestedQuery = query;
  status.textContent = 'Loading discussions…';
  const params = new URLSearchParams({ q: query, limit: '8' });
  if (cursor && !reset) params.set('cursor', cursor);
  try {
    const response = await fetch(`/api/feed?${params}`, { headers: { authorization: `Bearer ${token}` } });
    if (!response.ok) throw new Error('feed rejected');
    const data = await response.json();
    if (serial !== requestSerial || requestedQuery !== query) return;
    if (reset) board.replaceChildren();
    for (const post of data.items) board.append(drawPost(post));
    cursor = data.nextCursor;
    more.hidden = !cursor;
    status.textContent = `${board.children.length} discussions`;
  } catch {
    if (serial === requestSerial) status.textContent = 'Could not load discussions';
  }
}

search.addEventListener('input', () => {
  query = search.value;
  cursor = null;
  fetchPage(true);
});
more.addEventListener('click', () => fetchPage(false));
fetchPage(true);
