# งานหลักที่เหลือ ณ 19 October 2026

ไม่ใช่ production-ready และไม่ตีเป็นเปอร์เซ็นต์จากจำนวนไฟล์หรือจำนวน tests

## 1. การยืนยันแพทย์และการลงนามจริง

- preflight มีแล้ว แต่ยังไม่มี trusted credential verification/revocation source
- ต้อง persisted signed approval ผูก exact artifact, ผู้ลงนาม, เวลา, เหตุผล และ audit
- ต้องมี reauthentication/authorization และ lifecycle เพิกถอนที่ตรวจย้อนหลังได้
- รอคลินิกกำหนดผู้มีอำนาจยืนยันใบอนุญาต แหล่งตรวจ และรอบตรวจซ้ำ

## 2. Clinical workflow และ delivery integration

- orchestrator มีโครงสร้าง แต่บางบทบาทยังไม่มี adapter จริง เช่น clinical logic
- review UI/feedback ไม่ทดแทน clinical review, independent audit หรือ physician signature
- ต้องเชื่อม clinical policies/formulas ที่ผู้รับผิดชอบอนุมัติ ไม่สร้างเกณฑ์แพทย์ขึ้นเอง
- ต้อง current consent, verified recipient/channel, fresh safety/input recheck ก่อนส่ง
- ต้องทำให้ PDF/LINE/ช่องทางอ่านข้อมูลใช้เงื่อนไขเดียวกันโดยไม่เปิด legacy bypass
- account recovery/activation แบบ verified, rate limiting และ security audit ยังมีงาน

## 3. Acceptance และ rollout

- browser E2E: เลือกคน/ฉบับ เปลี่ยนบัญชี สิทธิ์หมดอายุ เน็ตหลุด retry และ malformed responses
- LINE จริง: channel/LIFF configuration, account switching และ token expiry
- PostgreSQL staging: migrations, concurrent writes/locks และ rollback plan
- ตรวจ requirement-to-test mapping เทียบ specification เต็ม ไม่ถือ selected tests เป็น coverage ทั้งระบบ
- ผู้ใช้ review, migration, push/deploy เองตามกฎโครงการ

## สิ่งที่ขอจากคลินิกได้ตอนนี้

1. ใครมีอำนาจตรวจและรับรองบัญชีแพทย์ ใช้หลักฐานจากแหล่งใด และต้องทบทวนเมื่อใด
2. ใครมีสิทธิ์ลงนามรายงานแต่ละประเภท และขั้นตอนเพิกถอน/แก้ไขหลังอนุมัติ
3. เกณฑ์ทางคลินิกฉบับที่อนุมัติแล้ว พร้อมเวอร์ชัน/ผู้รับผิดชอบ และกรณีทดสอบที่คาดหวัง
4. ขอบเขตความยินยอมและช่องทางส่งรายงานที่คลินิกอนุญาต

รายการนี้เป็นงานค้างที่ยืนยันจากโค้ดปัจจุบัน ไม่ใช่คำรับรองว่าไม่มีช่องว่างอื่น
