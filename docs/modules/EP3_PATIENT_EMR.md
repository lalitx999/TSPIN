# EP 3: Doctor Portal: Patient Roster & EMR View (เวชระเบียนและความฉลาดทางการแพทย์)

## 1. ภาพรวมโมดูล (Module Overview)
โมดูลนี้ทำหน้าที่เป็นหัวใจหลักของคลินิกในการบริหารจัดการเวชระเบียนผู้ป่วย (Patient Master Record / EMR), การค้นหาแบบตอบสนองทันที (HTMX Live Search), แฟ้มประวัติการรักษาแบบครอบคลุม (Comprehensive Clinical Dossier), และระบบบันทึกผลการตรวจรักษาตามกรอบมาตรฐาน **SOAP Clinical Notes** (Subjective, Objective, Assessment, Plan) พร้อมระบบคำนวณดัชนีมวลกาย (BMI) และสัญญาณชีพอัตโนมัติ

สร้างขึ้นเพื่อทดแทนระบบเดิมใน Next.js ที่ส่งสัญญาณเรียก API ผ่าน client-side ซึ่งเสี่ยงต่อการรั่วไหลของข้อมูลเวชระเบียน และแก้ปัญหา state ซ้ำซ้อน โดยเปลี่ยนมาใช้ **Pure Django + HTMX + PostgreSQL** 100%

---

## 2. Security Pillars & Iron Rules ที่ควบคุม
- **Pillar 2 (Strict Authorization & RBAC):** ทุก View ถูกล็อกด้วย `@clinical_staff_required` อนุญาตเฉพาะแพทย์ (`doctor`), พยาบาล (`nurse`), และผู้ดูแลระบบ (`admin`) เท่านั้น คนไข้ทั่วไป (`patient`) หรือผู้ไม่ระบุตัวตนจะถูกสกัดกั้นด้วย `403 Forbidden` ทันที
- **Pillar 5 (ORM Efficiency & Anti-N+1):** ใช้ `prefetch_related('histories__doctor')` ในการโหลดแฟ้มเวชระเบียน ทำให้สามารถดึงข้อมูลประวัติการรักษาทั้งหมดและชื่อแพทย์ผู้ตรวจได้ใน **1 Single Query** ป้องกันปัญหาฐานข้อมูลทำงานหนัก
- **Pillar 8 (AuditLog Trail):** ทุกครั้งที่มีการเปิดดูแฟ้มเวชระเบียนผู้ป่วย (`EMR_PATIENT_VIEW`), ลงทะเบียนผู้ป่วยใหม่ (`PATIENT_EMR_CREATED`), แก้ไขเวชระเบียน (`PATIENT_EMR_UPDATED`), หรือบันทึก SOAP Note (`SOAP_NOTE_RECORDED`) ระบบจะทำการบันทึก AuditLog ลงฐานข้อมูลทันทีพร้อม IP Address, User Agent และ Metadata ตามมาตรฐาน PDPA
- **Pillar 15 (Clinical Safety Alerts):** เพิ่มแถบแจ้งเตือนระดับสีแดงเด่นชัด (`Allergies Warning Alert Banner`) บนหัวแฟ้มเวชระเบียนทันทีหากผู้ป่วยมีประวัติการแพ้ยาหรือสารเคมี เพื่อป้องกันความผิดพลาดทางการแพทย์

---

## 3. สถาปัตยกรรม & Data Flow

```
[Doctor Browser]
       │
       ├─ (1) พิมพ์คำค้นหา HN/ชื่อ (HTMX keyup 300ms) ──────────┐
       │                                                         ▼
       │                                            [patient_list_view]
       │                                                         │
       │   (2) คืนค่าเฉพาะ Partial HTML (<tr> rows)              ▼
       │ ◀────────────────────────────────────── [patient_table_rows.html]
       │
       ├─ (3) คลิกเปิดแฟ้มคนไข้ (GET /doctor/patients/<id>/) ────┐
       │                                                         ▼
       │                                           [patient_detail_view]
       │                                                         │
       │                                           (Prefetch & AuditLog)
       │                                                         ▼
       │ ◀── คืนค่าเต็มหน้าแฟ้มเวชระเบียน ──────── [patient_detail.html]
       │
       └─ (4) บันทึก SOAP Note ใหม่ (HTMX POST) ─────────────────┐
                                                                 ▼
                                                      [patient_add_soap_view]
                                                                 │
                                                       (บันทึก & บันทึก AuditLog)
                                                                 ▼
           คืนค่าเฉพาะ Partial Card ◀────────── [history_soap_card.html]
```

