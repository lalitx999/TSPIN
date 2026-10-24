# Module: Raw analysis and LINE dashboard delivery

## ทำอะไร

- จำกัด tspi-analysis ledger ให้ clinical reviewers ตาม access policy เดิม
- LINE postback view_dashboard และข้อความ 39 แกน/แดชบอร์ด/dashboard
  ไม่คำนวณคะแนนสดหรือส่งผลวิเคราะห์อีก ส่งเฉพาะข้อความสถานะว่ายังไม่พร้อมเผยแพร่
- ไม่อ้างว่าแพทย์ได้รับแจ้ง ไม่ใส่ชื่อผู้ป่วยหรือ HN ในข้อความสถานะ

## ทำไมถึงทำแบบนี้

ทางเลือกซ่อนเฉพาะ PDF ยังเหลือ raw ledger และ dashboard ที่คำนวณจากข้อมูลปัจจุบัน
โดยไม่ผูกกับรายงานฉบับอนุมัติ จึงปิดสองเส้นทางนี้ก่อน
ข้อแลกเปลี่ยนคือ patient dashboard ใน LINE ยังไม่แสดงคะแนนจนมี trusted release integration
การซักประวัติส่วนอื่นยังไม่ได้เปลี่ยนในรอบนี้

## โครงสร้างไฟล์

- backend/patients/views.py: tspi-analysis access check
- backend/patients/views_line.py: pending dashboard notice และแทนสอง outbound branches
- backend/patients/tests_analysis_delivery.py: 3 synthetic API/webhook tests

## ผลทดสอบ

18 October 2026: 3 tests ผ่านบน SQLite :memory:
LINE reply mocked, urlopen ถูกบล็อก, assert ว่าไม่เรียก scoring engine
ไม่มีการส่ง LINE จริง ไม่มี production migration/deploy/push
ชุดรวมล่าสุด 187 tests ผ่าน (exit 0), Django system check ไม่พบปัญหา

## ยังต้องแก้ก่อนใช้งานจริง

- webhook signature bypass ถูกแก้ในรอบถัดมาแล้ว ดู LINE_WEBHOOK_AUTHENTICATION.md
  ยังต้องตรวจ replay protection และ event-specific payload validation
- ยังมี free-form AI intake responses, LLM scores และการผูก LINE identity ที่ต้อง audit
- ยังไม่ใช่ shared pre-send gate ครบทุกข้อความ/ช่องทาง
- biological record APIs, frontend caches และ legacy identity fixture ต้องตรวจต่อ
