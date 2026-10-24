# Module: EP0 — Audit & Test Case Baseline

## ทำอะไร
ทำการสำรวจสถานะซอร์สโค้ดปัจจุบัน เปรียบเทียบกับข้อกำหนด Final Core Correction 25 ข้อ (P0/Core Invariants) รวมถึงตรวจสอบโครงสร้าง Migrations, สถาปัตยกรรมเส้นทางการสร้างรายงาน และจัดเตรียมชุดเคสทดสอบมาตรฐาน (Test Fixtures & Baseline Cases) สำหรับใช้ในการตรวจรับใน EP1–EP8

---

## สรุปรายการตรวจสอบ 25 ข้อ (P0 Audit Baseline)

| ข้อที่ | หัวข้อ | สถานะปัจจุบันใน Codebase | ไฟล์ที่รับผิดชอบหลัก | วิธีการทดสอบ / Test Case |
|---|---|---|---|---|
| **P0-1** | Identity Hard Gate | มี `validate_patient_identity()` บล็อกหาก HN/Age/Sex ขัดแย้ง | [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L222) | `IdentityConflictGateTests` ใน `tests.py` |
| **P0-2** | Single Ledger | `AnalysisRecord.ledger` ถูกใช้อ้างอิงร่วมกัน | [models.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/models.py#L156) | `AnalysisRecordProvenanceTests` |
| **P0-3** | Approval State Machine | มี `AnalysisReportRelease` รองรับ 4 สถานะ | [models.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/models.py#L203) | `ReportApprovalStateTests` |
| **P0-4** | Scoring Rule ID | มี `scoring_contracts` ตรวจสอบกฎคะแนน | [models.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/models.py#L227) | `ScoringContractGateTests` |
| **P0-5** | HYPOTHESIS Score = null | มีการล็อก `severity_score = null` สำหรับ HYPOTHESIS axes | [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L98) | `TspiEngineHypothesisTests` |
| **P0-6** | Canonical 12 Domains | ล็อก `SYSTEM_DOMAINS` ตรงตาม Master Registry | [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L61) | `TspiEngineDomainTests` |
| **P0-7** | Canonical 39 Axis Names | ล็อก `OFFICIAL_39_AXES` ตรงตาม Master Registry | [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L5) | `ValidateAnalysisRecordTests` |
| **P0-8** | Canonical 9 Steps | ล็อก `OFFICIAL_9_STEPS` คงลำดับและชื่อ Canonical | [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L47) | `TspiEngineNineStepsTests` |
| **P0-9** | Data Availability vs Score | แยกชั้น `Data Availability` ออกจาก `Score Availability` | [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L115) | `BaselineDataAvailabilityTests` |
| **P0-10** | DERIVED Label | กำหนดคะแนนคำนวณเป็น `DERIVED` ทุกจุด | [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L125) | `TspiEngineThreeKeysTests` |
| **P0-11** | Remove Confidence % | ถอดตัวเลข % ปรับใช้ Qualitative (`HIGH`, `MODERATE` ฯลฯ) | [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py) | `ConfidenceRuleTests` |
| **P0-12** | Separate Lab Critical | แยก `LAB_CRITICAL_VALUE` ออกจาก `TSPI_SEVERITY_BAND` | [models.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/models.py#L425) | `LabCriticalValueTests` |
| **P0-13** | TSPI Severity Taxonomy | ใช้เกณฑ์ Optimal / Subclinical / Functional / Pathological | [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py) | `SeverityTaxonomyTests` |
| **P0-14** | Module Fail Closed | หาก `approved_modules = 0` ซ่อน Module Clinical Section | [models.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/models.py#L244) | `ModuleRegistryApprovalEndpointTests` |
| **P0-15** | Clean Patient Tags | ซ่อน Debug Tags เช่น `[MEASURED]` ใน Patient Edition | `frontend/src/app/patient/` | `PatientViewRendererTests` |
| **P0-16** | Patient Wording | เปลี่ยนข้อความหัวข้อหากสถานะยังไม่อนุมัติโดยแพทย์ | `frontend/src/app/patient/` | `PatientApprovalWordingTests` |
| **P0-17** | Prevent Over-inference | ปรับประโยคสื่อสารเรื่อง WBC/Platelet | `frontend/src/app/patient/` | `PatientInferenceWordingTests` |
| **P0-18** | Iron Safety HOLD | กำหนด `status = HOLD_PENDING_CONFIRMATION` | [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py) | `SafetyLayer1Tests` |
| **P0-19** | Omics Utility Gate | ใช้ 12-field utility gate บล็อกหาก management change = LOW | [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L395) | `OmicsUtilityGateTests` |
| **P0-20** | Omics Not Prerequisite | ปรับ UI/Engine ไม่ให้มอง Omics เป็นเงื่อนไขจำเป็นในการทำ TSPI | `frontend/src/app/doctor/` | `OmicsPrerequisiteTests` |
| **P0-21** | Thalassemia Flow | ลำดับการสั่งตรวจซีด: Standard → Iron/Hb typing → Genetic | [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py) | `ThalassemiaWorkupFlowTests` |
| **P0-22** | MASH Terminology | แก้ชื่อเป็น Metabolic dysfunction-associated steatohepatitis | `frontend/`, `data/` | `TerminologyCheckTests` |
| **P0-23** | Disease Layer Wording | ปรับถ้อยคำชีววิทยา ไม่กล่าวว่าเป็นสาเหตุเดี่ยว | `frontend/`, `views_ai.py` | `DiseaseLayerWordingTests` |
| **P0-24** | Cross-Report Invariants | ตรวจสอบข้อมูลตรงกันทุก View ก่อนสร้าง PDF | [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L211) | `ValidateAnalysisRecordTests` |
| **P0-25** | Complete Artifact Bundle | ชุดไฟล์ส่งตรวจรับ (PDF 3 ฉบับ, AnalysisRecord JSON ฯลฯ) | Backend exporters | `ArtifactBundleTests` |

---

## ชุดเคสทดสอบมาตรฐาน (Baseline Test Fixtures)

สำหรับการทดสอบใน EP1–EP8 มีการจัดเตรียม 3 เคสหลัก:
1. **Case A (Fully Verified & Complete):**
   - มีข้อมูล HN, Sex, DOB, Labs ครบถ้วน
   - ไม่มี Identity conflict
   - ผลการทดสอบ: สามารถสร้าง `AnalysisRecord` และออกรายงานทั้ง 3 ฉบับได้อย่างสมบูรณ์
2. **Case B (Identity Conflict Case):**
   - ข้อมูล HN ในเวชระเบียนหลัก ไม่ตรงกับ Owner HN ของแล็บ
   - ผลการทดสอบ: Identity Gate สั่งเปลี่ยนสถานะเป็น `CONFLICT` และบล็อกการประเมินผล (`BLOCKED_DATA_RECONCILIATION`)
3. **Case C (Unapproved Rule & Missing Evidence):**
   - ข้อมูลแล็บไม่ครบ และแกนชีวภาพไม่มี `scoring_rule_id` ที่ได้รับการอนุมัติ
   - ผลการทดสอบ: `score_status = NO_APPROVED_SCORING_RULE`, `severity_score = null`, `severity_band = null`

---

## จุดที่ต้องระวัง
- ห้ามรันคำสั่ง Terminal โดยอัตโนมัติ ให้แจ้งคำสั่งให้ User ตรวจสอบและรันเองตามกฎ 5.3
- ในการสร้างรายงาน ต้องมั่นใจว่าทุก View ดึงข้อมูลจาก `AnalysisRecord.ledger` เดียวกันเท่านั้น

---

## อ้างอิง
- เอกสาร Final Core Correction Request (22.09.2026)
- [models.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/models.py)
- [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py)
- [tests.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tests.py)
