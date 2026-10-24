// Real Chromium UI tests against a LOCAL Next dev server; every API is synthetic.
// NODE_PATH may point to an existing Playwright installation; no package downloads.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const origin = process.env.REVIEW_TEST_ORIGIN || 'http://127.0.0.1:3117';
if (!['127.0.0.1', 'localhost'].includes(new URL(origin).hostname)) throw new Error('Local test origin required');
const artifactId = '11111111-1111-4111-8111-111111111111';
const hash = 'a'.repeat(64);

test('artifact review browser acceptance with synthetic API', { timeout: 180000 }, async t => {
  const browser = await chromium.launch({ headless: true,
    ...(process.env.REVIEW_TEST_CHROME ? { executablePath: process.env.REVIEW_TEST_CHROME } : {}) });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, serviceWorkers: 'block' });
  let events = [], loseResponse = false, wrongHash = false, historyDenied = false, releaseSearch, searchStarted;
  const errors = [];
  await context.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url());
    if (url.origin === origin) return route.continue();
    if (url.origin !== 'http://127.0.0.1:8912') return route.abort();
    const reply = (body, status = 200) => route.fulfill({ status, contentType: 'application/json',
      headers: { 'Access-Control-Allow-Origin': origin, 'Access-Control-Allow-Headers': 'authorization,content-type',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS', 'Cache-Control': 'no-store' }, body: JSON.stringify(body) });
    if (request.method() === 'OPTIONS') return reply({});
    if (url.pathname === '/api/auth/doctor/me/') return reply({ id: 7, name: 'Synthetic Reviewer', first_name: 'Synthetic', last_name: 'Reviewer', email: 'synthetic@example.test' });
    if (url.pathname === '/api/patients/artifact-review-patients/') {
      if (searchStarted) { searchStarted(); await new Promise(resolve => { releaseSearch = resolve; }); }
      return reply({ results: [{ id: 42, hn: 'SYNTHETIC-HN', name: 'Synthetic Patient' }], truncated: false });
    }
    if (url.pathname === '/api/patients/42/artifact-review-list/') return reply({ results: [{ id: artifactId, kind: 'EVIDENCE_DRAFT', created_at: '2026-10-19T00:00:00Z' }], next_before_id: null });
    const path = `/api/patients/42/agentic-artifacts/${artifactId}/`;
    if (url.pathname === path) return reply({ artifact_id: artifactId, integrity_hash: hash, kind: 'EVIDENCE_DRAFT',
      payload: { manifest: { identity: { patient_id: '42' } }, packet: { editions: { PHYSICIAN: { facts: [
        { evidence_id: 'synthetic-evidence', concept_id: 'synthetic-concept', value: 0, unit: 'unit',
          source_id: 'synthetic-lab', source_type: 'LAB_MEASURED', source_timestamp: '2026-10-19T00:00:00Z', verification: 'VERIFIED', version: 1 },
      ] } } } } });
    if (url.pathname === `${path}release-readiness/`) return reply({ artifact_id: artifactId, state: 'BLOCKED',
      diagnostic_only: true, send_allowed: false, clinical_use_authorized: false, input_is_current: true,
      artifact_manifest_hash: hash, current_manifest_hash: hash, issues: [{ code: 'PRE_SEND_SAFETY_RECHECK_REQUIRED' }] });
    if (url.pathname === `${path}reviews/`) {
      if (historyDenied) return reply({ error: 'Expired synthetic session' }, 401);
      if (request.method() === 'GET') return reply({ results: [...events].reverse(), next_before_id: null,
        artifact_hash: wrongHash ? 'b'.repeat(64) : hash, send_allowed: false, clinical_use_authorized: false });
      const body = request.postDataJSON();
      assert.equal(body.expected_artifact_hash, hash);
      assert.match(body.request_id, /^[0-9a-f-]{36}$/);
      assert.equal(body.actor_id, undefined);
      let event = events.find(item => item.request_id === body.request_id);
      const replayed = Boolean(event);
      if (!event) {
        event = { id: events.length + 1, actor_id: 7, created_at: '2026-10-19T00:00:00Z',
          artifact_hash: hash, decision: body.decision, reason: body.reason, request_id: body.request_id };
        events.push(event);
      }
      if (loseResponse) { loseResponse = false; return route.abort(); }
      return reply({ review_event_id: event.id, decision: event.decision, send_allowed: false, clinical_use_authorized: false, replayed }, replayed ? 200 : 201);
    }
    errors.push(`Unexpected synthetic API: ${url.pathname}`);
    return reply({ error: 'UNEXPECTED_TEST_ROUTE' }, 500);
  });
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto(`${origin}/doctor/login`);
    await page.evaluate(() => localStorage.setItem('doctor_access_token', 'synthetic-staff-A'));
    await page.goto(`${origin}/doctor/artifact-review`);
    await page.getByRole('heading', { name: 'ตรวจร่าง Agentic', exact: true }).waitFor();
    const open = async () => {
      await page.getByRole('button', { name: 'เปิดร่างและโหลดประวัติ', exact: true }).click();
      await page.getByLabel('เหตุผล', { exact: true }).waitFor();
    };
    await t.test('search, select exact artifact and render evidence', async () => {
      await page.getByLabel('ค้นหาผู้ป่วยที่มีร่างด้วย HN หรือชื่อ').fill('SYNTHETIC');
      await page.getByRole('button', { name: 'ค้นหา', exact: true }).click();
      await page.getByText('เลือกผู้ป่วยด้านล่าง', { exact: true }).waitFor();
      await page.getByLabel('เลือกผู้ป่วย', { exact: true }).selectOption('42');
      await page.getByLabel('เลือกร่าง (รายการไม่ได้เรียงตามเวลา)').selectOption(artifactId);
      await open();
      assert.match(await page.locator('table').innerText(), /synthetic-concept/);
      assert.match(await page.locator('table').innerText(), /0 \/ unit/);
      assert.equal(await page.getByRole('button', { name: 'บันทึกผลตรวจ (ไม่ใช่อนุมัติ)', exact: true }).isDisabled(), true);
    });
    if (process.env.REVIEW_TEST_FIRST_ONLY) return;
    await t.test('readiness does not unlock clinical delivery', async () => {
      await page.getByRole('button', { name: 'ตรวจเงื่อนไขกับข้อมูลปัจจุบัน' }).click();
      await page.getByText('ยังไม่อนุญาตให้ส่งรายงาน', { exact: true }).waitFor();
      assert.equal(await page.getByRole('button', { name: 'ส่งรายงาน', exact: true }).count(), 0);
    });
    await t.test('lost POST response and retry use same idempotency key', async () => {
      loseResponse = true;
      await page.getByLabel('เหตุผล', { exact: true }).fill('Synthetic review retry');
      await page.getByRole('checkbox').check();
      await page.getByRole('button', { name: 'บันทึกผลตรวจ (ไม่ใช่อนุมัติ)', exact: true }).click();
      await page.getByText(/ยังยืนยันผลบันทึกไม่ได้/).waitFor();
      assert.equal(events.length, 1);
      await open();
      await page.getByLabel('เหตุผล', { exact: true }).fill('Synthetic review retry');
      await page.getByRole('checkbox').check();
      await page.getByRole('button', { name: 'บันทึกผลตรวจ (ไม่ใช่อนุมัติ)', exact: true }).click();
      await page.getByText('บันทึกผลตรวจแล้ว ยังไม่ได้อนุมัติหรือส่งรายงาน', { exact: true }).waitFor();
      assert.equal(events.length, 1);
    });
    await t.test('wrong-snapshot history prevents review form', async () => {
      wrongHash = true;
      await page.getByRole('button', { name: 'เปิดร่างและโหลดประวัติ', exact: true }).click();
      await page.getByText(/ประวัติผลตรวจไม่ครบถ้วนหรือไม่ตรงกับร่าง/).waitFor();
      assert.equal(await page.getByLabel('เหตุผล', { exact: true }).count(), 0);
      wrongHash = false;
      await open();
    });
    await t.test('expired access clears loaded patient and review state', async () => {
      historyDenied = true;
      await page.getByRole('button', { name: 'เปิดร่างและโหลดประวัติ', exact: true }).click();
      await page.getByText(/สิทธิ์หมดอายุหรือถูกระงับ/).waitFor();
      assert.equal(await page.getByLabel('เหตุผล', { exact: true }).count(), 0);
      assert.equal(await page.getByLabel('Patient ID (ระบุเองได้)').inputValue(), '');
      historyDenied = false;
      await page.getByLabel('Patient ID (ระบุเองได้)').fill('42');
      await page.getByLabel('Artifact UUID', { exact: true }).fill(artifactId);
      await open();
    });
    await t.test('mobile layout keeps content within viewport', async () => {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.waitForFunction(() => document.querySelector('.inapp-sidebar').getBoundingClientRect().right <= 1);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1));
      const contentWidth = await page.locator('main.container').evaluate(element => element.getBoundingClientRect().width);
      assert.ok(contentWidth > 300, `Mobile content too narrow: ${contentWidth}`);
      if (process.env.REVIEW_TEST_SCREENSHOT) await page.screenshot({ path: process.env.REVIEW_TEST_SCREENSHOT, fullPage: false });
    });
    const other = await context.newPage();
    await other.goto(`${origin}/doctor/login`);
    await t.test('cross-tab account change clears opened PHI and feedback', async () => {
      await page.getByLabel('เหตุผล', { exact: true }).fill('Unsaved synthetic review');
      await other.evaluate(() => localStorage.setItem('doctor_access_token', 'synthetic-staff-B'));
      await page.getByText(/บัญชีเปลี่ยนหรือออกจากระบบแล้ว/).waitFor();
      assert.equal(await page.locator('table').count(), 0);
      assert.equal(await page.getByLabel('เหตุผล', { exact: true }).count(), 0);
      assert.equal(await page.getByLabel('Patient ID (ระบุเองได้)').inputValue(), '');
    });
    await t.test('late search response cannot repopulate data after logout', async () => {
      const started = new Promise(resolve => { searchStarted = resolve; });
      await page.getByLabel('ค้นหาผู้ป่วยที่มีร่างด้วย HN หรือชื่อ').fill('SYNTHETIC');
      await page.getByRole('button', { name: 'ค้นหา', exact: true }).click();
      await started;
      await other.evaluate(() => localStorage.removeItem('doctor_access_token'));
      await page.getByText(/บัญชีเปลี่ยนหรือออกจากระบบแล้ว/).waitFor();
      const finished = page.waitForResponse(response => response.url().includes('artifact-review-patients'));
      releaseSearch();
      await finished;
      // Flush response body and React work; no fixed sleep required.
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      assert.equal(await page.getByRole('option', { name: /Synthetic Patient/ }).count(), 0);
    });
    assert.deepEqual(errors, []);
  } finally {
    if (errors.length) console.error('Browser errors:', errors);
    if (releaseSearch) releaseSearch();
    await context.close();
    await browser.close();
  }
});
