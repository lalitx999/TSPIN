const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const filename = path.resolve(__dirname, '../src/lib/patient-auth-response.ts');
const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const loaded = new Module(filename, module);
loaded._compile(compiled, filename);
const { readPatientTokens, patientAuthEndpoint } = loaded.exports;

test("auth URL accepts origin or api suffix without duplicate api segments", () => {
  for (const base of ["https://example.test", "https://example.test/", "https://example.test/api", "https://example.test/api/"]) {
    for (const action of ["login", "register"]) {
      assert.equal(patientAuthEndpoint(base, action), `https://example.test/api/auth/${action}/`);
    }
  }
});

test('accepts complete token pair without returning other patient data', () => {
  assert.deepEqual(readPatientTokens({ tokens: { access: 'synthetic-access', refresh: 'synthetic-refresh' }, patient: { hn: 'private' } }),
    { access: 'synthetic-access', refresh: 'synthetic-refresh' });
});

test('rejects malformed or incomplete success before any credential can be stored', () => {
  for (const value of [null, [], {}, '<html>error</html>', { tokens: null },
    { tokens: { access: 'synthetic-access' } }, { tokens: { access: 123, refresh: 'r' } },
    { tokens: { access: ' ', refresh: 'r' } }, { tokens: { access: 'a', refresh: '' } }]) {
    assert.throws(() => readPatientTokens(value));
  }
});

// Source guards, not browser E2E: keep retired identity assertions out of these forms.
test('registration no longer carries legacy identity assertions or auto-close timers', () => {
  const source = fs.readFileSync(path.resolve(__dirname, '../src/app/patient/register/page.tsx'), 'utf8');
  for (const forbidden of ['line_user_id', 'existing_doc_id', 'is_activation_mode', 'setTimeout', 'JSON.parse']) {
    assert.equal(source.includes(forbidden), false, forbidden);
  }
  assert.ok(source.includes('href="/liff/identity"'));
  assert.ok(source.includes('readPatientTokens(data)'));
});

test('login has no name-phone activation request or patient prefill storage', () => {
  const source = fs.readFileSync(path.resolve(__dirname, '../src/app/patient/login/page.tsx'), 'utf8');
  assert.equal(source.includes('/api/auth/activate/'), false);
  assert.equal(source.includes('sessionStorage.setItem'), false);
  assert.ok(source.includes('readPatientTokens(data)'));
});
