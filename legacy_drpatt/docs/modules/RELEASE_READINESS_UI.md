# Module: Release readiness diagnostics UI

## ทำอะไร

หน้าตรวจร่างเรียก GET release-readiness เมื่อผู้ตรวจร้องขอ
แสดงเหตุผลที่ยังส่งไม่ได้ ความตรงกันของ manifest และเวลาที่ browser รับผล (กรุงเทพฯ)
ล้างผลเก่าทุกครั้งที่ตรวจใหม่; remount ตาม artifact เพื่อไม่แสดงผลของฉบับก่อน
แสดงคำเตือนว่าผลตรวจ ณ เวลานั้นไม่แทน pre-send check

## ทำไมถึงทำแบบนี้

ทางเลือกแสดงป้ายพร้อมส่งเมื่อ input ตรงกันจะทำให้เข้าใจผิดว่าได้รับอนุมัติ
จึงรับเฉพาะ diagnostic-only BLOCKED contract และไม่สร้างปุ่มส่ง
ค่าตอบกลับไม่ครบ/ไม่ตรง artifact/อ้างอนุญาตส่ง หรือ hash ขัดแย้งต้องปฏิเสธ
unknown issue codes แสดงเป็นเงื่อนไขเพิ่มเติม ไม่ถือว่าผ่าน

## ไฟล์

- frontend/src/components/ReleaseReadinessPanel.tsx
- frontend/src/lib/release-readiness-view.ts
- frontend/tests/release-readiness-view.test.cjs
- frontend/src/app/doctor/artifact-review/page.tsx
- backend/patients/views.py: readiness success response เพิ่ม no-store

## ผลตรวจ 19 October 2026

Selected frontend suite 22 tests ผ่าน; full TypeScript และ targeted lint ผ่าน
backend agentic service suite 18 tests ผ่านบน SQLite test database
ยังไม่มี browser visual/E2E; เวลาที่แสดงเป็นเวลารับผลของ browser ไม่ใช่ server attestation
ไม่มี production migration/push/deploy; ไม่เปลี่ยนเงื่อนไขอนุมัติหรือส่งจริง
