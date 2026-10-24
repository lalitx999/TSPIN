# Module: EP3 Hard Safety Gates & Machine-Readable Refusal Engine

## ทำอะไร
- บังคับใช้ Identity Hard Gate (INV-000): หากพบความขัดแย้งของข้อมูลอัตลักษณ์ (HN/อายุ/เพศ) สั่งบล็อกการสร้างรายงานคลินิกทั้งหมด และส่งกลับเฉพาะ `DATA_RECONCILIATION_REPORT`
- บังคับใช้ Hard Safety Gates สำหรับ Red Flags / Contraindications ตัดสายการประเมินทันที (ไม่ใช้การตัดคะแนน)
- กำหนด Machine-Readable Refusal States (`BLOCKED_BY_POLICY`, `INSUFFICIENT_APPROVED_INFORMATION`, `NOT_ASSESSED`, `REQUIRES_CLINICIAN_REVIEW`, `EMERGENCY_ESCALATION`)
- บังคับใช้หลักการ Default Fail-Closed: หากเจอข้อมูลขัดแย้ง ข้อมูลไม่ครบ หรือ Validation ไม่ผ่าน ต้องหยุดสรุปผลทันที

## ทำไมถึงทำแบบนี้
- เพื่อทำตาม Directive ข้อ 9, 12, 13, 20 ในจดหมายควบคุมขอบเขต AI และสถาปัตยกรรมป้องกัน Hallucination
- ป้องกันความเสี่ยงร้ายแรงทางคลินิกจากการสร้างรายงานในสภาวะที่มีข้อมูลขัดแย้ง หรือให้ LLM ตอบปฏิเสธด้วยภาษาธรรมชาติมโนเอง

## โครงสร้างไฟล์
- `backend/patients/views_ai.py`: ตรวจสอบ `identity_validation_status != 'VERIFIED'` และส่งกลับ HTTP 400 `DATA_RECONCILIATION_REPORT`
- `backend/patients/output_validator.py`: เก็บ Dictionary `REFUSAL_STATES` สำหรับ Machine-Readable Enum
- `backend/patients/tests_e2e_golden.py`: ชุดทดสอบ `test_e2e_004_identity_conflict_blocks_all_clinical_pdfs`

## จุดที่ต้องระวัง
- ห้าม bypass Identity Validation Gate ไม่ว่ากรณีใดๆ
- หากเกิด Emergency Escalation ต้องส่งต่อเข้ากระบวนการแพทย์เร่งด่วนทันที

## อ้างอิง
- Directive 9, 12, 13, 20 (AI Scope Control Architecture Oct 2026)
- TSPI Invariant Rule INV-000 (30 Sep 2026)
