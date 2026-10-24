# Module: Agentic review UI

## ทำอะไร

หน้า /doctor/artifact-review มีลิงก์จาก clinical-review เดิม
ระบุ Patient ID/Artifact UUID แล้วโหลดร่างและประวัติจาก API
แสดง snapshot JSON แบบ escaped text, hash, ผู้ตรวจและเวลาในประวัติ
มีสาม feedback decisions เท่านั้น ไม่มีอนุมัติ/ส่งรายงาน
ต้องยืนยันได้ตรวจฉบับที่แสดงแล้วและกรอกเหตุผลก่อนบันทึก

## ทำไมถึงทำแบบนี้

หน้าตรวจเดิมใช้ Digital Twin คนละ contract; การแทนที่ทันทีเสี่ยงสลับฉบับ
จึงเพิ่มหน้าแยกที่ผูก exact artifact ก่อน แทนการเดาว่ารายงานเดิมคือ artifact ใหม่
ข้อจำกัดคือยังต้องระบุ IDs เองและอ่าน JSON; ต้องพัฒนา artifact picker/structured viewer ต่อ

อัปเดต: เพิ่มค้นผู้ป่วยด้วย HN/ชื่อ (2–100 ตัวอักษร) เฉพาะผู้ป่วยที่มี artifact
ค้นครั้งละไม่เกิน 50 รายและแจ้งให้ค้นแคบลงเมื่อมากกว่านั้น
เลือกร่างจากรายการครั้งละ 50 พร้อม cursor; เรียง UUID ไม่ใช่ลำดับล่าสุดตามเวลา
ยังมีช่อง IDs สำหรับใช้โดยเจ้าหน้าที่ และล้างร่างเดิมเมื่อเปลี่ยนผู้ป่วย
EVIDENCE_DRAFT แสดง facts ฉบับ PHYSICIAN เป็นตารางตรงต้นฉบับ ไม่คำนวณหรือแปลค่า
WORKFLOW และรูปแบบอื่นยังดูผ่าน JSON; ยังไม่มี structured workflow trace viewer

## ไฟล์

- frontend/src/app/doctor/artifact-review/page.tsx
- frontend/src/app/doctor/clinical-review/page.tsx (navigation link)
- frontend/tests/artifact-review-ui.test.cjs

## ข้อควรระวัง

ใช้ doctor JWT เท่านั้น ไม่ fallback patient token; backend เป็นผู้ตัดสินสิทธิ์
ต้องมี migration 0030 และ permissions ตาม ARTIFACT_REVIEW_HISTORY.md
ไม่เก็บร่าง/เหตุผลใน browser storage; fetch no-store/no redirect และ timeout
หากผล POST ไม่ชัดเจนต้องเปิดร่างและตรวจประวัติก่อนส่งซ้ำ ไม่มี automatic retry
การ reload ไม่ใช่การรับประกัน exactly-once; backend ยังไม่มี idempotency key
ยังต้องทดสอบ browser/mobile/role switching จริงและ PostgreSQL staging
ยังไม่เชื่อมทะเบียนแพทย์หรือ signed clinical approval

## การตรวจ

มี source guards 3 ข้อ ไม่ใช่ interactive browser E2E
ตรวจ TypeScript และ ESLint เฉพาะหน้าใหม่แยกจาก legacy clinical-review
ไม่มี production build/deploy/push หรือ migration จริงในรอบนี้

ผลตรวจ 19 October 2026: frontend selected suite 15 tests ผ่าน (รวม source guards),
full tsc --noEmit --incremental false ผ่าน และ ESLint หน้าใหม่ exit 0
มีคำเตือน config เดิม .eslintignore; ยังไม่ได้ interactive browser QA

ผลตรวจหลังเพิ่ม picker/table: backend artifact review + agentic service ผ่าน 28 tests
รวม search/list permissions และ malformed cursor; full TypeScript และ lint หน้าใหม่ผ่าน
ยังไม่ได้ browser visual/interaction QA หรือทดสอบ pagination พร้อม concurrent inserts บน PostgreSQL
