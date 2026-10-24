# Module: EP1 Canonical Knowledge & Data Ontology Governance

## ทำอะไร
- ล็อกโครงสร้าง Canonical Ontology (3 Keys, 9 Restoration Steps, 12 Domains, 39 Axes, 180 Living Networks)
- บังคับใช้ Strict Missing Data Rules (`NOT_ASSESSED`, `INSUFFICIENT_DATA`, `REQUIRES_ADDITIONAL_INFORMATION`)
- ป้องกัน HYPOTHESIS axes ไม่ให้ถูกนำไปคำนวณคะแนนความรุนแรง (`severity_score = None`)
- บังคับใช้กฎ INV-015 (Axis severity score ต้องมีสถานะเป็น `DERIVED` เท่านั้น ห้ามเป็น `MEASURED`)
- ป้องกันการหลุดใช้คำว่า `NOT_AVAILABLE` เมื่อมีข้อมูลแล็บจริงแต่ยังไม่มีสูตรคะแนนอนุมัติ (`NO_APPROVED_SCORING_RULE`)

## ทำไมถึงทำแบบนี้
- เพื่อทำตาม Directive ข้อ 3, 4, 6, 7 ในจดหมายควบคุมขอบเขต AI และป้องกัน Hallucination
- ป้องกันไม่ให้ Generative AI สถาปนา Axis ใหม่ (เช่น AXIS_40), ย้ายหมวด, หรือแอบเติมค่าคะแนนเดาเมื่อข้อมูลแล็บขาดหายไป

## โครงสร้างไฟล์
- `backend/patients/tspi_engine.py`: เก็บ Constants `OFFICIAL_39_AXES`, `OFFICIAL_9_STEPS`, `SYSTEM_DOMAINS`, `HYPOTHESIS_AXES`, `CLINICAL_INFERENCE_AXES`, `EVIDENCE_PRESENT_NO_SCORING_RULE_AXES`
- `backend/patients/tests.py`: ชุดทดสอบ `TspiEngineHypothesisTests` และ `ValidateAnalysisRecordTests`

## จุดที่ต้องระวัง
- หากในอนาคตมีการเพิ่มหรือแก้ไขสูตรคะแนน Axis ต้องผ่านการอนุมัติใน Registry ก่อน ห้ามแก้ไข Constants เหล่านี้โดยตรง
- Missing Data ห้ามเปลี่ยนเป็นค่าประมาณหรือคะแนน 0

## อ้างอิง
- Directive 3, 4, 6, 7 (AI Scope Control Architecture Oct 2026)
- TSPI Master Canonical Registry (30 Sep 2026)
