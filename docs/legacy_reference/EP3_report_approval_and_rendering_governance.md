# EP3 — Report Approval State Machine & Rendering Governance (30 Sep 2026)

## ทำอะไร
- ปรับปรุง `markdown_to_html` ใน `views_ai.py` ให้รับ parameter `edition` และ `is_approved`
- ใน **Patient Edition**: ซ่อน Tag Debug ภายในทั้งหมด (`[MEASURED]`, `[DERIVED]`, `[HYPOTHESIS]`, `[CLINICAL_INFERENCE]`, `[NOT_AVAILABLE]`, `[AI_SUGGESTED_CONSIDERATION]`, `[PHYSICIAN_APPROVED_RECOMMENDATION]`) แปลงเป็นภาษาธรรมชาติภาษาไทย เช่น `(ผลตรวจยืนยัน)`, `(สภาวะสงสัย — รอตรวจเพิ่มเติม)`
- แก้ไขข้อความขัดแย้งเรื่องการอนุมัติ (P0-11): หากรายงานยังไม่ได้รับการอนุมัติจากแพทย์ จะเปลี่ยนข้อความ *"แผนดูแลสุขภาพที่แพทย์อนุมัติแล้ว"* เป็น *"ร่างแผนดูแลสุขภาพที่อยู่ระหว่างการพิจารณาของแพทย์"* โดยอัตโนมัติ
- เพิ่ม Cross-Report Invariant Rules ใหม่ใน Engine:
  - **INV-013**: ตรวจจับและสั่ง `BUILD_FAIL` หากรายงานอยู่ในสถานะ `AI_DRAFT` แต่มีข้อความอ้างว่าแพทย์อนุมัติแล้ว
  - **INV-014**: ตรวจจับและสั่ง `BUILD_FAIL` หาก Module Registry ยังไม่อนุมัติ (`approved_modules == 0`) แต่กลับมีรายการใน `recommended_modules_clinical`

## ทำไมถึงทำแบบนี้
- เอกสาร P0-9 ถึง P0-12 กำหนดว่า Patient Report ต้องไม่มี Tag ภายในของ Engine หลุดออกไปให้คนไข้เห็น และรายงานที่ยังไม่อนุมัติห้ามหลอกลวงคนไข้ว่าเป็นแผนที่แพทย์อนุมัติแล้ว

## โครงสร้างไฟล์ที่แก้ไข
| ไฟล์ | การเปลี่ยนแปลง |
|------|----------------|
| `backend/patients/views_ai.py` | อัปเดต `markdown_to_html` เพิ่ม `edition` & `is_approved`, ซ่อน Tag ใน Patient view และปรับแก้ `generate_report_pdf_view` ให้ส่ง edition เข้าไป |
| `backend/patients/tspi_engine.py` | เพิ่มกฎ INV-013 และ INV-014 ใน `validate_analysis_record()` |
| `backend/patients/tests.py` | เพิ่ม 5 Test Cases (PatientRenderingGovernanceTests, InvariantINV013014Tests) |

## ผลการทดสอบ
- **Ran 64 tests in 1.842s — OK** (ผ่านทั้ง 64 เคส)

## Invariant Rules ใหม่
| Rule ID | สิ่งที่ตรวจ | ผลลัพธ์เมื่อพบข้อขัดแย้ง |
|---------|-----------|-------------------------|
| INV-013 | ข้อความ "อนุมัติแล้ว" ปรากฏในรายงานสถานะ `AI_DRAFT` | BUILD_FAIL |
| INV-014 | `recommended_modules_clinical` ไม่เป็นค่าว่างเมื่อ `approved_modules == 0` | BUILD_FAIL |

## อ้างอิง
- FINAL CORE CORRECTION REQUEST (TSPI Clinical Intelligence Engine) ลงวันที่ 30 Sep 2026
- Section P0-9, P0-10, P0-11, P0-12
