# Browser acceptance — 19 October 2026

## ขอบเขตที่ทดสอบจริง

ใช้ Next.js dev server localhost:3117 + Chrome headless โปรไฟล์ใหม่ผ่าน Playwright
API localhost:8912 เป็น route mocks ทั้งหมด; ทุก external browser request ถูก abort
ไม่มี patient/doctor credential จริง, ไม่มี backend/LINE production request
จึงเป็น UI integration acceptance ไม่ใช่ end-to-end กับฐานข้อมูล/LINE จริง

8 scenarios ผ่าน (node:test รายงาน 9 tests เมื่อนับ parent test):

1. ค้นผู้ป่วย เลือก exact artifact และดู evidence table รวม value=0
2. Readiness ไม่เปิดสิทธิ์ส่ง
3. จำลอง server บันทึกแล้ว response หาย; retry ใช้ UUID เดิม ไม่เกิด event ซ้ำใน mock
4. Wrong-snapshot history ไม่เปิดฟอร์มตรวจ
5. 401 หลังเปิดร่างล้างข้อมูลผู้ป่วย/feedback
6. Mobile 390×844: sidebar ปิด, content width >300px, ไม่มี horizontal overflow
7. เปลี่ยนบัญชีในแท็บอื่นล้างร่างและเหตุผลที่ยังไม่ส่ง
8. Late search response หลัง logout ไม่คืนข้อมูลเก่าเข้าหน้า

ตรวจ screenshot mobile ด้วยตาแล้ว (synthetic data เท่านั้น)
พบ accessible name ของ select ปะปนกับ options และแก้ aria-label ก่อน rerun ผ่าน

## รันซ้ำ

ต้องมี Playwright + Chromium/Chrome อยู่แล้ว ไม่มี auto-download/install ในชุดนี้
จาก frontend เปิด server เฉพาะ local ด้วย env จำลอง:

```sh
NEXT_PUBLIC_API_URL=http://127.0.0.1:8912 NEXT_PUBLIC_LIFF_ID= NEXT_PUBLIC_LINE_LIFF_ID= ./node_modules/.bin/next dev --hostname 127.0.0.1 --port 3117 --webpack
```

อีก terminal ใช้ `node --test tests/artifact-review.browser.cjs`
ตั้ง NODE_PATH ไปยัง Playwright ที่ติดตั้งหากไม่ได้อยู่ใน project node_modules
ตั้ง REVIEW_TEST_CHROME เป็น executablePath ของ Chrome หากไม่ใช้ browser ที่ Playwright จัดการ
REVIEW_TEST_ORIGIN จำกัด localhost/127.0.0.1; REVIEW_TEST_SCREENSHOT เลือก output screenshot ได้
ควรหยุด dev server หลังจบ ไม่ใช้การตั้งค่า mock เป็น deployment configuration

## สิ่งที่ยังไม่ผ่าน acceptance จริง

PostgreSQL locking/concurrency, shared-cache login limits, LINE real device,
trusted physician verification/signoff และ actual report delivery
ยังไม่ได้ production build หรือ requirement-to-test mapping ครบ specification ทั้งหมด
Frontend unit/contract/source guards 27 tests เป็นคนละชุดกับ browser 8 scenarios
