const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const filename = path.resolve(__dirname, '../src/lib/review-history-response.ts');
const loaded = new Module(filename, module);
loaded._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText, filename);
const { readReviewHistory } = loaded.exports;
const hash = 'a'.repeat(64);
const row = id => ({ id, actor_id: 1, created_at: '2026-10-19T00:00:00Z', decision: 'REQUEST_CHANGES', reason: 'synthetic', artifact_hash: hash });
const page = results => ({ results, artifact_hash: hash, send_allowed: false, clinical_use_authorized: false, next_before_id: null });
test('accepts an empty history and ordered matching history', () => {
  assert.equal(readReviewHistory(page([]), hash).results.length, 0);
  assert.deepEqual(readReviewHistory(page([row(2), row(1)]), hash).results, [row(2), row(1)]);
});
test('rejects malformed, wrong artifact and approval-bearing payloads', () => {
  for (const raw of [null, '<html>error</html>', {}, { ...page([]), results: {} },
    { ...page([]), artifact_hash: 'b'.repeat(64) }, { ...page([]), send_allowed: true },
    page([{ ...row(1), artifact_hash: 'wrong' }]), page([{ ...row(1), decision: 'APPROVE' }]),
    page([{ ...row(1), created_at: 'invalid' }])]) assert.throws(() => readReviewHistory(raw, hash));
});
test('rejects duplicate, unordered, overlapping or inconsistent pagination', () => {
  for (const rows of [[row(1), row(1)], [row(1), row(2)]]) assert.throws(() => readReviewHistory(page(rows), hash));
  assert.throws(() => readReviewHistory(page([row(3)]), hash, 3));
  assert.throws(() => readReviewHistory({ ...page([row(1)]), next_before_id: 1 }, hash));
  const rows = Array.from({ length: 50 }, (_, i) => row(51 - i));
  assert.equal(readReviewHistory({ ...page(rows), next_before_id: 2 }, hash).next_before_id, 2);
  assert.equal(readReviewHistory(page([row(1)]), hash, 2).results[0].id, 1);
});
