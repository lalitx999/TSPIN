# Module: Clinical PDF access and legacy release gates

## ทำอะไร

- Clinical dossier HTML ต้องเป็น clinical staff ตาม access policy เดิม
- Saved report PDF ต้องตรวจสิทธิ์ patient ก่อนอ่านรายงาน
- Physician/Multi-Omics Edition เปิดให้ clinical reviewers เท่านั้น ไม่ให้ patient owner ดูร่างภายใน
- ปฏิเสธ edition ที่ไม่รู้จัก ไม่ตีความเป็น edition อื่น
- Patient Edition หยุดด้วย VERIFIED_PHYSICIAN_SIGNOFF_REQUIRED แม้มี PATIENT_RELEASED เดิม

## ทำไมถึงทำแบบนี้

ทางเลือกเชื่อ release row เดิมยังเปิดให้สถานะที่เคยสร้างจาก self-attestation ใช้ส่งต่อได้
จึงเลือกหยุด Patient PDF จนมีการยืนยันผู้ลงนามที่ผูกกับเนื้อหาฉบับนั้น
ข้อแลกเปลี่ยน: รวมถึงรายงานที่เคยปล่อยแล้วก็ยังดาวน์โหลด Patient PDF ผ่าน endpoint นี้ไม่ได้
ไม่ได้ลบหรือ revoke ประวัติเดิม และยังคงเส้นทาง clinical draft review สำหรับเจ้าหน้าที่

## โครงสร้างไฟล์

- backend/patients/permissions.py: can_review_clinical_reports เป็นสิทธิ์ review ไม่ใช่การยืนยันแพทย์
- backend/patients/views_ai.py: guards ก่อนสร้าง dossier/saved report PDF
- backend/patients/tests_release_security.py: เพิ่ม 5 authorization/delivery regressions
- backend/patients/tests.py: fixture doctor2 ระบุ is_staff ให้ตรงสิทธิ์ review ที่ทดสอบ

## ผลทดสอบ

18 October 2026: release security + GenerateClinicalPdfGatingTests รวม 13 ข้อผ่าน
บน SQLite :memory: ไม่มี production writes/deploy/push
รันชุดรวมซ้ำ 177 tests ผ่าน (exit 0); Django system check ไม่พบปัญหา

## ยังไม่ครบ

ยังไม่ได้ยืนยันสิทธิ์แพทย์จริง, signed content digest, recipient verification หรือ consent
ยังไม่ได้ audit การแสดง generated_reports ใน patient JSON/frontend, LINE และทุกช่องทาง export
จึงไม่อ้างว่าข้อมูลรายงานถูกป้องกันครบทุกช่องทางแล้ว
