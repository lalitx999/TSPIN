# สรุปชุดงาน 19 October 2026

## สิ่งที่ปิดได้ในรอบนี้

- ช่อง public staff signup / legacy login auto-promotion ปิดแล้วในโค้ด
- Staff profile ไม่เปลี่ยน identity/privileges ผ่าน payload
- Staff login มี account/IP fixed-window limit + deploy check + outage tests
- เครื่องมือ read-only inventory สำหรับตรวจบัญชีเจ้าหน้าที่เดิม
- Notification token binding ไม่อิง shared email หรือ ambiguous patient
- หน้าตรวจร่างผ่าน Chrome UI integration 8 scenarios รวม mobile/session/retry
- UI access-denied ล้าง state และ accessible select labels แก้แล้ว

## หลักฐาน

- Backend selected regression: 259 tests, SQLite test DB
- Frontend unit/contract/source guards: 27 tests
- Browser: 8 scenarios + parent (9 tests), mocked APIs
- Full TypeScript: ผ่าน
- Targeted ESLint: ไม่มี errors; legacy doctor login มี img/unused warning เดิม

## ยังไม่ใช่จบทั้งระบบ

1. Trusted physician verification และ signed clinical approval จริง
2. Clinical adapters/policies ที่ขาด + consent/recipient/safety delivery integration
3. Verified account recovery/activation และ broader auth/session/rate-limit work
4. PostgreSQL/shared cache/LINE staging, complete requirements mapping และ production build

เรื่องที่ต้องให้คลินิกตัดสินใจยังอยู่ใน AGENTIC_REMAINING_WORK.md
รายการนี้ไม่เปลี่ยนงานค้างเหล่านั้นเป็น completed เพราะมี test เพิ่ม

## ก่อน deploy

อ่าน STAFF_AUTH_SECURITY.md เรื่อง legacy staff และบัญชีเก่าที่อาจเคยสมัครสาธารณะ
ผู้ใช้ review, สำรองข้อมูล, เตรียม staging, ตรวจ migrations 0029–0031 และ shared cache
ตรวจ environment จริงรวม DEBUG/SECRET_KEY/ALLOWED_HOSTS และ trusted proxy
ไม่มี production migration, account mutation, push หรือ deploy ในรอบนี้
