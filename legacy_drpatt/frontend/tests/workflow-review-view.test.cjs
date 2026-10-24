const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const ts = require('typescript');
const filename = path.resolve(__dirname, '../src/lib/workflow-review-view.ts');
const loaded = new Module(filename, module);
loaded._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText, filename);
const { workflowReviewView } = loaded.exports;

test('missing workflow is not fabricated and malformed trace is explicit', () => {
  assert.equal(workflowReviewView({ packet: {} }), null);
  const view = workflowReviewView({ workflow: { state: 'BLOCKED', trace: {} } });
  assert.equal(view.malformedTrace, true);
  assert.equal(view.steps.length, 0);
});
test('preserves order, revisions, issues and missing handler without invented steps', () => {
  const payload = { workflow: { state: 'HUMAN_REVIEW_REQUIRED', rounds_used: 2,
    reason: 'HANDLER_NOT_CONFIGURED:A07', trace: [
      { role: 'A14', round: 1, decision: 'FAIL', output: { issues: [{ code: 'FACT_MISMATCH' }] } },
      { role: 'A01', round: 2, decision: 'PASS' },
      { role: 'A07', round: 2, decision: 'DEFER', code: 'HANDLER_NOT_CONFIGURED' },
    ] } };
  const before = JSON.stringify(payload);
  const view = workflowReviewView(payload);
  assert.deepEqual(view.steps.map(s => s.role), ['A14', 'A01', 'A07']);
  assert.match(view.steps[0].issues[0], /FACT_MISMATCH/);
  assert.equal(view.steps[2].issues[0], 'HANDLER_NOT_CONFIGURED');
  assert.equal(view.steps[2].finished, 'ไม่ระบุ');
  assert.equal(JSON.stringify(payload), before);
});
test('safety precheck remains visible with zero workflow rounds', () => {
  const view = workflowReviewView({ workflow: { rounds_used: 0, state: 'ESCALATED',
    trace: [{ stage: 'SAFETY_PRECHECK', decision: 'ESCALATE', safety: { alerts: ['synthetic-alert'] } }] } });
  assert.equal(view.rounds, '0');
  assert.equal(view.steps[0].role, 'SAFETY_PRECHECK');
  assert.match(view.steps[0].safety, /synthetic-alert/);
});
test('unknown decisions and text are preserved rather than converted into PASS', () => {
  const view = workflowReviewView({ workflow: { trace: [{ decision: 'UNKNOWN', code: '<script>test</script>' }, null] } });
  assert.equal(view.steps[0].decision, 'UNKNOWN');
  assert.equal(view.steps[0].issues[0], '<script>test</script>');
  assert.equal(view.steps[1].decision, 'ไม่ระบุ');
});
