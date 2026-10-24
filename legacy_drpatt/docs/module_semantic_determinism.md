# Module: Semantic Determinism & Analysis Record Pipeline

## ทำอะไร
- สร้าง Identity Validator Gate (`validate_patient_identity()`) เพื่อตรวจสอบข้อมูล demographics (อายุ, เพศ, HN) และ SOAP note ป้องกันการวิเคราะห์ข้อมูลข้ามคนไข้
- แก้ไข Semantic Evidence Classification ใน `tspi_engine.py`:
  - แยก `data_availability` (PRESENT) ออกจาก `score_status` (NO_APPROVED_SCORING_RULE) สำหรับ A35, A37, A38
  - บังคับการแมปพยาธิสภาพกระดูกเข้า A29 (Bone Remodeling) ห้ามแมปเข้า A30
  - แยก `known_disease_context` ออกจาก `current_severity` ใน A5/A27
  - กำหนด `score_derivation = DERIVED` สำหรับทุก Axis ที่คำนวณได้
- เพิ่มโครงสร้างฟิลด์ใหม่ใน Reasoning Ledger (`buildReasoningLedger` ใน `route.ts`): `identity_validation`, `care_goal_mode`, `respiratory_state`, `domain_mapping`
- อัปเดตกฎ Prompt Constitution (`TSPI_FUNDAMENTAL_MEDICINE_RULES`): ซ่อนชื่อ Module เมื่อ `approved_modules = 0`, ห้ามใช้ตัวเลข Confidence %, บังคับติดป้าย Clinical Action Labels, และกำหนด Omics เป็น Resolution layer
- ขยายกฎ Invariant Validator (`validateAnalysisRecord`) เพิ่ม INV-009 ถึง INV-014
- อัปเดต Patient Report QA Gate: ปรับถ้อยคำ Thalassemia Trait และตรวจเช็ค Release blockers

## ทำไมถึงทำแบบนี้
- ** Identity Conflict Gate**: หากข้อมูลคนไข้สับสน ข้อมูลทางคลินิกที่ได้จะอันตรายต่อ Patient Safety จึงต้อง Hard Block ทั้งระบบทันที
- **One Analysis Record — Multiple Views**: ให้ Django สร้าง Reasoning Ledger ชุดเดียว แล้ว Frontend ทั้ง 3 เล่มรายงาน (Physician, Patient, Multi-Omics) นำไปแสดงผลโดยไม่ตีความคะแนนใหม่
- **No Pseudo-Precision**: ห้ามใช้ตัวเลข % ของความเชื่อมั่นเนื่องจากยังไม่มี cohort calibration ที่ ratify แล้ว

## โครงสร้างไฟล์
- [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py): หลักการประเมิน Axis scores, Identity validator, Invariant checks (Python), และการสร้าง Ledger
- [views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py): API Endpoint `calculate_precision_medicine` ที่เรียก Identity Validator Gate ก่อนประเมินผล
- [route.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/api/ai/report/route.ts): Next.js API Route สำหรับสร้างรายงาน 3 เล่ม, `buildReasoningLedger`, `validateAnalysisRecord` (INV-001..014), และ Prompt Constitution

## จุดที่ต้องระวัง
- **Identity Conflict Handling**: เมื่อ API คืน HTTP 400 พร้อม `BLOCKED_DATA_RECONCILIATION` ฝั่ง UI ต้องแสดงผล Data Reconciliation Report เพื่อให้เจ้าหน้าที่ตรวจสอบข้อมูลก่อน
- **Module Registry Approval**: ตราบใดที่ `approved_modules = 0` ชื่อโมดูลจะไม่ถูกแสดงในรายงานหลัก หากอนุมัติแล้วต้องอัปเดต `mapping_status = APPROVED` ใน DB

## อ้างอิง
- `x.md` (ข้อเสนอแนะและฟีดแบ็คจากทีมแพทย์)
- `AGENTS.md` (รัฐธรรมนูญนักพัฒนา 19 ข้อ)
