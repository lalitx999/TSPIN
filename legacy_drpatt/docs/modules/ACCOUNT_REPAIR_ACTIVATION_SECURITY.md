# Module: Account repair and legacy activation security

## ทำอะไร

- บัญชี Django เดิมที่ไม่มี Patient profile ต้อง authenticate ด้วยรหัสผ่านเดิมก่อนซ่อม
- ไม่ reset password หรือเปลี่ยน email จาก registration payload ระหว่าง repair
- inactive account ซ่อมผ่าน registration ไม่ได้
- activation ด้วยชื่อ/เบอร์โทรถูกระงับ ไม่คืนเวชระเบียนจากข้อมูลระบุตัวตนเพียงอย่างเดียว
- request ที่ส่ง is_activation_mode หรือ existing_doc_id ถูกปฏิเสธก่อนสร้าง user
- เอาโค้ดแก้เวชระเบียนตาม existing_doc_id จาก client ออก

## ทำไมถึงทำแบบนี้

การเปลี่ยนรหัสผ่านทันทีเพราะไม่มี Patient profile ไม่ได้พิสูจน์เจ้าของบัญชี
จึงเลือกตรวจรหัสผ่านเดิมแทน reset แบบไม่ยืนยันตัวตน
ส่วน legacy activation ไม่มี trusted proof ที่ใช้ได้ จึงระงับก่อนแทนการเดา ownership จากชื่อ/โทรศัพท์
ผู้ลืมรหัสผ่านต้องผ่าน recovery ที่ยืนยันตัวตนหรือติดต่อคลินิก ไม่ข้ามด้วย registration

## โครงสร้างไฟล์

- backend/accounts/views.py: authenticated repair และ activation containment
- backend/patients/tests_account_identity_security.py: password/email preservation, inactive, activation guards
- backend/patients/tests.py: successful repair fixture ใช้รหัสผ่านเดิมจริง

## ผลกระทบและข้อจำกัด

legacy activation wizard เดิมยังใช้ไม่ได้ ต้องออกแบบ verified activation flow และปรับ frontend
new registration และ repair ที่ใช้รหัสผ่านเดิมยังทำงานตาม tests
ยังต้องทดสอบ concurrent repair บน PostgreSQL, rate limiting, doctor auth และ UI recovery
ไม่เปลี่ยนรหัสผ่านหรือข้อมูลผู้ใช้จริง ไม่มี production migration/deploy/push

## ผลทดสอบ

18 October 2026: account identity + registration suite 15 tests ผ่านบน SQLite :memory:
audit unavailable เป็น error ที่ mock ตั้งใจให้เกิดเพื่อทดสอบ rollback
ชุดรวมล่าสุด 212 tests ผ่าน (exit 0), Django system check ไม่พบปัญหา
