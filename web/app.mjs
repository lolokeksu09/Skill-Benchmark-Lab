const token = document.querySelector('meta[name="demo-token"]').content;
const board = document.getElementById('board');
const search = document.getElementById('search');
const status = document.getElementById('status');
const more = document.getElementById('more');
let cursor = null;
let query = '';
let searchGeneration = 0;
let feedController = null;
let loading = false;

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
  button.textContent = post.saved ? '★' : '☆';
  const updateButton = () => {
    button.setAttribute('aria-pressed', String(post.saved));
    button.setAttribute('aria-label', post.saved ? 'Remove saved post' : 'Save post');
    button.textContent = post.saved ? '★' : '☆';
  };
  updateButton();
  button.addEventListener('click', async () => {
    if (button.disabled) return;
    const previous = { saved: post.saved, version: post.version };
    post.saved = !post.saved;
    updateButton();
    button.disabled = true;
    let response;
    try {
      response = await fetch(`/api/bookmarks/${encodeURIComponent(post.id)}`, {
        method: 'PUT',
        headers: {
          authorization: `Bearer ${token}`,
          'content-type': 'application/json',
          'if-match': `"${previous.version}"`,
        },
        body: JSON.stringify({ saved: post.saved }),
      });
      if (!response.ok) throw new Error('bookmark rejected');
      const body = await response.json();
      post.version = body.version;
    } catch {
      post.saved = previous.saved;
      post.version = previous.version;
      updateButton();
      status.textContent = 'Could not save post';
    } finally { button.disabled = false; }
  });
  card.append(button);
  return card;
}

async function fetchPage(reset) {
  if (loading && !reset) return;
  const generation = reset ? ++searchGeneration : searchGeneration;
  if (feedController) feedController.abort();
  feedController = new AbortController();
  loading = true;
  status.textContent = 'Loading discussions…';
  const params = new URLSearchParams({ q: query, limit: '8' });
  if (cursor && !reset) params.set('cursor', cursor);
  try {
    const response = await fetch(`/api/feed?${params}`, { headers: { authorization: `Bearer ${token}` }, signal: feedController.signal });
    if (!response.ok) throw new Error('feed rejected');
    const data = await response.json();
    if (generation !== searchGeneration) return;
    if (reset) board.replaceChildren();
    for (const post of data.items) board.append(drawPost(post));
    cursor = data.nextCursor;
    more.hidden = !cursor;
    status.textContent = `${board.children.length} discussions`;
  } catch (error) {
    if (error.name !== 'AbortError' && generation === searchGeneration) status.textContent = 'Could not load discussions';
  } finally { if (generation === searchGeneration) loading = false; }
}

search.addEventListener('input', () => {
  query = search.value;
  cursor = null;
  fetchPage(true);
});
more.addEventListener('click', () => fetchPage(false));
fetchPage(true);