---

## 4. โครงสร้างไฟล์ที่สร้างและแก้ไข

| ตำแหน่งไฟล์ | คำอธิบายหน้าที่ |
|---|---|
| `apps/patients/models.py` | โมเดล `Patient` (HN, ID Hash, ประวัติการแพ้), `PatientHistory` (SOAP, Vitals JSON), `Appointment` |
| `apps/patients/forms.py` | `PatientForm` (Validation HN ซ้ำ) และ `PatientHistorySOAPForm` (คำนวณ BMI อัตโนมัติ) |
| `apps/patients/views.py` | Controller จัดการ Dashboard, Live Search, Patient Detail, Patient Create/Edit, และ Add SOAP |
| `apps/patients/urls.py` | กำหนด Route ภายใต้เนมสเปซ `patients` (`/doctor/...`) |
| `apps/patients/tests.py` | ชุดทดสอบ 7 หมวด: Model, Form BMI, RBAC 403, AuditLog, HTMX Live Search, HTMX Filter, SOAP Note |
| `templates/patients/dashboard.html` | แดชบอร์ดคลินิกพร้อมตัวเลขสถิติดึงจากฐานข้อมูลจริง |
| `templates/patients/patient_list.html` | หน้ารายชื่อคนไข้ (Roster) รองรับช่องค้นหา HTMX และ Filter สถานะ |
| `templates/patients/partials/patient_table_rows.html` | Partial template สำหรับแถวตาราง คืนเฉพาะแถวเมื่อค้นหาผ่าน HTMX |
| `templates/patients/patient_detail.html` | หน้าแฟ้มเวชระเบียนฉบับเต็ม พร้อมแท็บ SOAP Timeline และแจ้งเตือนแพ้ยา |
| `templates/patients/partials/history_soap_card.html` | Partial template สำหรับการ์ดบันทึก SOAP Note แต่ละครั้ง |
| `templates/patients/patient_form.html` | ฟอร์มเพิ่ม/แก้ไขข้อมูลเวชระเบียนผู้ป่วย |

---

## 5. ผลการทดสอบ (Automated Test Verification)

รันคำสั่ง:
```bash
USE_SQLITE=True ./.venv/bin/python manage.py test patients accounts core
```

ผลลัพธ์:
```text
Found 21 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
.....................
----------------------------------------------------------------------
Ran 21 tests in 2.075s

OK
Destroying test database for alias 'default'...
```
- ผ่านการทดสอบทั้งหมด **21/21 รายการ** (100% Pass)
- ตรวจสอบความปลอดภัย RBAC สกัดกั้น Patient เข้าถึง EMR ด้วยรหัส 403 สำเร็จ
- ตรวจสอบ AuditLog ถูกบันทึกเมื่อเปิดดูและบันทึกประวัติการรักษาสำเร็จ

---

## 6. แผนการเชื่อมต่อ EP ถัดไป (EP 4: 39 Biological Axes Engine)
ใน EP 4 เราจะนำข้อมูลจาก `Patient` และ `PatientHistory` เชื่อมเข้าสู่:
1. **Mechanistic Biological Engine:** คำนวณคะแนนสุขภาพระดับเซลล์และชีววิทยาโมเลกุล 39 แกน
2. **Chart.js Visualization:** แสดงกราฟใยแมงมุม (Radar/Topology Chart) และไทม์ไลน์คะแนนสุขภาพ
3. **AnalysisRecord Model:** บันทึก Snapshot ข้อมูลผลการวิเคราะห์แบบ Immutable เพื่อการตรวจสอบย้อนหลัง
