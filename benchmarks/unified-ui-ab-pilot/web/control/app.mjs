const token = document.querySelector('meta[name="demo-token"]').content;
const board = document.getElementById('board');
const search = document.getElementById('search');
const status = document.getElementById('status');
const more = document.getElementById('more');
let cursor = null;
let query = '';

function drawPost(post) {
  const card = document.createElement('article');
  card.className = 'card';
  card.dataset.id = post.id;
  card.innerHTML = `<h2>${post.title}</h2><p>${post.summary}</p>`;
  const button = document.createElement('button');
  button.className = 'bookmark';
  button.type = 'button';
  button.textContent = '☆';
  button.setAttribute('aria-pressed', String(post.saved));
  button.addEventListener('click', async () => {
    post.saved = !post.saved;
    button.setAttribute('aria-pressed', String(post.saved));
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
    }
  });
  card.append(button);
  return card;
}

async function fetchPage(reset) {
  status.textContent = 'Loading discussions…';
  const params = new URLSearchParams({ q: query, limit: '8' });
  if (cursor && !reset) params.set('cursor', cursor);
  const response = await fetch(`/api/feed?${params}`, { headers: { authorization: `Bearer ${token}` } });
  const data = await response.json();
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
