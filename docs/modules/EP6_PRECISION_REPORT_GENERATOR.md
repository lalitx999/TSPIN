# EP 6: Precision Report Generator & WeasyPrint Multi-Omics PDF (เครื่องยนต์สร้างรายงานการแพทย์แม่นยำ)

## 1. ภาพรวมโมดูล (Module Overview)
โมดูลนี้ทำหน้าที่เป็นระบบสร้างรายงานการแพทย์แม่นยำและการแพทย์เฉพาะบุคคล (Precision Medicine & Multi-Omics Clinical Report) สำหรับ TSPI Monolith โดยรองรับการสร้างเอกสารสิ่งพิมพ์ความละเอียดสูง (300 DPI Print-Ready A4 PDF) ผ่านเครื่องยนต์ **WeasyPrint** โดยตรงบนฝั่ง Server (Zero Client-side Leak)

พร้อมระบบแบ่งระดับรายงาน 3 ฉบับ (3 Editions):
1. **Physician Edition:** รายงานฉบับละเอียดสำหรับแพทย์ มีการระบุค่าคะแนน 39 แกน สรุปประวัติ SOAP การวิเคราะห์เชิงกลไก และสูตรสารอาหารบำบัดเฉพาะเจาะจง (Targeted Protocol)
2. **Patient Edition:** รายงานฉบับสำหรับคนไข้ เน้นการใช้ภาษาที่เข้าใจง่าย การแสดงภาพรวม 12 โดเมน และข้อแนะนำการปรับเปลี่ยนพฤติกรรมชีวิต (Lifestyle Recommendations)
3. **Multi-Omics Edition:** รายงานฉบับชีวโมเลกุลขั้นสูง ผสานข้อมูล 39 แกนชีวภาพ เครือข่าย 180 Biological Network และ 200 โมดูลสารพฤกษเคมีบำบัด

---

## 2. Security Pillars & Iron Rules ที่ควบคุม
- **Pillar 2 (Strict RBAC Authorization):** เฉพาะบุคลากรทางการแพทย์ (`doctor`, `nurse`, `lab_technician`) เท่านั้นที่มีสิทธิ์เข้าถึงหน้ารวมรายงาน ออกรายงานใหม่ หรือกดอนุมัติรายงาน คนไข้ทั่วไปจะถูกสกัดกั้นด้วย `403 Forbidden`
- **Pillar 8 (AuditLog Trail):** ทุกขั้นตอนสำคัญถูกบันทึกอย่างเข้มงวด:
  - `REPORT_PREVIEW_HTML`: มีการเปิดดูพรีวิวรายงาน
  - `REPORT_DOWNLOAD_PDF`: มีการดาวน์โหลดไฟล์ PDF รายงาน
  - `REPORT_PHYSICIAN_APPROVED`: แพทย์ลงนามอนุมัติรายงานอย่างเป็นทางการ
  - `REPORT_PHYSICIAN_REJECTED`: แพทย์ปฏิเสธรายงานเพื่อแก้ไข
- **Pillar 15 (Human-in-the-loop & Safety Boundary):**
  - **DRAFT Watermark Isolation:** ตราบใดที่รายงานยังไม่ได้รับการลงนามอนุมัติจากแพทย์ (`status != 'approved'`), ตัวสร้าง PDF และ HTML Preview จะแสดงลายน้ำตัวพิมพ์ใหญ่เฉียงคาดหน้ากระดาษ **"DRAFT - FOR CLINICAL REVIEW ONLY (NOT RELEASED)"** อย่างชัดเจน เพื่อป้องกันการนำรายงานที่ยังไม่ตรวจทานไปจ่ายยาหรือส่งต่อภายนอก
  - เมื่อแพทย์กดปุ่ม **"อนุมัติรายงาน (Physician Sign-Off)"** สถานะจะเปลี่ยนเป็น `approved` ลายน้ำจะถูกปลดออก และประทับตราเวลาและชื่อแพทย์ผู้รับรองอย่างเป็นทางการ

---

## 3. สถาปัตยกรรม & Data Flow

