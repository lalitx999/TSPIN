# Module: EP5 Claim-Level Provenance & Post-LLM Output Validator

## ทำอะไร
- บังคับใช้ Claim-Level Provenance: ข้อความคลินิกทุกบรรทัดต้องสามารถสืบย้อน (Trace) ไปยัง Patient Data ID, Rule ID, Evidence ID, Axis ID และ Registry Version ได้
- สร้างและเชื่อมต่อ `ClinicalOutputValidator` เข้ากับกระบวนการ `markdown_to_html()` โดยอัตโนมัติ
- บังคับใช้ด่านตรวจจับ 6 ข้อหลัง LLM เรียบเรียง:
  1. VAL-001: ปฏิเสธข้อความที่มี Axis/Domain ปลอม (เช่น Axis 40+)
  2. VAL-002: แก้ไขข้อความที่แอบให้คะแนนใน Axis ที่ยังไม่ได้ประเมิน
  3. VAL-003: แก้ไขข้อความที่แนะนำสูตรสมุนไพรขณะที่ `approved_modules == 0`
  4. VAL-004: แก้ไขข้อความแอบอ้างการอนุมัติในรายงานที่เป็น `AI_DRAFT`
  5. VAL-005: แก้ไขข้อความแบนเนื้อแดง/อาหารธรรมชาติเรื่องธาตุเหล็ก
  6. Patient Tags Cleansing: ล้างแท็กวงเล็บเหลี่ยม `[MEASURED]`, `[DERIVED]`, `[HYPOTHESIS]` ออกจาก Patient PDF 100%

## ทำไมถึงทำแบบนี้
- เพื่อทำตาม Directive ข้อ 10, 16, 18, 19 ในจดหมายควบคุมขอบเขต AI และสถาปัตยกรรมป้องกัน Hallucination
- เป็นด่านสุดท้าย (Final Guardrail) ที่รับประกันว่า Generative AI จะไม่มีวันส่งข้อความมโนขัดแย้งกับความจริงทางคลินิกหลุดออกไปในรายงาน PDF

## โครงสร้างไฟล์
- `backend/patients/output_validator.py`: คลาส `ClinicalOutputValidator` และฟังก์ชัน `validate()`
- `backend/patients/views_ai.py`: เรียกใช้งาน `ClinicalOutputValidator` ใน `markdown_to_html()`
- `backend/patients/tests_anti_hallucination.py`: ชุดทดสอบ Anti-Hallucination Directives 7 ข้อ

## จุดที่ต้องระวัง
- หาก LLM สุ่มสร้าง Axis ปลอมเกิน 39 ตัว ตรวจจับได้จะสั่ง `REJECT` ทั้งฉบับทันทีและคืนค่า `BLOCKED_BY_POLICY`
- ใน Patient Edition แท็กภาษาอังกฤษวงเล็บเหลี่ยมทั้งหมดจะถูก Regex สกัดออก 100%

## อ้างอิง
- Directive 10, 16, 18, 19 (AI Scope Control Architecture Oct 2026)
- TSPI E2E Golden Test Directives (30 Sep 2026)
