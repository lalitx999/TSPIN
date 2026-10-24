const { test, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const filename = path.resolve(__dirname, '../src/app/api/liff/identity/route.ts');
const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const loaded = new Module(filename, module);
loaded.filename = filename;
loaded.paths = Module._nodeModulePaths(path.dirname(filename));
loaded._compile(compiled, filename);
const { POST } = loaded.exports;
const originalFetch = global.fetch;
const originalEnv = { ...process.env };
afterEach(() => {
  global.fetch = originalFetch;
  for (const key of ['BACKEND_API_URL', 'NEXT_PUBLIC_API_URL']) {
    if (originalEnv[key] === undefined) delete process.env[key];
    else process.env[key] = originalEnv[key];
  }
});
function request(body = { password: 'synthetic-password', access_token: 'synthetic-line-token' }, auth = 'Bearer synthetic-clinic-token') {
  return new Request('https://frontend.example.test/api/liff/identity', {
    method: 'POST', headers: { 'Content-Type': 'application/json', ...(auth ? { Authorization: auth } : {}) },
    body: JSON.stringify(body),
  });
}
test('forwards only credentials to verified endpoint with normalized base and no redirects/cache', async () => {
  for (const base of ['https://backend.example.test', 'https://backend.example.test/api/']) {
    process.env.BACKEND_API_URL = base;
    global.fetch = async (url, options) => {
      assert.equal(String(url), 'https://backend.example.test/api/line/verified-link/');
      assert.equal(options.headers.Authorization, 'Bearer synthetic-clinic-token');
      assert.deepEqual(JSON.parse(options.body), { password: 'synthetic-password', access_token: 'synthetic-line-token' });
      assert.equal(options.redirect, 'error');
      assert.equal(options.cache, 'no-store');
      return Response.json({ success: true, status: 'LINKED', patientId: 123, unexpected: 'private' });
    };
    const response = await POST(request());
    assert.equal(response.status, 200);
    assert.equal(response.headers.get('cache-control'), 'no-store');
    assert.deepEqual(await response.json(), { success: true, status: 'LINKED' });
  }
});
test('missing authentication never calls backend', async () => {
  global.fetch = () => { throw new Error('Network forbidden'); };
  assert.equal((await POST(request(undefined, ''))).status, 401);
});
test('legacy fields and extra patient identity are rejected', async () => {
  for (const body of [{ phone: '0000000000', lineUserId: 'untrusted' },
    { password: 'test', access_token: 'test', patient_id: 123 }, null, []]) {
    assert.equal((await POST(request(body))).status, 400);
  }
});
test('missing or insecure remote configuration fails closed', async () => {
  delete process.env.BACKEND_API_URL;
  delete process.env.NEXT_PUBLIC_API_URL;
  assert.equal((await POST(request())).status, 503);
  process.env.BACKEND_API_URL = 'http://backend.example.test';
  assert.equal((await POST(request())).status, 503);
});
test('backend conflict is mapped without returning private fields', async () => {
  process.env.BACKEND_API_URL = 'https://backend.example.test';
  global.fetch = async () => Response.json({ error: 'LINE_LINK_CONFLICT', patient: 'private' }, { status: 409 });
  assert.deepEqual(await (await POST(request())).json(), { error: 'LINE_LINK_CONFLICT' });
});
test('HTML errors and transport exceptions never leak response bodies or token URLs', async () => {
  process.env.BACKEND_API_URL = 'https://backend.example.test';
  global.fetch = async () => new Response('<html>private exception</html>', { status: 500 });
  assert.deepEqual(await (await POST(request())).json(), { error: 'LINK_SERVICE_UNAVAILABLE' });
  global.fetch = async () => { throw new Error('secret-token'); };
  assert.deepEqual(await (await POST(request())).json(), { error: 'LINK_SERVICE_UNAVAILABLE' });
});
test('malformed success is not reported as linked', async () => {
  process.env.BACKEND_API_URL = 'https://backend.example.test';
  global.fetch = async () => Response.json({ success: true });
  assert.equal((await POST(request())).status, 502);
});
