# Module: Review response validation

## ทำอะไร

ตรวจรูปแบบ history ก่อน render ทั้งตอนเปิดร่าง บันทึก และโหลดหน้าเก่า
ต้อง artifact hash ตรง, ไม่มี delivery authority, IDs เรียงลดลงและไม่ซ้ำ,
cursor ตรงท้ายหน้าที่ครบ 50 และหน้าถัดไปไม่มี ID ทับกับหน้าปัจจุบัน
ไม่รับ decision ที่ไม่ใช่ feedback หรือ timestamp ที่ parse ไม่ได้

เพิ่ม session-token comparison หลังรับ JSON, ระหว่างเปิดร่าง/โหลดประวัติ
และก่อนบันทึก หากบัญชีเปลี่ยนต้องเปิดร่างและยืนยันใหม่

## ทำไมถึงทำแบบนี้

TypeScript cast ไม่ตรวจ runtime response; malformed JSON object อาจทำให้หน้า crash
หรือแสดง history ผิด snapshot จึง validate ก่อนเปลี่ยน state
อีกทางเลือกคือเชื่อ response backend ทั้งหมด แต่ไม่ครอบคลุม regression/proxy failure

## ไฟล์

- frontend/src/lib/review-history-response.ts
- frontend/src/app/doctor/artifact-review/page.tsx
- frontend/tests/review-history-response.test.cjs

## ผลตรวจ

Frontend selected tests 25 ผ่าน รวม parser regressions 3 ข้อใหม่
targeted lint ผ่าน; full TypeScript ตรวจแยก
ไม่ใช่ browser E2E ไม่ได้จำลอง React clicks หรือ request race จริง
session comparison ยังไม่ทดสอบแบบ browser multi-tab และไม่ทดแทน server authorization
ยังต้อง clear sensitive UI ทันทีเมื่อ logout ข้าม tab, validate picker/artifact payload เพิ่ม
ไม่ได้เพิ่ม dependencies, deploy/push หรือ production migration
