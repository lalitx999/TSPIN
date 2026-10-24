# EP2 — Master Canonical Ontology & Priority Governance (30 Sep 2026)

## ทำอะไร
- ปรับแก้ไข `CLINICAL_IMPRESSIONS` และ `COUPLING_MECHANISMS` ใน `local_report_generator.py` ให้ใช้ชื่อ **12 Canonical Domains** ตาม Master Registry ใน `tspi_engine.py` ครบถ้วน 100%
- ตัดการโหลดไฟล์ stale frontend JSON (`tspi_36_axes_v2.json`) ใน `render_html_precision_report` และเปลี่ยนมาดึง `OFFICIAL_39_AXES` จาก `tspi_engine.py` โดยตรง (Single Source of Truth)
- แก้ไขข้อความลอย "36 Axes Dynamic Model" ใน `views_ai.py` (Dossier Cover & TOC) เป็น **"39 Axes Master Model"**
- ปรับปรุงการตรวจสอบ Invariant กฎ INV-004, INV-008, INV-009, INV-010 ให้ครอบคลุมความสอดคล้องของ Ontology ทั้งหมด

## ทำไมถึงทำแบบนี้
- เอกสาร P0-4/P0-5 กำหนดว่า Renderer ห้าม Hard-code ชื่อ Domain หรือใช้ Ontology เก่าโดยเด็ดขาด หากชื่อ Domain ไม่ตรง Master Registry ระบบจะถือว่า Invariant Validation ล้มเหลวทันที
- ชื่อย่อสำหรับ UI ใช้ `display_alias` ได้ แต่ในระดับ Database, Core Engine และ Report Generation ต้องเป็น Canonical Name เท่านั้น

## โครงสร้างไฟล์ที่แก้ไข
| ไฟล์ | การเปลี่ยนแปลง |
|------|----------------|
| `backend/patients/local_report_generator.py` | อัปเดต Dict Keys ใน `CLINICAL_IMPRESSIONS` & `COUPLING_MECHANISMS` ให้ตรง 12 Canonical Domains, ดึง `OFFICIAL_39_AXES` โดยตรง |
| `backend/patients/views_ai.py` | แก้ไขข้อความหน้าปกและ TOC จาก 36 Axes เป็น 39 Axes Master Model |
| `backend/patients/tests.py` | เพิ่ม `MasterCanonicalOntologyTests` (3 Test Cases ใหม่) สำหรับตรวจความสอดคล้องของ Domain Keys และ Axes Mapping |

## ผลการทดสอบ
- **Ran 59 tests in 1.849s — OK** (ผ่านทั้ง 59 เคส)

## Invariant Rules ที่บังคับใช้ใน EP2
| Rule ID | สิ่งที่ตรวจ | ผลลัพธ์เมื่อไม่ตรง |
|---------|-----------|-------------------|
| INV-004 | Canonical Restoration Steps 1..9 ชื่อและลำดับ | BUILD_FAIL |
| INV-008 | Canonical 39 Axes รหัสและชื่อภาษาอังกฤษ | BUILD_FAIL |
| INV-010 | Canonical 12 Domains รหัส ชื่อ และการจับคู่กับ Axes | BUILD_FAIL |

## อ้างอิง
- FINAL CORE CORRECTION REQUEST (TSPI Clinical Intelligence Engine) ลงวันที่ 30 Sep 2026
- Section P0-4, P0-5, P0-7, P0-8
