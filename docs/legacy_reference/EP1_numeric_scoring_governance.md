# EP1 — Numeric Scoring Rules & Axis Governance (30 Sep 2026)

## ทำอะไร
- ปรับปรุง Core Engine ให้แยก **CLINICAL_INFERENCE axes** (A27 Glycation/Carbonyl Stress, A33 Thyroid-Adrenal-Growth) ออกจากการให้คะแนน — เนื่องจากข้อมูล confounded ต้องรอยืนยันด้วย current markers ก่อน
- ปรับ `score_status` ให้แยก `"SCORED"` (มี approved rule) vs `"NOT_SCORED_CONFOUNDED"` (confounded) vs `"NO_APPROVED_SCORING_RULE"` (มี evidence แต่ไม่มีสูตรคำนวณ)
- เพิ่ม `priority_derivation`, `priority_rule_id`, `rank_label` ให้ `system_priorities` ใน ledger — ใช้คำว่า "Highest Scored Assessed Axes" (ไม่ใช่ "Restoration Priority") จนกว่าจะมี approved rule จริง
- เพิ่ม Test Evidence Tiering (STANDARD_CLINICAL, CLINICALLY_ACTIONABLE_ADVANCED, OPTIONAL_ADVANCED, RESEARCH_ONLY)

## ทำไมถึงทำแบบนี้
- เอกสาร P0-7/P0-8 ระบุว่า A27 (glycation from disease history alone) และ A33 (thyroid-adrenal confounded by renal + critical illness) ต้องไม่มี numeric score
- P0-4 ระบุว่าห้ามเรียก Priority ว่า "Restoration Priority" จนกว่าจะมี approved priority rule
- ทุกอย่างต้อง trace กลับไปหา evidence และ scoring rule ได้ (P0-1)

## โครงสร้างไฟล์ที่แก้ไข
| ไฟล์ | การเปลี่ยนแปลง |
|------|----------------|
| `backend/patients/core_contracts.py` | เพิ่ม `clinical_inference_axes` parameter, แยก score gating, เพิ่ม TEST_EVIDENCE_TIERS |
| `backend/patients/tspi_engine.py` | ส่ง CLINICAL_INFERENCE_AXES ให้ classify_axis(), เพิ่ม INV-011/012, ปรับ candidate axes, เพิ่ม priority_derivation metadata |
| `backend/patients/tests.py` | เพิ่ม 10 test cases ใหม่ (ClinicalInferenceGatingTests, PriorityDerivationTests, InvariantINV011012Tests) |

## จุดที่ต้องระวัง
- `CLINICAL_INFERENCE_AXES = {27, 33}` เป็น hardcode set ใน `tspi_engine.py` — หากแพทย์อนุมัติ scoring rule ใหม่สำหรับ A27/A33 ต้องลบออกจาก set นี้
- รายงานเก่าที่สร้างจาก `AnalysisRecord` เดิมจะยังมี `score_status: "NO_APPROVED_SCORING_RULE"` สำหรับ A5 — ไม่กระทบเพราะ AnalysisRecord เป็น immutable snapshot

## ผลการทดสอบ
- **Ran 56 tests in 1.912s — OK** (ผ่านทั้ง 56 เคส, เพิ่มจาก 46 เป็น 56)

## Invariant Rules ใหม่
| Rule ID | เงื่อนไข | ผลลัพธ์ |
|---------|----------|---------|
| INV-011 | CLINICAL_INFERENCE axis มี severity_score != None | BUILD_FAIL |
| INV-012 | CLINICAL_INFERENCE axis มี eligible_for_priority = True | BUILD_FAIL |

## อ้างอิง
- FINAL CORE CORRECTION REQUEST (TSPI Clinical Intelligence Engine) ลงวันที่ 30 Sep 2026
- Section P0-1, P0-3, P0-4, P0-5, P0-7, P0-8, P0-13
