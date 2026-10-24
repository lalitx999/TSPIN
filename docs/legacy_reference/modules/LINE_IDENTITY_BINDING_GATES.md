# Module: LINE identity binding containment

## ทำอะไร

- เลขบัตรในแชตไม่ค้น/เปลี่ยนบัญชี และตอบข้อความเดียวกันทั้งเลขที่มีและไม่มีในระบบ
- LINE เดียวพบหลาย patient จะหยุด event ไม่เลือกคนที่อัปเดตล่าสุด ไม่ส่งชื่อ/HN
- ระงับ legacy line/link และ liff/identity ด้วย VERIFIED_ACCOUNT_LINK_REQUIRED
  ไม่ค้นเบอร์ ไม่แก้ binding ไม่ใช้/ลบ token และไม่ส่ง welcome push

## ทำไมถึงทำแบบนี้

ทางเลือกคงการผูกด้วยเลขบัตร/เบอร์ต่อไปแม้ตรวจ webhook signature แล้ว
ยังอนุญาตให้ผู้ใช้ LINE จริงอ้างข้อมูลคนอื่นได้ จึงเลือก containment แบบ fail closed
ลายเซ็น channel ไม่ได้ยืนยันเจ้าของเวชระเบียน และ lineUserId จาก client ไม่ใช่ token ที่ตรวจสอบแล้ว

## ผลกระทบ

การเชื่อมใหม่ผ่านเลขบัตรในแชตและสอง endpoints นี้จะใช้ไม่ได้จนพัฒนา verified linking flow
บัญชีเดิมไม่ถูกลบหรือย้าย; binding ที่ซ้ำต้องให้คลินิกตรวจสอบ ไม่แก้อัตโนมัติ
ยังไม่ใช่ระบบ linking ใหม่ที่เสร็จพร้อมใช้งาน

## โครงสร้างไฟล์

- backend/patients/views_line.py: duplicate binding guard, ID-only denial, legacy endpoint containment
- backend/patients/tests_line_identity_security.py: 5 synthetic regressions

## ทดสอบและงานค้าง

ทดสอบ signed webhook, matched/unmatched ID response, unlinked account,
duplicate identity และ legacy endpoint ไม่มี lookup/token consumption/push
ไม่เรียก LINE จริง ใช้ SQLite :memory:
ยังต้องทำ authenticated clinic account + server-verified LINE token/nonce,
one-time atomic linking, database uniqueness, replay protection และ audit failure outcomes
ยังต้อง audit registration/login endpoints ที่รับ line_user_id ด้วย
ไม่มี production migration/deploy/push
18 October 2026: ชุดรวมล่าสุด 198 tests ผ่าน (exit 0), Django system check ไม่พบปัญหา
