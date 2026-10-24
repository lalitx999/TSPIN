# Module: Workflow review viewer

## ทำอะไร

แสดง state/reason/rounds และ trace ตามลำดับที่ backend บันทึกจริง
แต่ละขั้นแสดง role, decision, issues, เวลา, handler version และ input/output/draft hashes
แสดง SAFETY_PRECHECK ที่เกิดก่อน workflow พร้อมรายละเอียดเดิม ไม่ซ่อน alert เมื่อ rounds=0
คง JSON ต้นฉบับในหน้าตรวจร่าง และไม่สร้างขั้นที่ยังไม่ได้รัน

## ทำไมถึงทำแบบนี้

ทางเลือกแสดงครบ 18 ขั้นพร้อมสถานะ default เสี่ยงทำให้เข้าใจว่าขั้นที่ไม่มีได้ผ่านแล้ว
จึงแสดงเฉพาะ trace จริง พร้อมคำเตือนว่า PASS ไม่ใช่อนุมัติทางคลินิก
ข้อความแสดงผ่าน React escaping ไม่แปลงเนื้อหาเป็น HTML

## ไฟล์

- frontend/src/lib/workflow-review-view.ts: presentation mapping ไม่แก้ payload
- frontend/src/components/WorkflowReviewTrace.tsx: structured trace component
- frontend/src/app/doctor/artifact-review/page.tsx: เลือก viewer ตาม artifact kind
- frontend/tests/workflow-review-view.test.cjs

## ผลตรวจ

19 October 2026: selected frontend suite 19 tests ผ่าน (unit/source guards/mock proxy)
full TypeScript และ targeted ESLint ผ่าน; มี warning .eslintignore จาก config เดิม
ครอบคลุม missing/malformed trace, revision order, missing handler, zero-round safety,
unknown decisions และไม่แก้ snapshot; ยังไม่ใช่ browser visual/E2E test

## งานค้าง

รายละเอียด safety ยังแสดงเป็น structured JSON ภายในส่วนเตือน
ยังไม่แปล clinical issue codes เป็นคำแนะนำทางการแพทย์
ต้อง browser QA, account switching และ staging integration ก่อนใช้จริง
ไม่เปลี่ยน backend gate ไม่ยืนยันใบอนุญาต ไม่อนุมัติหรือส่งรายงาน
