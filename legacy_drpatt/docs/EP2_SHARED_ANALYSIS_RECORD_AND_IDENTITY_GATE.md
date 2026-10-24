# Module: EP2 — ข้อมูลกลางและ Identity Gate

## ทำอะไร
กำหนดให้ระบบใช้ Backend `AnalysisRecord` เป็น Single Source of Truth สำหรับการออกรายงานทุกประเภท (Physician Edition, Patient Edition, Multi-Omics Edition) และบล็อกกระบวนการวิเคราะห์หากพบปัญหาความไม่สอดคล้องของตัวตนผู้ป่วย (Identity Conflict) หรือข้อมูลไม่สมบูรณ์ (`UNVERIFIED`)

---

## ทำไมถึงทำแบบนี้
1. **ป้องกันการคำนวณหรือสร้าง ID จำลองใน Frontend:** Frontend ต้องไม่ประมวลผลคะแนนชีววิทยาเองเพื่อป้องกันความขัดแย้งของข้อมูล ทุก View จะอ่านข้อมูลวิเคราะห์จาก `AnalysisRecord.ledger` ที่สร้างจาก Backend เท่านั้น
2. **Identity Hard Gate:** หากพบกรณีที่ข้อมูล HN, DOB, Sex หรือเจ้าของผลแล็บไม่ตรงกัน (`CONFLICT`) หรือข้อมูลเดโมกราฟิกไม่ครบ (`UNVERIFIED`) ระบบจะกำหนด `analysis_state = BLOCKED_DATA_RECONCILIATION` และบล็อกการวิเคราะห์และการออกรายงานทันที

---

## โครงสร้างไฟล์
- `backend/patients/models.py`: [AnalysisRecord](file:///Users/tanchonl/Downloads/drpatt/backend/patients/models.py#L156) โมเดลบันทึก Ledger แบบแก้ไขไม่ได้ (Immutable Snapshot)
- `backend/patients/tspi_engine.py`: [validate_patient_identity()](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L222) ฟังก์ชันตรวจสอบและล็อก Invariants ก่อนเริ่มประมวลผล
- `backend/patients/tests.py`: `IdentityConflictGateTests` สำหรับทดสอบเกณฑ์การบล็อกและการแสดงผล `UNVERIFIED`

---

## จุดที่ต้องระวัง
- ห้ามคืนสถานะ `VERIFIED` สำหรับเคสที่ข้อมูลเดโมกราฟิกไม่ครบถ้วน
- ทุกรายงาน (HTML/PDF) จะต้องมี Invariant Check และสร้างจาก `AnalysisRecord` เดียวกันเสมอ

---

## อ้างอิง
- เอกสารเกณฑ์ตรวจรับ EP2 (รอบแก้ 22.09.2026)
- [models.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/models.py)
- [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py)