```
[Doctor Portal / Intelligence]
       │
       ├─ (1) สร้างรายงานจากผลวิเคราะห์ (POST /clinical/reports/create/<patient_id>/)
       │                                  │
       │                                  ▼
       │                    [สร้าง AnalysisRecord: status='draft']
       │                                  │
       ├─ (2) แสดงผลพรีวิวแบบเรียลไทม์ (GET /clinical/reports/<id>/preview/?edition=physician)
       │                                  │
       │                                  ▼
       │                    [PrecisionReportGenerator.get_report_context]
       │                    - ดึง 39 แกนชีวภาพ & คำนวณ 12 โดเมน
       │                    - คัดกรอง Dysfunctional Axes (คะแนน >= 60)
       │                    - จับคู่ 200 Therapeutic Modules
       │                    - ตรวจสอบสถานะอนุมัติ (หากยังไม่อนุมัติ -> แปะ DRAFT Watermark)
       │                                  │
       │ ◀── แสดงผลใน Browser Preview Wrapper ───┘
       │
       ├─ (3) แพทย์ตรวจทานและลงนามอนุมัติ (POST /clinical/reports/<id>/signoff/)
       │                                  │
       │                                  ▼
       │                    [status เปลี่ยนเป็น 'approved', บันทึก AuditLog]
       │
       └─ (4) ดาวน์โหลดเอกสารฉบับพิมพ์ A4 (GET /clinical/reports/<id>/pdf/?edition=...)
                                          │
                                          ▼
                            [PrecisionReportGenerator.generate_pdf]
                            - ใช้ WeasyPrint แปลง HTML/CSS เป็น PDF 300 DPI
                            - ฝัง Sarabun Font (Clean Thai Typography)
                            - รองรับ CSS Paged Media (@page, page-break, margin boxes)
                                          │
       ◀── ส่งออกไฟล์ PDF ไบนารี (Content-Type: application/pdf)
```

---

## 4. โครงสร้างไฟล์ที่สร้างและพัฒนา

| ตำแหน่งไฟล์ | คำอธิบายหน้าที่ |
|---|---|
| `apps/clinical/reports.py` | Service Layer: `PrecisionReportGenerator` รวบรวม Context และเชื่อม WeasyPrint engine สร้าง PDF |
| `apps/clinical/views_report.py` | Controller Views: แดชบอร์ดรายงาน, ฟอร์มสร้างรายงาน, HTML Preview, WeasyPrint PDF Download, และ Sign-Off Action |
| `templates/clinical/reports/precision_report_template.html` | เทมเพลต A4 Print CSS สำหรับ WeasyPrint พร้อม DRAFT Watermark และ 3 Editions |
| `templates/clinical/reports/report_preview_wrapper.html` | หน้าจอสำหรับแพทย์ตรวจทานรายงาน มีแถบควบคุมเลือก Edition, พิมพ์, ดาวน์โหลด และปุ่ม Sign-Off |
| `templates/clinical/reports/report_dashboard.html` | หน้ารายการรายงานการแพทย์แม่นยำทั้งหมด พร้อมระบบค้นหาและสถานะอนุมัติ |
| `templates/clinical/reports/report_create.html` | ฟอร์มเลือกคนไข้และกรอกหมายเหตุทางคลินิกเพื่อสร้างรายงานใหม่ |
| `apps/clinical/urls.py` | ลงทะเบียน URL Patterns ทั้ง 5 endpoints ของรายงานการแพทย์แม่นยำ |
| `apps/clinical/engine.py` | ปรับปรุง `get_modules_data()` และ `match_therapeutic_recommendations()` ให้รองรับฐานข้อมูล `200_module_tspi.json` อย่างสมบูรณ์ |
| `apps/clinical/tests.py` | ชุดทดสอบครอบคลุม 100%: ตรวจสอบการสร้าง PDF ไบนารี, ลายน้ำ DRAFT, Sign-Off gate, RBAC, และ AuditLog |

---

## 5. ผลการทดสอบ (Verification Checklist)
- [x] WeasyPrint 70.0 ติดตั้งใน Local Virtual Environment และเรนเดอร์เอกสาร PDF ขนาดกระดาษ A4 สวยงามสมบูรณ์ (ขึ้นต้นด้วย `%PDF`)
- [x] รองรับ 3 Editions: `physician`, `patient`, `omics` ครอบคลุมผู้รับสารทุกกลุ่ม
- [x] ตรวจสอบลายน้ำ DRAFT: รายงานสถานะร่างจะแสดงลายน้ำเตือน เมื่อแพทย์อนุมัติแล้วลายน้ำจะถูกปลดออกอัตโนมัติ
- [x] ระบบป้องกันความปลอดภัย RBAC สกัดกั้นผู้ไม่มีสิทธิ์ด้วย `403 Forbidden`
- [x] ทุกการดาวน์โหลด PDF และการลงนามอนุมัติถูกบันทึก AuditLog อย่างเคร่งครัด
- [x] ชุดทดสอบทั้งหมด 38/38 tests ผ่าน 100% (Pass Rate 100%)
