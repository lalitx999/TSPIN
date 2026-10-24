# Module: Review session isolation

## ทำอะไร

หน้าตรวจร่างฟัง storage/focus/pageshow/visibilitychange
เมื่อ doctor token เปลี่ยน ล้างผู้ป่วย ร่าง ประวัติ ข้อความตรวจ และ pending request key
ใช้ generation counter ปฏิเสธ response เก่าที่กลับมาหลังเปลี่ยน session
รวมกรณีบัญชี A ไป B แล้วกลับ A ไม่อาศัยเทียบ token อย่างเดียว
ผลตรวจ readiness ถูก unmount พร้อมร่าง; คำขอเก่าไม่สามารถแทนที่ session ใหม่

## ทำไมถึงทำแบบนี้

ทางเลือกเทียบ token หลัง fetch อย่างเดียวไม่ครอบคลุม A→B→A
จึงใช้ generation เพิ่มพร้อมล้าง state และกัน finally/catch เก่าทับสถานะคำขอใหม่
ไม่เปลี่ยน server authorization หรือรูปแบบ JWT storage ของแอป

## ไฟล์

- frontend/src/lib/review-session-guard.ts
- frontend/src/app/doctor/artifact-review/page.tsx
- frontend/tests/review-session-guard.test.cjs

## ขอบเขตและผลตรวจ

Unit/contract/source-guard frontend suite 27 tests ผ่าน รวม async deferred-response test
ยังไม่ใช่ browser multi-tab E2E; storage event ขึ้นกับ browser scheduling
การเปลี่ยน localStorage ในแท็บเดียวไม่มี storage event ต้องตรวจเมื่อ focus/visibility/request
ยังไม่ได้ immediate same-tab auth event integration ทั่วแอป
ไม่มี abort รับประกันยกเลิก POST ที่ server รับไปแล้ว; response ถูกทิ้งได้แต่ write อาจสำเร็จ
ต้องตรวจประวัติก่อนส่งซ้ำ และ migration 0031 สำหรับ request idempotency
ไม่มี production migration/push/deploy
