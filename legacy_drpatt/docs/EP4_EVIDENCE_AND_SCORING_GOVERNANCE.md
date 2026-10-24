# Module: EP4 — Evidence และ Scoring Governance

## ทำอะไร
กำหนดโครงสร้างและกฎควบคุมการให้คะแนนชีวภาพ (Scoring Governance) อย่างเคร่งครัด:
1. **แยก 4 Layers:** Data Availability / Evidence Status / Assessment Status / Score Status
2. **HYPOTHESIS Axes Score Lock:** แกนชีวภาพที่เป็นเพียงสมมติฐานหรือขาดผลตรวจยืนยันสายตรง (A8, A16, A17, A19, A25, A28, A30, A34) จะต้องถูกกำหนด `severity_score = null`, `severity_band = null` และไม่นำไปรวมในคะแนน NSS หรือจับคู่ Module
3. **Approved Rule Enforcement:** หากไม่มี `scoring_rule_id` ที่ผ่านการอนุมัติ คะแนนจะถูกกำหนดเป็น `NO_APPROVED_SCORING_RULE` และ `severity_score = null`
4. **Remove Unvalidated Confidence %:** ยกเลิกการแสดงค่าเปอร์เซ็นต์ความเชื่อมั่นที่ไม่มีสูตรรับรอง ให้ใช้ระดับคุณภาพ (`VERY_HIGH`, `HIGH`, `MODERATE` ฯลฯ) แทน

---

## ทำไมถึงทำแบบนี้
1. **ป้องกัน Pseudo-Precision (ความแม่นยำลวง):** ป้องกันไม่ให้ระบบสร้างตัวเลขคะแนน 0-100 ขึ้นมาจากข้อมูลที่ไม่สมบูรณ์หรือจากสมมติฐาน
2. **การเมืองเรื่องธรรมาภิบาลข้อมูลการแพทย์:** การมีคะแนนตัวเลขต้องรับรองด้วยสูตรการคำนวณและเวอร์ชันของกฎที่มีแพทย์ลงนามเท่านั้น (`AxisScoringContract`)

---

## โครงสร้างไฟล์
- `backend/patients/tspi_engine.py`: [HYPOTHESIS_AXES](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L98), [CLINICAL_INFERENCE_AXES](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L113), [EVIDENCE_PRESENT_NO_SCORING_RULE_AXES](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L121)
- `backend/patients/models.py`: [AxisScoringContract](file:///Users/tanchonl/Downloads/drpatt/backend/patients/models.py#L227)
- `backend/patients/tests.py`: `EvidenceScoringGovernanceTests`

---

## จุดที่ต้องระวัง
- ห้ามให้ LLM สร้างคะแนนตัวเลขแกนชีวภาพขึ้นเอง ข้อมูลตัวเลขทั้งหมดต้องมาจากคำสั่งคำนวณ Deterministic ของ Engine เท่านั้น
- Evidence Exists ≠ Numeric Score Available (มีหลักฐาน ไม่ได้แปลว่าต้องมีคะแนนตัวเลข)

---

## อ้างอิง
- เอกสารเกณฑ์ตรวจรับ EP4 (รอบแก้ 22.09.2026)
- [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py)
