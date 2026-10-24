# Module: Review request idempotency

## ทำอะไร

POST review ต้องมี request_id UUID; scope คือ artifact + actor + request_id
คำขอซ้ำที่ hash/decision/reason เหมือนเดิมคืน event เดิม HTTP 200 และ replayed=true
คำขอใหม่ HTTP 201; key เดิมแต่ payload ต่างคืน 409 ไม่แก้ประวัติ
ตรวจ permissions และ artifact integrity ใหม่ก่อนคืนผล replay ทุกครั้ง

## ทำไมถึงทำแบบนี้

ทางเลือกปิดปุ่มเฉพาะหน้าเว็บกัน double click ได้ แต่กัน response loss ไม่ได้
ใช้ request identity พร้อม transaction lock และ unique DB constraint
ไม่ deduplicate ตามข้อความเพียงอย่างเดียว เพราะผู้ตรวจอาจตั้งใจส่งข้อความเดิมใหม่

## ไฟล์

- backend/patients/artifact_review.py / views.py / models.py
- backend/patients/migrations/0031_artifact_review_request_id.py
- backend/patients/tests_artifact_review.py
- frontend/src/app/doctor/artifact-review/page.tsx

## ขอบเขต

request_id nullable สำหรับประวัติเก่า; internal service ที่ไม่ส่ง key ยังสร้าง event ใหม่
API ใหม่บังคับ key จึงต้อง deploy frontend/backend ให้เข้ากันหลัง migration
หน้าเว็บเก็บ pending key ใน memory เท่านั้น ใช้ซ้ำเมื่อ payload เดิมและ response ยังไม่ยืนยัน
ไม่คง key หลัง browser reload/unmount; ต้องตรวจประวัติก่อนส่งใหม่ ไม่รับประกัน exactly-once ข้าม session
ยังคงบังคับเปิดร่าง/อ่านประวัติก่อนลองซ้ำเมื่อผลไม่ชัดเจน ไม่มี automatic retry
ไม่เพิ่มสิทธิ์ clinical approval หรือ delivery

## ผลตรวจ 19 October 2026

ชุด backend review/preflight/release/artifact ผ่าน 49 tests บน SQLite test DB
ครอบคลุม replay, conflicting payload, revoked permission, malformed key และ DB uniqueness
TypeScript และ targeted ESLint ผ่าน (มี warning .eslintignore เดิม)
ยังไม่ได้ PostgreSQL concurrent request test หรือ browser network-loss E2E
migration 0031 ยังไม่รัน production; ไม่ push/deploy
