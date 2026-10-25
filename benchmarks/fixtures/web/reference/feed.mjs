function escapeText(input) {
  return String(input).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
export function renderPost(post) {
  return '<article class="post"><h2>' + escapeText(post.title) + '</h2><button class="save" type="button" aria-label="Save post"><svg aria-hidden="true"></svg></button></article>';
}
