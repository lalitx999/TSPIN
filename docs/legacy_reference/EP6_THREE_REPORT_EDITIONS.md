# Module: EP6 — การสกัดและแสดงผลรายงานทั้ง 3 ฉบับ (Physician, Patient, Multi-Omics)

## ทำอะไร
ปรับปรุงการแสดงผลรายงานทางการแพทย์ทั้ง 3 ฉบับ (Physician Edition, Patient Edition, Multi-Omics Edition) ให้ใช้สถาปัตยกรรม Renderer อ่านจาก Backend `AnalysisRecord` เดียวกัน และปฏิบัติตามกฎความปลอดภัยการสื่อสารข้อมูล:
1. **Physician Edition:** แสดงผลรายละเอียดทางชีววิทยาสรีรวิทยาครบถ้วน ซ่อน Module ที่ยังไม่ผ่านการอนุมัติ (`approved_modules = 0`)
2. **Patient Edition:** แปลงข้อมูลเป็นภาษาธรรมชาติ อ่านง่าย ปราศจาก Debug Tags (เช่น `[MEASURED]`, `[HYPOTHESIS]`) และปรับหัวข้อข้อความไม่ให้กล่าวเกินจริงหากยังไม่ผ่านการรับรองโดยแพทย์
3. **Multi-Omics Edition:** รักษาข้อมูลตั้งต้นให้สอดคล้องกับฉบับแพทย์ โดยแสดง Omics recommendations เฉพาะเมื่อผ่านการประเมิน Clinical Utility Gate

---

## ทำไมถึงทำแบบนี้
1. **One Patient → One Immutable Ledger → Multi-Views:** รับประกันว่าข้อมูลทางคลินิก (เช่น คะแนน Axis, NSS, Identity, Safety Gate) จะตรงกัน 100% ทุกรายงาน ต่างกันเฉพาะภาษาและระดับรายละเอียด
2. **Patient Safety Communication:** ป้องกันไม่ให้ข้อความเทคนิคภายในของระบบหรือสมมติฐานสร้างความเข้าใจผิดแก่คนไข้

---

## โครงสร้างไฟล์
- `backend/patients/views_ai.py`: Endpoint สร้างรายงานและ PDF
- `frontend/src/app/doctor/precision-report/page.tsx`: UI ควบคุมการสร้างรายงาน
- `backend/patients/tests.py`: `ReportConsistencyTests`

---

## อ้างอิง
- เอกสารเกณฑ์ตรวจรับ EP6 (รอบแก้ 22.09.2026)
