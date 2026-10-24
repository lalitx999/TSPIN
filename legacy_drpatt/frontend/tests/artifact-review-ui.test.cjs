const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.resolve(__dirname, '../src/app/doctor/artifact-review/page.tsx'), 'utf8');

// Source guards only. Browser interaction and server authorization need separate tests.
test('review page uses staff credentials without patient-token fallback', () => {
  assert.ok(source.includes('localStorage.getItem("doctor_access_token")'));
  assert.equal(source.includes('patient_access_token'), false);
  assert.ok(source.includes('cache: "no-store"'));
  assert.ok(source.includes('redirect: "error"'));
});
test('review form binds to loaded artifact and requires confirmation', () => {
  assert.ok(source.includes('expected_artifact_hash: opened.artifact.integrity_hash'));
  assert.ok(source.includes('!confirmed || !reason.trim() || mustReload'));
  assert.ok(source.includes('setMustReload(true)'));
  assert.equal(source.includes('dangerouslySetInnerHTML'), false);
});
test('only feedback decisions are offered, not clinical approval', () => {
  for (const value of ['REVIEWED_NOT_APPROVED', 'REQUEST_CHANGES', 'REJECT']) assert.ok(source.includes(value));
  assert.equal(source.includes('PHYSICIAN_APPROVED'), false);
  assert.equal(source.includes('PATIENT_RELEASED'), false);
});
