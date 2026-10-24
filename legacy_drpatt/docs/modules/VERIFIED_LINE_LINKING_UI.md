# Module: Verified LINE linking UI and proxy

## ทำอะไร

- หน้า /liff/identity ใช้ shared LiffProvider แทน init ซ้ำ
- เปลี่ยน phone/profile assertions เป็น clinic JWT + password confirmation + liff.getAccessToken()
- checkbox ยืนยันเจตนาเชื่อม, ป้องกันกดซ้ำ, ล้าง password หลังจบ request, ไม่เก็บ LINE token
- login returnTo=line-link กลับหน้าเชื่อมด้วย fixed allowlist ไม่รับ arbitrary redirect URL
- แสดงผลสำเร็จ ก่อนให้กดปิดกลับ LINE เฉพาะ isInClient; browser ปกติกลับ dashboard ได้
- มีข้อความ token expired, conflict, login required และ provider unavailable
- Provider รองรับ NEXT_PUBLIC_LIFF_ID หรือชื่อเดิม NEXT_PUBLIC_LINE_LIFF_ID

## Proxy

POST /api/liff/identity ใช้ Authorization จากผู้เรียกและส่งเฉพาะ password/access_token
ไป /api/line/verified-link/ ไม่ใช้ legacy linking endpoint
BACKEND_API_URL หรือ NEXT_PUBLIC_API_URL รองรับทั้ง origin และ suffix /api/
ต้อง HTTPS ยกเว้น localhost; ปฏิเสธ URL ที่มี credentials/query/hash
no-store, timeout, ไม่ตาม redirect, ไม่ส่ง exception/HTML/extra backend payload กลับ browser
ไม่ fallback production origin หากไม่ตั้ง configuration

## ทำไมถึงทำแบบนี้

ทางเลือกส่ง lineUserId/phone ไม่พิสูจน์เจ้าของบัญชี
จึงเลือก proof จาก LINE พร้อมยืนยันบัญชีคลินิกตาม backend contract ใหม่
การเชื่อมสำเร็จไม่ได้อนุมัติรายงานหรือรักษาอัตโนมัติ
ไม่ปิดหน้าต่างทันทีเพื่อให้ผู้ใช้เห็นผลสำเร็จและมีทางกลับเมื่อใช้ browser ภายนอก

## ไฟล์

- frontend/src/app/liff/identity/page.tsx
- frontend/src/app/api/liff/identity/route.ts
- frontend/src/components/providers/LiffProvider.tsx
- frontend/src/app/patient/login/page.tsx
- frontend/tests/verified-line-route.test.cjs

## ผลตรวจ 18 October 2026

- node --test tests/verified-line-route.test.cjs: 7 tests ผ่าน; fetch เป็น mock ทั้งหมด
- eslint เฉพาะ identity/page.tsx และ identity/route.ts: exit 0
- tsc --noEmit --incremental false: exit 2 เพราะ precision-report/page.tsx implicit any
  และ lib/axis-definitions.ts modules_by_context type mismatch; ไม่มี error ระบุไฟล์ linking ที่แก้
- ยังไม่ได้ browser visual QA, LIFF real-device E2E หรือ production build ที่สำเร็จ
- ไม่ได้ deploy/push หรือรัน production migration

## งานค้างก่อนใช้จริง

backend migration 0029, LINE_LOGIN_CHANNEL_ID, LIFF profile scope และ provider/channel alignment
ต้องตรวจใน staging ด้วยบัญชีทดสอบจริงก่อน deploy
registration/legacy activation screens ยังต้องปรับตาม security changes ก่อนหน้านี้
อัปเดต 19 October 2026: ปรับ screens แล้ว และ full TypeScript ผ่าน
ดู REGISTRATION_LINKING_UX.md; ยังต้อง LINE/staging E2E และ verified recovery flow
clinic JWT ยังใช้ storage pattern เดิมของแอป; ไม่ได้ย้าย authentication เป็น HttpOnly cookies ในงานนี้
rate limiting, consent audit และ account-switch/expiry E2E ยังต้องทดสอบเพิ่ม
