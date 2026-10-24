# Module: EP3 — ล็อก Canonical Registry (12 Domains, 39 Axes, 9 Steps)

## ทำอะไร
ดำเนินการล็อกค่า Master Registry ของระบบ TSPI ให้ตรงตามมาตรฐานเอกสารวันที่ 22.09.2026 โดยครอบคลุม:
1. **12 Canonical Domains:** D1 ถึง D12
2. **39 Biological Axes:** A1 ถึง A39 พร้อมการแยก `canonical_axis_name` และ `display_alias`
3. **9 Restoration Steps:** S1 ถึง S9 (Detoxification ... Prakati)

---

## ทำไมถึงทำแบบนี้
1. **ป้องกัน Ontology Inconsistency:** ป้องกันไม่ให้ส่วนประกอบต่างๆ (เช่น Next.js Renderer หรือ LLM Prompt) สะกดชื่อ รหัส หรือลำดับของแกนชีวภาพผิด หรือนำชื่อ Domain ยุคเก่า (Legacy) กลับมาแสดงผล
2. **Strict Validation:** หาก Renderer หรือ Data Import พบรหัสหรือชื่อที่ไม่ตรงกับ Canonical Registry ระบบจะสั่งบล็อกและตอบกลับ `BUILD_FAIL` หรือ `INVARIANT_VIOLATION` ทันที

---

## โครงสร้างไฟล์
- `backend/patients/tspi_engine.py`: [SYSTEM_DOMAINS](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L61), [OFFICIAL_39_AXES](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L5), [OFFICIAL_9_STEPS](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L47)
- `frontend/src/data/39_last_x.json`: Single Source of Truth สำหรับ Frontend
- `backend/patients/tests.py`: `CanonicalRegistryLockTests` สำหรับทดสอบเกณฑ์ความถูกต้องของชื่อและรหัส

---

## จุดที่ต้องระวัง
- ห้ามเรนเดอร์ Domain แบบ hard-code ใน HTML/PDF ให้ดึงข้อมูลจาก `canonical_domain_registry()` เท่านั้น
- ชื่อ `display_alias` ใช้ประดับหน้าจอได้ แต่ในระดับ Data Record ต้องอ้างอิงรหัส Canonical (เช่น A35, D1, S1) เสมอ

---

## อ้างอิง
- เอกสารเกณฑ์ตรวจรับ EP3 (รอบแก้ 22.09.2026)
- [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py)
