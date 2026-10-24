# Module: LINE webhook authentication

## ทำอะไร

ตรวจ HMAC-SHA256 ของ raw request bytes ก่อน decode/parse หรือเข้า event handler
เปรียบเทียบด้วย compare_digest และไม่มี DEBUG bypass

- missing/invalid/non-ASCII signature: 401
- ไม่ตั้ง Channel Secret ฝั่งเซิร์ฟเวอร์: 503
- signed payload ที่ encoding/JSON/events shape ผิด: 400
- signed empty events probe: 200

## ทำไมถึงทำแบบนี้

ทางเลือกเดิมตรวจเฉพาะเมื่อ signature และ secret มีค่า ทำให้ไม่มี signature ก็ผ่านได้
จึงเลือก fail closed ทุก environment แทน bypass เพื่อความสะดวกในการพัฒนา
ข้อแลกเปลี่ยน: local/webhook tests ต้องลงลายเซ็น และ environment ที่ขาด secret จะไม่รับ events
ก่อน deploy ต้องตรวจ LINE_DOCTORPATT_CHANNEL_SECRET หรือ LINE_CHANNEL_SECRET ให้ตรง channel
ห้ามใส่ secret ลง repository/logs

## โครงสร้างไฟล์

- backend/patients/views_line.py: exact-byte verification, constant-time compare, payload validation
- backend/patients/tests_line_webhook_security.py: 5 tests รวม DEBUG/production cases
- backend/patients/tests.py: unsigned rebinding regression ยืนยันว่า LINE binding ทั้งสองบัญชีไม่เปลี่ยน

## ทดสอบ

mock network และ reply, ตรวจว่าคำขอปลอมไม่เรียก patient lookup
ทดสอบ body เปลี่ยน, missing/non-ASCII signature, missing secret, malformed encoding/JSON/events
ทดสอบ signed dashboard branches ร่วมกับ tests_analysis_delivery
ไม่มีการเรียก LINE จริงหรือแก้ข้อมูล production
18 October 2026: ชุดรวม 193 tests ผ่านบน SQLite :memory: (exit 0)

## ขอบเขตที่ยังไม่ครบ

ลายเซ็นยืนยันว่า request มาจาก channel ไม่ได้พิสูจน์เจ้าของเลขบัตรประชาชน
ยังต้องตรวจ account linking, duplicate LINE identity, replay/event deduplication,
event-specific payload validation และ free-form AI output gates
ไม่ถือว่า EP8/EP9 ครบ และไม่มี deploy/push
