# Module: Verified LINE linking backend

## ทำอะไร

เพิ่ม POST `/api/line/verified-link/` สำหรับผู้ใช้ที่ล็อกอินคลินิกแล้ว
รับเฉพาะ password และ access_token (LINE user access token ไม่ใช่ channel access token)
ตรวจรหัสผ่านเดิม, verify token กับ LINE, client_id ตรง LINE_LOGIN_CHANNEL_ID,
expires_in > 0 และ profile scope แล้วดึง userId จาก LINE /v2/profile
ไม่รับ patient ID, LINE ID, display name หรือเบอร์โทรจาก client เป็นหลักฐาน ownership

## การบันทึก

ใช้ transaction และ patient row lock; VerifiedLineBinding มี patient OneToOne และ line_user_id unique
ไม่ย้าย binding ของคนอื่น ไม่เปลี่ยน LINE เดิมเป็นบัญชีอื่นอัตโนมัติ
ทำซ้ำกับคู่เดิมคืน ALREADY_LINKED ไม่สร้าง audit ซ้ำ
audit write ล้มเหลวต้อง rollback ทั้ง binding และ patient field
ไม่ส่ง welcome push และไม่เก็บ access token/password ใน model หรือ audit
generic PatientSerializer ไม่รับการเขียนฟิลด์ LINE เพื่อข้าม verified endpoint

## ทางเลือกและข้อแลกเปลี่ยน

เลือก verify access token + profile ตามเอกสาร LINE แทนเชื่อ profile จาก client
ใช้รหัสผ่านคลินิกยืนยันซ้ำ แทน phone-only activation
เพิ่มตาราง constraint แยก ไม่ backfill หรือแก้ duplicate legacy bindings อัตโนมัติ
กรณี conflict ต้องให้คลินิกตรวจสอบ ไม่เคลียร์บัญชีคนอื่น

## ไฟล์

- backend/patients/verified_line_link.py
- backend/patients/models.py: VerifiedLineBinding
- backend/patients/migrations/0029_verified_line_binding.py
- backend/patients/views_line.py และ urls.py: authenticated endpoint
- backend/patients/tests_verified_line_link.py: 10 tests

## ผลทดสอบ 18 October 2026

ชุดรวม 222 tests ผ่านบน SQLite :memory: (exit 0)
provider responses เป็น mock ไม่ใช้ LINE tokens จริง ไม่มี outbound LINE test
ทดสอบ success/idempotency, password, channel, expiry, scope, client assertions,
binding conflicts, audit rollback, unavailable provider/config, authentication และ generic update bypass
migration ใช้เฉพาะฐานข้อมูลทดสอบ ยังไม่ได้ apply กับฐานข้อมูลใช้งานจริง

## ก่อนเปิดใช้งาน

- ผู้ใช้ต้อง review/apply migration 0029 ใน workflow deployment ที่อนุมัติ
- ตั้ง LINE_LOGIN_CHANNEL_ID เป็น LINE Login channel ของ LIFF (ไม่ใช่ Messaging API channel)
- LINE Login และ Messaging API ต้องใช้ provider ที่ให้ user IDs สอดคล้องกัน ตรวจจากระบบจริง
- เชื่อม frontend ให้ส่ง clinic JWT, รหัสผ่านยืนยัน และ liff.getAccessToken()
- ยังไม่ได้ทดสอบ end-to-end กับ LINE จริง, PostgreSQL concurrency, rate limiting หรือ UX consent
- backend ใหม่ยังไม่ได้แทนหน้า LIFF เดิมที่ส่ง phone/lineUserId
- account activation, physician sign-off และ report release ยังเป็นงานแยกที่ไม่เสร็จ
- ไม่มี production migration, deploy หรือ push

## อ้างอิง

https://developers.line.biz/en/docs/liff/using-user-profile/
https://developers.line.biz/en/reference/line-login/
