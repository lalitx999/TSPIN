# Agentic implementation progress — 18 October 2026

เอกสารนี้ติดตามเฉพาะแผน EP0–EP10 ของ Agentic specification ฉบับ 12 October 2026
ไม่ใช้สถานะของ EP ชุดเก่ามาอ้างว่าชุดใหม่นี้เสร็จแล้ว

| EP | สถานะ | งานที่ยังไม่ครบ |
|---|---|---|
| 0 Audit | ตรวจเส้นทาง calculate/persistence และกฎโปรเจกต์บางส่วนแล้ว | inventory และ AT01–30 traceability ทั้งระบบ |
| 1 Canonical evidence | เขียน validator, persistence, service/API และ analysis input preflight พร้อม stale hash check แล้ว | รัน tests, PostgreSQL concurrency, import adapter, UI, persisted analysis/release invalidation |
| 2 Registries | เขียน unit registry, governed metadata lifecycle, bundle validator/API และ unit+bundle input manifest แล้ว ยังไม่ทดสอบ | clinical registry content, source verification, legacy import, revalidation และผลทดสอบจริง |
| 3 Deterministic scoring | เขียน executor, SCORING registry, backend gate, persistent run/history replay และ tests แล้ว ยังไม่ทดสอบ | approved clinical rules, time-window policy, dependency recomputation และ legacy replacement |
| 4 Safety | เขียน policy contract, completeness/freshness/SOC evaluator, preview + persistent snapshot/history/replay API และ tests แล้ว ยังไม่ทดสอบ | clinical policies, interaction connector และ execution/release integration |
| 5 Orchestration | pure controller ผ่าน unit tests; เพิ่ม backend adapters บางบทบาทและ persistent artifact/API แล้ว ยังไม่ทดสอบ integration | adapters ที่ยังขาด, queue/timeouts, independent audits และ integration tests |
| 6 Reports | evidence-only drafts สามฉบับจาก snapshot เดียวผ่าน unit tests; เพิ่ม persistence/API แต่ยังไม่ทดสอบ integration | clinical composition, review/release, UI และ integration tests |
| 7 Approval | เพิ่ม read-only release readiness โดยไม่ใช้ legacy approval แทน artifact binding | licence/auth verification และ signed output version |
| 8 Communication | readiness แสดง consent/recipient/safety ที่ยังขาด แต่ยังไม่อนุญาตส่ง | shared A–D pre-send gates และบังคับใช้ทุกเส้นทางส่ง |
| 9 Audit/Consent | เพิ่ม deterministic scoring snapshot/replay บางส่วนแล้ว ยังไม่ทดสอบ | request/security audit ทุก outcome, agent traces, consent separation และ retention policy |
| 10 Acceptance | ยังไม่เริ่ม | AT01–30 จริง, regression, pilot, rollback |

## ผลตรวจล่าสุด — 18 October 2026

หลังผู้ใช้อนุญาตให้ agent รันทดสอบ: pure unit tests ผ่าน 64 ข้อ (exit 0)
คำสั่งจาก backend:

```sh
python3 -m unittest patients.tests_canonical_state patients.tests_deterministic_scoring patients.tests_safety_contracts patients.tests_agentic_orchestrator patients.tests_evidence_reports -q
```

ผลนี้ครอบคลุม pure logic ของ EP1/3/4/5/6 เท่านั้น ไม่ใช่ service/API/database tests
ข้อความ “ยังไม่ทดสอบ” ในตารางสำหรับ persistence และ services ยังคงเป็นจริง
ไม่มี production migration, deploy หรือ push โดย agent

แก้ regression เพิ่ม: correction เลิกใช้ duplicate aliases ของหลักฐานต้นฉบับด้วย
และข้อมูล CLEAR ที่ยังใช้ยืนยันไม่ได้จะไม่บดบัง alert เดิม
canonical snapshots ใหม่ใช้ v2; safety evaluator ใหม่ใช้ v2 โดย replay v1 ยังใช้ semantics เดิม
รายละเอียด: `AGENTIC_REGRESSION_HARDENING.md`

