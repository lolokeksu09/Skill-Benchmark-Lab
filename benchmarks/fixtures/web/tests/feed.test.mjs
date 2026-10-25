import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const variant = process.env.FIXTURE_VARIANT ?? 'baseline';
if (!['baseline', 'reference', 'candidate-qwen3-control-001'].includes(variant)) throw new Error('Unknown variant: ' + variant);
const { renderPost } = await import('../' + variant + '/feed.mjs');
const css = readFileSync(new URL('../' + variant + '/feed.css', import.meta.url), 'utf8');

test('escapes user-controlled title markup', () => {
  const result = renderPost({ title: '<img src=x onerror=alert(1)>' });
  assert.ok(result.includes('&lt;img src=x onerror=alert(1)&gt;'));
  assert.ok(!result.includes('<img src=x onerror='));
});

test('icon-only save button has an accessible name', () => {
  const result = renderPost({ title: 'Safe title' });
  assert.match(result, /<button[^>]+aria-label="Save post"/);
});

test('feed width is responsive rather than fixed to desktop pixels', () => {
  assert.match(css, /\.feed\s*\{[^}]*max-width\s*:\s*100%/s);
});
