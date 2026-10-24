const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const filename = path.resolve(__dirname, '../src/lib/review-session-guard.ts');
const loaded = new Module(filename, module);
loaded._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText, filename);
const { createReviewSessionGuard } = loaded.exports;
test('old response is rejected after logout and after returning to original account', () => {
  const guard = createReviewSessionGuard();
  const original = guard.capture();
  guard.assertCurrent(original);
  guard.invalidate();
  guard.invalidate();
  assert.throws(() => guard.assertCurrent(original));
  assert.equal(guard.isCurrent(original), false);
  guard.assertCurrent(guard.capture());
});
test('late async completion cannot commit into a new session', async () => {
  const guard = createReviewSessionGuard();
  let resolve;
  const response = new Promise(done => { resolve = done; });
  const captured = guard.capture();
  let committed = false;
  const work = (async () => { await response; guard.assertCurrent(captured); committed = true; })();
  guard.invalidate();
  resolve();
  await assert.rejects(work);
  assert.equal(committed, false);
});
