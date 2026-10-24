# Module: Account identity binding containment

## ทำอะไร

registration ปฏิเสธ line_user_id/lineUserId ที่มีค่าก่อนสร้างบัญชี ไม่ผูกหรือส่ง welcome push
login/me เลือก patient เฉพาะ id_card ที่ตรง username เพียงหนึ่งราย ไม่ fallback ตาม email
email login ต้องค้นเจอ Django user เพียงหนึ่งราย ถ้าซ้ำให้ใช้ citizen-ID login หรือคลินิกตรวจสอบ

## ทำไมถึงทำแบบนี้

ทางเลือก fallback ไปตาม email อาจให้บัญชีที่ไม่มี EMR ได้ข้อมูลของคนอื่นจากอีเมลร่วม/ว่าง
จึงเลือก explicit unique binding; สิทธิ์เข้าใช้ได้ปกติไม่ได้แปลว่ามีสิทธิ์เป็นเจ้าของทุก profile ที่อีเมลตรง
LINE ID ใน URL/request ไม่ใช่หลักฐานควบคุม LINE account

## ผลกระทบ

- registration request ที่ยังส่ง LINE ID จะได้ 400 VERIFIED_ACCOUNT_LINK_REQUIRED
  ต้องปรับ frontend ให้แจ้งเรื่องการเชื่อมแยก ไม่แสดงว่าสำเร็จแล้ว
- บัญชีที่เคยพึ่ง email fallback หรือมี patient ID ซ้ำจะได้ 404 แทนข้อมูลผู้ป่วย
- unique identity login ยังได้ tokens และข้อมูลผู้ป่วยตามเดิม
- ไม่เปลี่ยนบัญชีเดิมหรือแก้ binding อัตโนมัติ

## โครงสร้างไฟล์

- backend/accounts/views.py: registration containment, unique account/profile lookup
- backend/patients/tests_account_identity_security.py: 5 regression tests

## ทดสอบและข้อจำกัด

account identity tests + PatientRegistrationTests รวม 10 ข้อผ่านบน SQLite :memory:
audit unavailable เป็น intentional mocked failure ใน rollback test
ยังต้องตรวจ legacy activation (existing_doc_id), incomplete-account password repair,
doctor authentication และ frontend integration ก่อนถือว่าปิด identity gaps ทั้งระบบ
ยังไม่ใช่ verified LINE linking flow ที่พร้อมใช้ ไม่มี production migration/deploy/push
18 October 2026: ชุดรวมล่าสุด 207 tests ผ่าน (exit 0), Django system check ไม่พบปัญหา