## ผล integration เพิ่มเติม — 18 October 2026

สถานะ “ยังไม่ทดสอบ” ในตารางข้างบนเป็นสถานะก่อนการรันครั้งนี้:
รันชุด pure + Django service/API ของ canonical evidence, unit/governed registry,
analysis preflight, scoring, safety history และ evidence artifacts รวม 152 tests ผ่าน
จากนั้นเพิ่ม workflow integration อีก 3 ข้อ และรัน artifact suite ทั้ง 11 ข้อผ่าน
รันรวมซ้ำล่าสุดครบ 155 tests ผ่าน (exit 0)
ใช้ project .venv และ SQLite :memory: ไม่ใช้ PostgreSQL หรือข้อมูลจริง
schema/migrations ถูกใช้เฉพาะฐานข้อมูลทดสอบที่ runner สร้างและทำลาย
รายละเอียดและข้อจำกัด: `AGENTIC_ARTIFACT_INTEGRATION.md`

เพิ่ม safety escalation, cross-patient artifact regression และ payload integrity แล้ว
ชุดรวมล่าสุดผ่าน 158 tests (exit 0) บน SQLite :memory:
ขั้นต่อไป: ตรวจ PostgreSQL concurrency และพัฒนา adapters/release gates ที่ยังขาด
ก่อนเชื่อมกับ calculation/release path เดิม ไม่มีการประกาศว่าครบ EP0–10 แล้ว

เพิ่ม release-readiness diagnostics และ 4 regression tests; artifact suite รวม 18 ข้อผ่าน
รันชุดรวมล่าสุด 162 tests ผ่าน (exit 0) บนฐานข้อมูลทดสอบ SQLite :memory:
รายละเอียด `AGENTIC_RELEASE_READINESS.md` — ยังไม่ใช่ระบบอนุมัติหรือ pre-send enforcement

ปิด legacy transition self-attestation bypass (`is_physician_signoff`),
ไม่ใช้ superuser/Physician group แทน licence verification และระงับ approval/release
ผ่าน endpoint นี้จนกว่าจะมี trusted verifier; draft/review ยังใช้ได้
รายละเอียดผลกระทบ `LEGACY_RELEASE_SECURITY.md` — ไม่ได้ revoke release เก่าหรือปิด delivery ทุกเส้นทาง
ชุดรวมล่าสุดรวม legacy approval/PDF gating: 172 tests ผ่านบน SQLite :memory: (exit 0)

เพิ่ม authorization ที่ dossier/saved PDF และระงับ Patient Edition ที่อาศัย release row เดิม
โดยไม่ลบประวัติ รายละเอียดผลกระทบ `CLINICAL_PDF_ACCESS_GATES.md`
ยังต้อง audit JSON/frontend/LINE/export ทุกเส้นทางก่อนถือว่า EP8 ครบ
ชุดรวมล่าสุด 177 tests ผ่านบน SQLite :memory: (exit 0)

ปิด generated_reports/latest_precision_insight ใน PatientSerializer สำหรับ nonclinical/contextless response
และปิดการเขียนอ้อมผ่าน extra_data/top-level aliases; รายละเอียด `PATIENT_REPORT_JSON_VISIBILITY.md`
ยังต้องตรวจ raw response/analysis/biological/LINE/cache เพิ่ม ไม่ถือว่า EP8 ครบ
ชุดรวมล่าสุด 184 tests ผ่านบน SQLite :memory: (exit 0)

เพิ่ม clinical-only raw tspi-analysis และหยุดส่งคะแนนสดจาก LINE dashboard ทั้ง text/postback
รายละเอียด `ANALYSIS_LINE_DELIVERY_GATES.md`; ยังมี webhook signature validation
และ AI intake delivery/identity ที่ต้องแก้ ไม่พร้อม deploy
ชุดรวมล่าสุด 187 tests ผ่านบน SQLite :memory: (exit 0)

