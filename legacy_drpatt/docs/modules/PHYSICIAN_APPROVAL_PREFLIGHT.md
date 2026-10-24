# Module: Physician approval preflight

## ทำอะไร

เพิ่ม internal pure validator สำหรับข้อมูลจาก trusted backend adapter เท่านั้น
ตรวจ actor/patient/artifact/content hash/manifest hash ตรงกับรายการอนุมัติ
ตรวจ provenance ใบอนุญาต ช่วงเวลา สถานะเพิกถอน และการยืนยันก่อนลงนาม
ไม่ถือ doctor group, superuser หรือ client checkbox เป็นหลักฐานใบอนุญาต

## ทำไมถึงทำแบบนี้

ทางเลือกใช้ role เดิมทำได้เร็ว แต่ไม่พิสูจน์สถานะแพทย์หรือฉบับรายงานที่ตรวจ
ทางเลือกแยก preflight ที่ไม่ให้สิทธิ์ส่ง ช่วยทดสอบ binding ก่อนต่อแหล่งข้อมูลจริง
ใช้ทางเลือกหลังตาม verified-signoff workstream; ยังไม่ใช่ระบบอนุมัติสำเร็จรูป

## โครงสร้างไฟล์

- backend/patients/physician_approval.py
- backend/patients/tests_physician_approval.py

## ขอบเขตและข้อควรระวัง

- ยังไม่เรียกจาก API/release readiness; ไม่มี endpoint รับ credential/approval JSON
- ไม่ตรวจลายเซ็นดิจิทัลหรือค้นทะเบียนใบอนุญาตจริง
- APPROVAL_PREFLIGHT_PASSED หมายถึงข้อมูลที่ป้อนผ่านเงื่อนไขเท่านั้น
- diagnostic_only=true และ send_allowed/clinical_use_authorized=false เสมอ
- ต้องมี trusted persisted verification/revocation source และ approval audit ก่อนเชื่อมใช้งาน
- ต้องตกลงแหล่งตรวจใบอนุญาต ผู้มีสิทธิ์ยืนยัน และรอบตรวจซ้ำกับคลินิก
- ไม่สร้าง migration, ไม่เปลี่ยนสิทธิ์ส่ง PDF/LINE หรือสถานะอนุมัติเดิม

## ผลทดสอบ 19 October 2026

Pure unit tests 7 ข้อผ่าน: binding ทุก field, expired/revoked/wrong actor,
provenance, signing time, client assertions, malformed context และไม่แก้ snapshot
ทุกข้อมูลเป็น synthetic; ไม่ใช่การยืนยันแพทย์จริงหรือ staging acceptance

ชุดรวม physician_approval + release_security + agentic_service ผ่าน 35 tests
บนฐานข้อมูลทดสอบ SQLite; Django system check ไม่พบปัญหา
