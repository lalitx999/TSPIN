# EP1 — Identity Conflict Gate

## ผลลัพธ์

เส้นทางวิเคราะห์และรายงานหลักใช้ identity gate เดียวกัน และผลที่ถูกเลือกใช้เป็น `AnalysisRecord` เดิมเท่านั้น ไม่สร้างหรือคำนวณ ledger ใหม่ระหว่างแสดงผล

## Contract

เมื่อพบ `CONFLICT` ระบบตอบกลับ `BLOCKED_DATA_RECONCILIATION` และอนุญาตเฉพาะ reconciliation payload:

- HN ใน SOAP/history ไม่ตรงกับ patient HN
- อายุหรือเพศใน clinical source ขัดกับ patient profile
- `lab_owner_hn`, `source_document_owner_hn`, `clinical_history_owner_hn` หรือรายการ `source_ownership[]` ไม่ตรงกับ HN ที่เลือก

## Enforcement ที่ทำแล้ว

1. `calculate-precision-medicine` ตรวจ ownership ก่อนสร้าง `PatientBiologicalRecord` หรือ `AnalysisRecord`
2. `tspi-analysis` เปลี่ยนเป็น read-only view ของ immutable `AnalysisRecord`; ไม่มี record ก็ส่ง `409 RUN_VERIFIED_ANALYSIS`
3. `generate-clinical-pdf` render จาก `AnalysisRecord` เดียวกัน และ ledger ที่ block จะส่งหน้า reconciliation แทน dossier
4. เพิ่ม regression tests ครอบคลุม ownership mismatch, การไม่สร้าง record, legacy analysis endpoint และ PDF block

## ข้อจำกัดที่ตั้งใจแยกไป EP3

EP1 รองรับ provenance จาก request contract ก่อน เพื่อปิด P0 gate ทันที ส่วนการเก็บ evidence ownership แบบ append-only พร้อม source hash, uploader, เวอร์ชัน และ timestamp จะทำใน EP3 AnalysisRecord & Evidence Ledger

## คำสั่งตรวจสอบ

```bash
cd backend
python manage.py test patients.tests.IdentityConflictGateTests patients.tests.GenerateClinicalPdfGatingTests
```

ไม่ต้องสร้าง migration ใน EP นี้