แก้ webhook signature bypass แล้ว: ตรวจ raw bytes ก่อน event handler ทุก environment,
missing secret ปฏิเสธ 503; เพิ่ม malformed payload และ unsigned rebinding regressions
ดู `LINE_WEBHOOK_AUTHENTICATION.md` — ยังต้องตรวจ identity linking/replay/AI output gates
ชุดรวมล่าสุด 193 tests ผ่านบน SQLite :memory: (exit 0)

ปิด ID-only webhook binding และ ambiguous binding selection;
ระงับ legacy phone/client-LINE-ID linking endpoints (ไม่ใช่สร้าง verified linking flow เสร็จ)
ดู `LINE_IDENTITY_BINDING_GATES.md` สำหรับผลกระทบและงานค้าง registration/login/token verification
ชุดรวมล่าสุด 198 tests ผ่านบน SQLite :memory: (exit 0)

ปิด registration LINE assertion และ email-based patient fallback; ambiguous account/profile ต้องหยุด
ดู `ACCOUNT_IDENTITY_BINDING.md` สำหรับผลกระทบต่อ frontend/legacy accounts
ยังต้องตรวจ activation/account repair/doctor auth เพิ่ม ไม่ใช่ identity remediation ครบระบบ
ชุดรวมล่าสุด 207 tests ผ่านบน SQLite :memory: (exit 0)

repair ต้องใช้รหัสผ่านเดิมและรักษา password/email; legacy activation/name-phone disclosure
และ client-selected existing_doc_id ถูกระงับ ดู `ACCOUNT_REPAIR_ACTIVATION_SECURITY.md`
ยังต้อง verified activation/recovery UI, concurrency/rate limiting และ doctor auth
ชุดรวมล่าสุด 212 tests ผ่านบน SQLite :memory: (exit 0)

เพิ่ม verified LINE linking backend ใหม่ (ไม่ใช่เพียงระงับ): clinic password confirmation,
LINE token verification/channel/expiry/profile และ unique binding model + migration 0029
ยังต้องเชื่อม frontend/LINE config/ทดสอบจริง ดู `VERIFIED_LINE_LINKING.md`
ชุดรวมล่าสุด 222 tests ผ่านบน SQLite :memory: (exit 0)

เชื่อม LIFF UI/proxy กับ verified endpoint แล้ว พร้อม fixed login return path,
password confirmation, token errors และปิดกลับ LINE หลังสำเร็จ
frontend proxy tests 7 ข้อผ่าน; targeted lint ผ่าน; full TypeScript ยังมีข้อผิดพลาด
ที่ precision-report/axis-definitions ดู `VERIFIED_LINE_LINKING_UI.md`
ยังไม่ได้ LIFF จริง/visual QA/production build และ registration activation UI ยังมีงานค้าง

19 October 2026: ปรับ registration/login ตาม verified linking contract แล้ว
ถอด name-phone activation UI, ไม่ส่ง client LINE assertions และไม่ auto-close ก่อนเชื่อม
ตรวจ token pair และ normalize auth API URL; frontend tests 12 ผ่าน, full tsc ผ่าน
ดู REGISTRATION_LINKING_UX.md; ยังไม่ใช่ browser/LINE E2E หรือ production readiness
ยังค้าง verified physician/signoff, clinical reviewer/delivery workflow และ staging acceptance

19 October 2026: เพิ่ม physician approval preflight contract + pure tests 7 ข้อ
ตรวจ exact artifact/manifest/actor binding และ credential validity/revocation
ยังไม่ต่อ trusted credential source หรือ approval persistence/API; ไม่เปิด release gates
ดู PHYSICIAN_APPROVAL_PREFLIGHT.md สำหรับงานที่ยังต้องเชื่อมและข้อมูลที่คลินิกต้องยืนยัน

