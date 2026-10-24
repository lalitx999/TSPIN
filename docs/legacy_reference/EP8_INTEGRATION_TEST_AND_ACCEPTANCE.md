# Module: EP8 — ทดสอบรวมและจัดเตรียมชุดเอกสารส่งมอบ (End-to-End Integration & Artifact Deliverables)

## ทำอะไร
ดำเนินการทดสอบรวมทั้งระบบตั้งแต่การลงทะเบียนผู้ป่วย การซักประวัติ การประเมินผล TSPI Biological Engine ไปจนถึงการสกัดเอกสาร JSON Ledger และ PDF ทั้ง 3 ฉบับ พร้อมจัดเตรียมชุดส่งมอบเพื่อตรวจรับสำหรับ Physician Shadow Pilot

---

## รายการ Artifacts สรุปผลส่งมอบเมื่อจบ EP8

1. **PDF Reports 3 ฉบับ:** Physician Edition, Patient Edition, Multi-Omics Edition
2. **AnalysisRecord JSON Ledger:** Snapshot แสดงโครงสร้าง Invariant ที่แก้ไขไม่ได้
3. **Scoring Registry:** รายการสัญญาพิกัดกฎคะแนน (`AxisScoringContract`)
4. **Ontology Snapshot:** รายการนิยาม 12 Domains, 39 Axes, 9 Steps
5. **ผลการทดสอบระบบ (Test Verification Results):** ครอบคลุม Unit Tests ทั้งหมดใน `backend/patients/tests.py`
6. **Approval Audit Log:** ประวัติประวัติตามกฎ PDPA และสิทธิ์การเปลี่ยนสถานะรายงาน

---

## คำสั่งสำหรับรันการทดสอบระบบ (สำหรับ User รันเองตามกฎ 5.3)

```bash
python backend/manage.py test patients.tests
```

---

## อ้างอิง
- เอกสารเกณฑ์ตรวจรับ EP8 (รอบแก้ 22.09.2026)
- [tests.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tests.py)
