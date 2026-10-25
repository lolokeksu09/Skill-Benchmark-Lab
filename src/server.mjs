import { createServer as httpCreateServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';
import { createEngine, DEMO_TOKENS } from './engine.mjs';

const folder = resolve(dirname(fileURLToPath(import.meta.url)), '..', 'web');
const staticRoutes = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/app.mjs', ['app.mjs', 'text/javascript; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']],
]);

function json(res, status, body, extra = {}) {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', ...extra });
  res.end(JSON.stringify(body));
}

async function readJson(req) {
  let text = '';
  for await (const chunk of req) text += chunk;
  try { return { ok: true, value: JSON.parse(text) }; }
  catch { return { ok: false, value: undefined }; }
}

export async function startServer({ port = 0, engine = createEngine() } = {}) {
  const server = httpCreateServer(async (req, res) => {
    const url = new URL(req.url, 'http://localhost');
    const route = staticRoutes.get(url.pathname);
    if (req.method === 'GET' && route) {
      const [file, type] = route;
      try {
        res.writeHead(200, { 'content-type': type, 'cache-control': 'no-store' });
        res.end(await readFile(resolve(folder, file)));
      } catch { json(res, 500, { error: 'static failure' }); }
      return;
    }
    const token = /^Bearer (.+)$/.exec(req.headers.authorization ?? '')?.[1];
    const viewer = DEMO_TOKENS[token];
    if (req.method === 'GET' && url.pathname === '/api/feed') {
      const result = engine.feed(viewer, {
        q: url.searchParams.get('q') ?? '',
        limit: url.searchParams.get('limit') ?? '8',
        cursor: url.searchParams.get('cursor') ?? '',
      });
      json(res, result.status, result.body, result.headers);
      return;
    }
    if (req.method === 'PUT' && /^\/api\/bookmarks\/[^/]+$/.test(url.pathname)) {
      let id;
      try { id = decodeURIComponent(url.pathname.split('/').at(-1)); }
      catch { json(res, 400, { error: 'invalid bookmark id' }); return; }
      const parsed = await readJson(req);
      const result = parsed.ok
        ? engine.bookmark(viewer, id, parsed.value, req.headers['if-match'])
        : { status: 400, body: { error: 'invalid JSON' } };
      json(res, result.status, result.body, result.headers);
      return;
    }
    json(res, 404, { error: 'not found' });
  });
  await new Promise(resolveListen => server.listen(port, '127.0.0.1', resolveListen));
  const address = server.address();
  return {
    url: `http://127.0.0.1:${address.port}`,
    close: () => new Promise((resolveClose, rejectClose) => server.close(err => err ? rejectClose(err) : resolveClose())),
  };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT || 3030);
  const app = await startServer({ port });
  console.log(`Benchmark local server: ${app.url}`);
}
