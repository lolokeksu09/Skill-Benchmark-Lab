import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { escapeHtml, renderCard, paginate, toggleBookmark } from '../src/board.mjs';

const css = readFileSync(new URL('../src/board.css', import.meta.url), 'utf8');

test('untrusted title and summary are HTML-escaped', () => {
  const text = "<img src=x onerror=\"alert('x')\"> & ok";
  assert.equal(escapeHtml(text), '&lt;img src=x onerror=&quot;alert(&#39;x&#39;)&quot;&gt; &amp; ok');
  const html = renderCard({ id: 'p1', title: '<script>bad</script>', summary: '<b>text</b> & more' });
  assert.ok(html.includes('&lt;script&gt;bad&lt;/script&gt;'));
  assert.ok(html.includes('&lt;b&gt;text&lt;/b&gt; &amp; more'));
  assert.ok(!html.includes('<script>'));
});

test('untrusted post ID cannot break the quoted data attribute', () => {
  const html = renderCard({ id: 'x" autofocus="true', title: 'ok', summary: 'ok' });
  assert.ok(html.includes('data-post-id="x&quot; autofocus=&quot;true"'));
  assert.ok(!html.includes('data-post-id="x" autofocus='));
});

test('bookmark control has a changing accessible name and pressed state', () => {
  const post = { id: 17, title: 'Test', summary: 'Text' };
  const unsaved = renderCard(post);
  const saved = renderCard(post, new Set(['17']));
  assert.match(unsaved, /<button[^>]+aria-label="Save post"/);
  assert.match(unsaved, /aria-pressed="false"/);
  assert.match(saved, /<button[^>]+aria-label="Remove saved post"/);
  assert.match(saved, /aria-pressed="true"/);
});

test('pagination is one-based and returns the correct next page', () => {
  const items = Array.from({length: 11}, (_, id) => ({id}));
  assert.deepEqual(paginate(items, 1, 4).map(x => x.id), [0, 1, 2, 3]);
  assert.deepEqual(paginate(items, 2, 4).map(x => x.id), [4, 5, 6, 7]);
  assert.deepEqual(paginate(items, 3, 4).map(x => x.id), [8, 9, 10]);
});

test('invalid pagination does not return arbitrary data', () => {
  const input = [1, 2, 3];
  for (const [p, s] of [[0, 2], [-1, 1], [1.5, 2], [1, 0], [1, -1]]) {
    assert.deepEqual(paginate(input, p, s), []);
  }
});

test('bookmark toggling returns new state without mutating previous snapshots', () => {
  const before = new Set(['1']);
  const after = toggleBookmark(before, 2);
  assert.notStrictEqual(after, before);
  assert.deepEqual([...before], ['1']);
  assert.deepEqual([...after].sort(), ['1', '2']);
  const removed = toggleBookmark(after, '2');
  assert.deepEqual([...removed], ['1']);
  assert.deepEqual([...after].sort(), ['1', '2']);
});

test('board CSS is responsive without horizontal overflow', () => {
  assert.match(css, /\.board\s*\{[^}]*\bwidth\s*:\s*100%\s*;/s);
  assert.match(css, /\.board\s*\{[^}]*\bmax-width\s*:\s*960px\s*;/s);
  assert.match(css, /\.board\s*\{[^}]*\bbox-sizing\s*:\s*border-box\s*;/s);
});

test('keyboard users can see focus on the bookmark control', () => {
  assert.match(css, /\.bookmark:focus-visible\s*\{[^}]*\boutline\s*:/s);
});
