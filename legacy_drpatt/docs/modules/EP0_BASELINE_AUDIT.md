# Module EP0 Baseline Audit

## ทำอะไร

บันทึก baseline ของ TSPI Clinical Intelligence ก่อนเริ่ม Final Core Correction Round ตามเอกสาร Development Requirements วันที่ 20 September 2026 โดย audit เส้นทางที่สร้าง analysis และรายงาน เพื่อกำหนดขอบเขตของ EP 1 Identity Conflict Gate

## ข้อค้นพบ

### สิ่งที่มีอยู่และต่อยอดได้

- `backend/patients/tspi_engine.py` มี `validate_patient_identity`, `calculate_tspi_analysis` และ `validate_analysis_record`
- `backend/patients/models.py` มี `AnalysisRecord` สำหรับเก็บ ledger snapshot
- `PatientViewSet.calculate_precision_medicine` ตรวจ identity conflict ก่อนคำนวณและบันทึก `AnalysisRecord`
- HYPOTHESIS axes ถูก gate ไม่ให้มี numeric score ใน backend engine แล้ว
- Module registry มีสถานะ PROVISIONAL และ engine ซ่อน clinical module matching เมื่อยังไม่มี approved module

### ช่องว่างที่ต้องแก้

1. การสร้าง analysis ยังไม่เป็น single path
   - `PatientViewSet.tspi_analysis` และ `generate_clinical_pdf` เรียก `calculate_tspi_analysis` จาก biological record ล่าสุดใหม่
   - เส้นทางเหล่านี้อาจไม่ใช่ ledger เดียวกับ `AnalysisRecord` ที่รายงานอื่นใช้

2. Frontend ยังประกอบ reasoning ledger ซ้ำ
   - `frontend/src/app/api/ai/report/route.ts` มี `buildReasoningLedger` และ `validateAnalysisRecord`
   - ทำให้ ontology, score state และ invariant เสี่ยงต่างจาก Django engine

3. Identity gate ยังตรวจเป็น demographic/text consistency เป็นหลัก
   - ยังไม่มี evidence ownership model ที่ยืนยันว่า lab, source document และ clinical history เป็นของ HN เดียวกัน
   - `generate_clinical_pdf` ยัง recompute จาก patient record แทนการรับ immutable `analysis_record_id`

4. สถานะการอนุมัติรายงานยังไม่เป็น state machine กลาง
   - report route มี prompt rules สำหรับ approval language แต่ยังไม่มี persistent release state ที่ renderer ทุกตัวบังคับใช้ร่วมกัน

## ขอบเขต EP 1

EP 1 จะเพิ่ม identity reconciliation gate เป็น backend authority และบังคับใช้กับทุก entry point ที่เริ่ม analysis หรือสร้าง report โดยยังไม่เปลี่ยน canonical registry, scoring contract หรือ UI report wording

### Contract ที่จะเพิ่ม

```text
identity_validation_status = VERIFIED | CONFLICT | UNVERIFIED
analysis_state = ANALYSIS_READY | BLOCKED_DATA_RECONCILIATION
```

เมื่อสถานะเป็น `CONFLICT` ต้อง block:

- axis scoring
- key scoring และ NSS
- network reasoning
- module matching
- treatment recommendation
- physician, patient และ multi-omics report generation

ผลลัพธ์ที่อนุญาตมีเพียง data reconciliation payload สำหรับ staff/physician

## Fixture ที่ต้องมี

- `verified_patient_case`: HN, DOB, sex และ evidence ownership ตรงกัน
- `demographic_conflict_case`: อายุหรือเพศใน clinical history ขัดกับ patient profile
- `ownership_conflict_case`: lab/source document อ้าง HN ไม่ตรงกับ patient ที่ร้องขอ analysis

## เกณฑ์ผ่าน EP 0

- ระบุจุดสร้าง analysis และ renderer หลักครบ
- ระบุ duplicate reasoning paths ที่ต้องตัดใน EP ถัดไป
- กำหนด fixture และ acceptance contract สำหรับ P0 identity gate แล้ว

## เกณฑ์เข้าสู่ EP 1

ก่อน implement EP 1 ต้องมี test ที่พิสูจน์ว่า conflict case ไม่สร้าง `PatientBiologicalRecord`, `AnalysisRecord`, PDF หรือ report content ใหม่
