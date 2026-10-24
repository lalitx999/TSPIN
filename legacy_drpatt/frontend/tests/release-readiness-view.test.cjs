const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const filename = path.resolve(__dirname, '../src/lib/release-readiness-view.ts');
const loaded = new Module(filename, module);
loaded._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText, filename);
const { releaseReadinessView } = loaded.exports;
const valid = () => ({ artifact_id: 'test-artifact', state: 'BLOCKED', diagnostic_only: true,
  send_allowed: false, clinical_use_authorized: false, input_is_current: true,
  artifact_manifest_hash: 'a'.repeat(64), current_manifest_hash: 'a'.repeat(64),
  issues: [{ code: 'PRE_SEND_SAFETY_RECHECK_REQUIRED' }] });
test('shows diagnostic reasons with no authority even when inputs are current', () => {
  const result = releaseReadinessView(valid(), 'test-artifact');
  assert.equal(result.current, true);
  assert.match(result.issues[0].message, /ตรวจความปลอดภัย/);
  assert.equal(result.send_allowed, undefined);
});
test('rejects wrong artifact, invented approval, incomplete or contradictory responses', () => {
  for (const change of [{ artifact_id: 'other' }, { send_allowed: true }, { state: 'READY' },
    { clinical_use_authorized: true }, { diagnostic_only: false }, { issues: [] },
    { issues: [null] }, { issues: [{ code: '' }] }, { current_manifest_hash: null },
    { current_manifest_hash: 'b'.repeat(64) }, { input_is_current: 'true' }]) {
    assert.throws(() => releaseReadinessView({ ...valid(), ...change }, 'test-artifact'));
  }
});
test('unverified freshness and unfamiliar reason remain blocked diagnostics', () => {
  const result = releaseReadinessView({ ...valid(), input_is_current: false,
    current_manifest_hash: null, issues: [{ code: 'NEW_BACKEND_BLOCKER' }] }, 'test-artifact');
  assert.equal(result.current, false);
  assert.equal(result.issues[0].code, 'NEW_BACKEND_BLOCKER');
  assert.match(result.issues[0].message, /ตรวจสอบเพิ่มเติม/);
});
