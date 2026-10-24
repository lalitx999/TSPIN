# EP4 — Scoring Contract Registry

`AxisScoringContract` เก็บ axis code, rule ID, version, threshold specification, approval status, ผู้อนุมัติ และวันอนุมัติ โดยไม่มี seeded contract ที่แต่งขึ้นเอง

ทุก AnalysisRecord เก็บ snapshot ของ contract ที่ครอบคลุม numeric scores. หากมี score ที่ contract เป็น `MISSING`, `DRAFT`, `PENDING_APPROVAL` หรือ `RETIRED` ระบบจะไม่อนุญาต transition ไป `PATIENT_RELEASED`.

## สิ่งที่ต้องขอจากแพทย์

สำหรับแต่ละ axis ที่ต้องการเปิด numeric score: axis code, rule/threshold, version, ชื่อผู้อนุมัติ, วันที่อนุมัติ และหลักฐานที่ใช้รองรับ rule.

Migration R0: `0019_axis_scoring_contract.py`
