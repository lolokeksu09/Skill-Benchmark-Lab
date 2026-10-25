/** Produce HTML-safe text for text nodes and quoted attributes. */
export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[character]));
}

/** Return a ready-to-insert post card. All post fields must be treated as untrusted. */
export function renderCard(post, savedIds = new Set()) {
  const postId = String(post.id);
  const saved = [...savedIds].some(id => String(id) === postId);
  const label = saved ? 'Remove saved post' : 'Save post';
  return '<article class="card">'
    + '<h2>' + escapeHtml(post.title) + '</h2>'
    + '<p class="summary">' + escapeHtml(post.summary) + '</p>'
    + '<button class="bookmark" type="button" data-post-id="' + escapeHtml(postId) + '" aria-label="' + label + '" aria-pressed="' + saved + '">'
    + '<svg aria-hidden="true"></svg></button>'
    + '</article>';
}

/** Page numbers are one-based. Invalid page and pageSize values return []. */
export function paginate(posts, page = 1, pageSize = 10) {
  if (!Number.isInteger(page) || !Number.isInteger(pageSize) || page <= 0 || pageSize <= 0) return [];
  const start = (page - 1) * pageSize;
  return posts.slice(start, start + pageSize);
}

/** Return the next saved-ID set, leaving the input set untouched. */
export function toggleBookmark(savedIds, id) {
  const key = String(id);
  const next = new Set([...savedIds].map(savedId => String(savedId)));
  if (next.has(key)) next.delete(key);
  else next.add(key);
  return next;
}
