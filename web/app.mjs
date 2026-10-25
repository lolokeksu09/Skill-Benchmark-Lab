const token = document.querySelector('meta[name="demo-token"]').content;
const board = document.getElementById('board');
const search = document.getElementById('search');
const status = document.getElementById('status');
const more = document.getElementById('more');
let cursor = null;
let query = '';
let requestSerial = 0;
let activeRequest;

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
  button.textContent = '☆';
  button.setAttribute('aria-label', post.saved ? 'Remove saved post' : 'Save post');
  button.setAttribute('aria-pressed', String(post.saved));
  button.addEventListener('click', async () => {
    const previous = post.saved;
    post.saved = !previous;
    button.setAttribute('aria-pressed', String(post.saved));
    button.setAttribute('aria-label', post.saved ? 'Remove saved post' : 'Save post');
    button.disabled = true;
    try {
    const response = await fetch(`/api/bookmarks/${encodeURIComponent(post.id)}`, {
      method: 'PUT',
      headers: {
        authorization: `Bearer ${token}`,
        'content-type': 'application/json',
        'if-match': `"${post.version}"`,
      },
      body: JSON.stringify({ saved: post.saved }),
    });
    if (response.ok) {
      const body = await response.json();
      post.version = body.version;
    } else throw new Error('save failed');
    } catch {
      post.saved = previous;
      button.setAttribute('aria-pressed', String(previous));
      button.setAttribute('aria-label', previous ? 'Remove saved post' : 'Save post');
      status.textContent = 'Could not save post';
    } finally { button.disabled = false; }
  });
  card.append(button);
  return card;
}

async function fetchPage(reset) {
  const serial = ++requestSerial;
  if (activeRequest) activeRequest.abort();
  activeRequest = new AbortController();
  status.textContent = 'Loading discussions…';
  const params = new URLSearchParams({ q: query, limit: '8' });
  if (cursor && !reset) params.set('cursor', cursor);
  let response, data;
  try {
    response = await fetch(`/api/feed?${params}`, { headers: { authorization: `Bearer ${token}` }, signal: activeRequest.signal });
    data = await response.json();
    if (!response.ok) throw new Error('feed failed');
  } catch (error) { if (error.name !== 'AbortError' && serial === requestSerial) status.textContent = 'Could not load discussions'; return; }
  if (serial !== requestSerial) return;
  if (reset) board.replaceChildren();
  for (const post of data.items) board.append(drawPost(post));
  cursor = data.nextCursor;
  more.hidden = !cursor;
  status.textContent = `${board.children.length} discussions`;
}

search.addEventListener('input', () => {
  query = search.value;
  cursor = null;
  fetchPage(true);
});
more.addEventListener('click', () => fetchPage(false));
fetchPage(true);
