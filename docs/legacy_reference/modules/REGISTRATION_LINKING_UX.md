# Module: Registration and verified LINE handoff

## ทำอะไร

- สมัครบัญชีคลินิกไม่ส่ง line_user_id, existing_doc_id หรือ activation assertions
- ล้าง legacy activationPatient ไม่ใช้ prefill เวชระเบียนจาก browser
- ถอดฟอร์มเปิดบัญชีด้วยชื่อ/เบอร์โทรออกจาก login; ให้ติดต่อคลินิกแทน
- สำเร็จแล้วแสดงลิงก์ไป verified LINE linking; ไม่ปิดหน้าต่างอัตโนมัติก่อนเชื่อม
- ยังเลือกกลับ LINE โดยไม่เชื่อมได้ พร้อมข้อความบอกสถานะชัดเจน
- ตรวจ token pair ก่อนเก็บ และรองรับ API base แบบ origin หรือ /api/
- ล้าง password ในฟอร์มหลังสมัครสำเร็จ

## ทำไมถึงทำแบบนี้

ต่อจาก verified linking contract เดิม ไม่สร้างช่องทางยืนยันตัวตนใหม่
ทางเลือกปิดหน้าทันทีสะดวกกว่า แต่ผู้ใช้จะข้ามการเชื่อมที่ต้องยืนยันรหัสผ่าน
จึงแสดงผลและให้เลือกเชื่อม/กลับ LINE อย่างชัดเจน
ทางเลือกคง activation เดิมใช้งานง่าย แต่ชื่อและโทรศัพท์ไม่ใช่หลักฐานเจ้าของเวชระเบียน
ระบบเปิดบัญชีเดิมผ่านเจ้าหน้าที่ที่ตรวจสอบได้ยังต้องพัฒนาต่อ

## โครงสร้างไฟล์

- frontend/src/app/patient/register/page.tsx
- frontend/src/app/patient/login/page.tsx
- frontend/src/lib/patient-auth-response.ts
- frontend/tests/patient-auth-response.test.cjs

## ผลตรวจ 19 October 2026

- node --test tests/verified-line-route.test.cjs tests/patient-auth-response.test.cjs: 12 ผ่าน
- มี unit tests กับ mocked proxy และ source guards 2 ข้อ; ไม่ใช่ browser E2E
- TypeScript ทั้ง frontend ผ่านด้วย --noEmit --incremental false
- targeted ESLint login/register/helper: ไม่มี error มี warning 9 ข้อ (img/unused เดิม)
- แก้ implicit-any callbacks ของ precision-report และ optional context mapping ใน axis-definitions
- ไม่ได้ทำ production build, ทดสอบอุปกรณ์จริง, deploy, push หรือ production migration

## จุดที่ต้องระวัง

ต้องตั้งค่า backend/LINE และ migration 0029 ก่อนทดสอบ staging
การสมัครสำเร็จไม่ได้ให้สิทธิ์อนุมัติหรือส่งรายงานทางคลินิก
ยังใช้ localStorage JWT เดิม ไม่ใช่ HttpOnly session และยังต้องทำ rate limiting/recovery
หากได้ response ไม่ครบ ไม่ควรสมัครซ้ำทันที ให้คลินิกตรวจสอบบัญชี
ยังต้องทดสอบ account switching, token expiry และคลิก flow จริงบน LINE

## อ้างอิง

- VERIFIED_LINE_LINKING_UI.md
- ACCOUNT_REPAIR_ACTIVATION_SECURITY.md
- Next.js bundled docs: use-client directive
