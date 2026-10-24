# Module: Staff authentication hardening — 19 October 2026

## ผลลัพธ์

- ปิด public doctor/register: 403 STAFF_PROVISIONING_REQUIRED ไม่มี user/token/legacy-table write
- doctor/login ใช้เฉพาะ Django user ที่ email ตรงเพียงรายเดียว active และ staff
- ถอด plaintext/MD5/SHA256 legacy admin authentication, auto-create/auto-promote และ credential debug prints
- คง success audit และ JWT สำหรับบัญชีเจ้าหน้าที่ Django เดิม; response no-store
- doctor/me เปลี่ยนได้เฉพาะ first_name/last_name แบบ bounded string; ไม่แก้ email/role/password ผ่าน profile
- หน้า register เป็นคำแนะนำติดต่อคลินิก; profile email เป็น read-only; login validates token pair
- normalize API base ทั้ง origin และ origin/api สำหรับ doctor login/layout/shared service
- FCM registration ต้อง unique username→patient binding ไม่ใช้ shared email หรือ first-match

## เหตุผลและทางเลือก

คง legacy auto-promotion ใช้งานสะดวก แต่ใครสมัครเองก็ได้ staff และ legacy login เปลี่ยน password/role ได้
จึงปิดทางยกระดับสิทธิ์อัตโนมัติ ไม่แตะบัญชีที่มีอยู่ และให้คลินิก review ก่อนย้ายบัญชีเก่า
ไม่ถือ is_staff เป็นหลักฐานใบอนุญาตหรือ clinical signoff

## Staff login limits

Fixed window 60 วินาที: default 60 ครั้งต่อ REMOTE_ADDR และ 10 ครั้งต่ออีเมล
key เป็น HMAC ไม่ใส่อีเมลหรือ IP ตรง ๆ ใน cache key; lowercase/trim อีเมล
ไม่ใช้ client-supplied X-Forwarded-For เพื่อป้องกันหมุน key; หลัง reverse proxy อาจรวมหลายคนเป็น IP เดียว
นับทั้งสำเร็จ/ไม่สำเร็จ; ตอบ 429 พร้อม Retry-After, cache failure ปฏิเสธ ไม่ bypass
ใช้ cache.add/incr; fixed-window boundary อาจอนุญาต burst สอง window ติดต่อกัน
นี่ไม่ใช่ DDoS protection และไม่ได้แทน edge/WAF limits

Settings/env: STAFF_LOGIN_IP_LIMIT_PER_MINUTE, STAFF_LOGIN_ACCOUNT_LIMIT_PER_MINUTE,
STAFF_LOGIN_CACHE_ALIAS (alias ต้องมีใน Django CACHES)
หลาย worker ต้อง shared cache ที่รองรับ atomic add/incr; default LocMem ยังไม่เหมาะ production
`python manage.py check --deploy` เตือน accounts.W001 สำหรับ backend ที่ยังไม่ยืนยัน
ไม่ได้ติดตั้ง Redis/Memcached driver หรือเปลี่ยน infrastructure ให้เอง
ยังต้องกำหนด trusted proxy/limits ให้เหมาะกับคลินิกและทดสอบ load
ยังไม่ได้ครอบคลุม patient authentication/ทุก write endpoint

## ตรวจบัญชีเดิมก่อน rollout (ผู้ใช้รันเอง)

`python manage.py audit_staff_provisioning`

คำสั่งอ่านอย่างเดียว คืน staff IDs, active/superuser flags และมี public-signup audit หรือไม่
ไม่คืน password/hash/email และไม่ revoke/verify/promote บัญชี
ไม่มี audit ไม่แปลว่าบัญชีได้รับการยืนยัน ต้อง review ทุก staff account
บัญชีเก่าที่ถูกยกระดับไปแล้วไม่ได้ถูกแก้โดย patch นี้
ตรวจการเข้าถึง log เก่าที่อาจบันทึก credential และกำหนด credential rotation/retention กับผู้ดูแล
ไม่ลบ log หรือบัญชีอัตโนมัติ เพื่อไม่ทำลายประวัติและไม่ตัดสิทธิ์ผิดคน

## ผลกระทบที่ต้องแจ้งผู้ใช้

- Legacy-only staff ต้องผ่านกระบวนการย้ายบัญชีที่ตรวจสอบได้ก่อน login
- Public staff signup ใช้งานไม่ได้โดยตั้งใจ
- เปลี่ยนอีเมล login เองไม่ได้ ต้องผ่านผู้ดูแล
- คง JWT storage เดิม ไม่ใช่ session/refresh revocation redesign
- ต้อง frontend/backend rollout พร้อมกัน ไม่สลับไปใช้ code เก่าที่เปิด auto-promotion

## ไฟล์

backend/accounts/{views,throttles,checks,apps}.py; backend/config/settings.py
backend/patients/management/commands/audit_staff_provisioning.py
backend/patients/tests_staff_account_security.py และ tests_account_identity_security.py
frontend doctor login/register/settings/layout และ utils/api/services.ts

## ผลตรวจ

Selected combined backend regression 259 tests ผ่านบน SQLite :memory:
รวม unique email, inactive/nonstaff, no legacy query/logging, no self-elevation,
profile immutability, read-only inventory, account/IP throttle, cache failure และ deployment checks
ยังต้อง production account review, shared-cache concurrency และ PostgreSQL staging
