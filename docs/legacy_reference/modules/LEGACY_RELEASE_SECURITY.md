# Module: Legacy release authorization hardening

## ทำอะไร

ปิดช่องทาง API `ai/report-release-transition/` ที่ยอมรับ
`is_physician_signoff=true` จาก client เป็นการยืนยันแพทย์
superuser และกลุ่ม Physician ก็ไม่ใช่หลักฐานยืนยันใบอนุญาตหรือ signed output

API ยังรับ AI_DRAFT และ PHYSICIAN_REVIEWED ตามลำดับเดิม
แต่ PHYSICIAN_APPROVED/PATIENT_RELEASED ถูกปฏิเสธจนกว่าจะมี trusted sign-off integration
ไม่มี fallback หรือ environment flag เพื่อข้ามเงื่อนไขนี้

## ทำไมถึงทำแบบนี้

ทางเลือกแก้เฉพาะ request flag ยังเหลือการใช้ admin/group เป็นตัวแทนใบอนุญาต
จึงเลือก fail closed สำหรับการอนุมัติ/ส่งใน API นี้ ข้อแลกเปลี่ยนสำคัญคือ
ผู้ใช้งานจะยังอนุมัติรายงานใหม่ผ่าน endpoint นี้ไม่ได้หลังนำโค้ดไปใช้
การเปิดใช้งานต่อจำเป็นต้องมี server-verified physician identity และการผูกลายเซ็นกับฉบับรายงาน

## โครงสร้างไฟล์

- backend/patients/views_ai.py: transition endpoint, validated record ID, transaction/row lock
- backend/patients/tests_release_security.py: 5 regression tests

## ผลทดสอบ

18 October 2026: security + artifact suites รวม 23 tests ผ่านบน SQLite :memory:
ตรวจ draft/review, self-attested flag, admin/group bypass, malformed ID,
nonstaff และ repeated transition ไม่มีแถวซ้ำ
row locking ต้องทดสอบ concurrent requests บน PostgreSQL เพิ่ม (SQLite ไม่ยืนยันคุณสมบัตินี้)
รันชุดรวมพร้อม ReportApprovalStateTests และ GenerateClinicalPdfGatingTests: 172 tests ผ่าน (exit 0)

## ขอบเขตที่ยังไม่ครบ

- ไม่ได้ revoke หรือแก้ release records เก่า
- ไม่ได้เปลี่ยน PDF/LINE delivery gate ทั้งหมด จึงไม่อ้างว่าปิดการส่งรายงานทุกช่องทางแล้ว
- ยังต้องตรวจ privileged ORM/admin writes และความถูกต้องของ approvals เดิม
- ยังไม่มี licence verifier, signed report digest, expiry/revocation checks หรือ release consent integration
- ไม่มี production migration, deploy หรือ push