19 October 2026: เพิ่ม append-only ArtifactReviewEvent + internal service + migration 0030
บันทึก feedback ที่ไม่ใช่ approval; ชุด tests ที่เกี่ยวข้อง 21 ข้อผ่าน
ยังไม่ต่อ API/UI และยังขาด trusted physician verification/signoff persistence
ดู ARTIFACT_REVIEW_HISTORY.md; production migration ยังไม่ได้รัน

ต่อ API GET/POST review history พร้อม explicit permissions, strict input,
patient/artifact binding และ bounded cursor pagination แล้ว; ยังไม่มี frontend UI
ยังไม่เปิด clinical approval หรือ delivery; ดู ARTIFACT_REVIEW_HISTORY.md

เพิ่ม /doctor/artifact-review UI และลิงก์จากหน้าตรวจเดิม: เปิด exact IDs,
แสดง snapshot/hash, บันทึก feedback และโหลดประวัติแบบแบ่งหน้า
ยังเป็น technical review UI (JSON/manual IDs), ไม่ใช่ clinical signoff
ดู ARTIFACT_REVIEW_UI.md; ยังต้อง browser QA และ structured artifact picker/viewer

เพิ่ม patient search/artifact picker + metadata APIs และ evidence fact table แล้ว
backend selected suite 28 tests ผ่าน, tsc/lint ผ่าน; ยังต้อง browser QA,
structured WORKFLOW viewer และ clinical signoff/delivery integration

เพิ่ม structured WORKFLOW trace viewer แล้ว: คงลำดับ/รอบ/issues และ safety precheck
frontend selected suite 19 tests ผ่าน, TypeScript/targeted lint ผ่าน
ดู WORKFLOW_REVIEW_VIEWER.md; ยังไม่ทดสอบ browser จริงหรือเปิด signoff/delivery

เพิ่ม review request idempotency + migration 0031; API ต้อง UUID key,
replay คืน event เดิมและ key conflict ปฏิเสธ; ชุด backend ที่เกี่ยวข้อง 49 tests ผ่าน
ดู REVIEW_REQUEST_IDEMPOTENCY.md และ AGENTIC_REMAINING_WORK.md สำหรับงานที่ยังไม่เสร็จ

เชื่อม release-readiness diagnostics เข้าหน้าตรวจร่าง: แสดง blockers และ input freshness
ตรวจ response binding/contract แบบ fail-closed; ไม่มีปุ่มอนุมัติหรือส่ง
ดู RELEASE_READINESS_UI.md; frontend selected 22 tests และ backend artifact suite 18 tests ผ่าน

เพิ่ม runtime history validation (snapshot/IDs/cursor/no delivery authority)
และ session comparison ระหว่างโหลด/ก่อนบันทึก; selected frontend tests 25 ผ่าน
ดู REVIEW_RESPONSE_VALIDATION.md; ยังไม่ใช่ browser E2E และยังมี validation/QA งานค้าง

เพิ่ม review session isolation: ล้าง sensitive state เมื่อ token เปลี่ยนข้ามแท็บ,
generation guard ปฏิเสธ late responses รวม A→B→A; frontend selected suite 27 tests ผ่าน
ดู REVIEW_SESSION_ISOLATION.md; ยังต้อง browser multi-tab E2E และ same-tab auth integration

ชุดใหญ่ 19 October 2026: ปิด public staff signup/legacy auto-promotion + staff login limits,
read-only staff inventory, unique-owner notification token binding และ Chrome UI acceptance
backend selected 259 tests, frontend 27 tests, browser 8 scenarios ผ่าน; TypeScript ผ่าน
รายละเอียดและผลกระทบ rollout: DELIVERY_STATUS_2026-10-19.md, STAFF_AUTH_SECURITY.md,
ARTIFACT_REVIEW_BROWSER_ACCEPTANCE.md — ยังไม่ใช่ full production/LINE/PostgreSQL acceptance
