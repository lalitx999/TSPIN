# EP 4: Mechanistic Biological Engine & 39 Axes Visualizer (กลไก 39 แกนชีววิทยาและแผนผังเรดาร์)

## 1. ภาพรวมโมดูล (Module Overview)
โมดูลนี้คือเครื่องยนต์หลักของการแพทย์แม่นยำเชิงกลไก (Precision Mechanistic Medicine Engine) ของ TSPI Clinic ทำหน้าที่ถอดรหัสความเสื่อมและความผิดปกติระดับเซลล์ของผู้ป่วยผ่านกรอบแนวคิด **TSPI™ 39 Biological Axes Framework** ซึ่งจัดกลุ่มออกเป็น **12 โดเมนชีวภาพหลัก (Biological Domains)**

ระบบนี้ช่วยให้แพทย์สามารถ:
1. สำรวจนิยาม กลไกชีวโมเลกุล และ Sub-axes A, B, C ของทั้ง 39 แกน
2. ประเมินและบันทึกคะแนนความผิดปกติระดับเซลล์ (0 - 100)
3. แสดงผลแผนผังเรดาร์ชีวภาพ (Chart.js Radar Topology) ทั้งในระดับ 12 โดเมน และ 39 แกน
4. ติดตามเส้นเวลาสุขภาพ (Health Timeline) ย้อนหลังเพื่อดูแนวโน้มการฟื้นฟูของ 4 เสาหลักชีวภาพ
5. จับคู่แกนที่มีปัญหา (คะแนน &ge; 60) เข้ากับคลังตำรับสารพฤกษเคมี 200 โมดูลมาตรฐาน TSPI™

---

## 2. Security Pillars & Iron Rules ที่ควบคุม
- **Pillar 2 (Role-Based Access Control):** ทุก View ถูกคุ้มครองด้วย `@clinical_staff_required` สกัดกั้นคนไข้ทั่วไป (`patient`) ด้วย `403 Forbidden` ป้องกันไม่ให้เข้าถึงข้อมูลการวินิจฉัยเชิงลึกของแพทย์ก่อนได้รับอนุญาต
- **Pillar 8 (AuditLog Trail):** ทุกการเข้าดูแผนผังเรดาร์ (`AXIS_GRAPH_VIEW`) และการอัปเดตคะแนนชีวภาพ (`BIOLOGICAL_AXES_UPDATED`) จะถูกบันทึก Audit Trail ลงฐานข้อมูลอย่างแม่นยำ พร้อมระบุ HN ของคนไข้และ IP ของแพทย์
- **Pillar 15 (Immutable Clinical Snapshots):** โมเดล `AnalysisRecord` ทำหน้าที่บันทึกผลการวิเคราะห์แบบแช่แข็ง (Frozen JSON Snapshot) และมีกระบวนการลงนามทางการแพทย์ (Draft &rarr; Reviewed &rarr; Approved &rarr; Released) ไม่สามารถแก้ไขย้อนหลังได้ เพื่อใช้เป็นหลักฐานทางการแพทย์
- **Ontology Inconsistency Resolution:** แก้ไขปัญหาความขัดแย้งของนิยามในระบบเดิมระหว่าง Next.js และ Django โดยยึด Single Source of Truth เดียวกัน:
  - `AXIS_11` = **DNA Repair & Genomic Stability**
  - `AXIS_12` = **Epigenetic Regulation**
  - `AXIS_33` = **Thyroid–Adrenal–Growth Axis**

---

## 3. สถาปัตยกรรม & Data Flow

```
[Doctor Portal]
       │
       ├─ (1) เปิดหน้า 39 Axes Explorer (GET /clinical/axes/?patient_id=X) ──┐
       │                                                                      ▼
       │                                                         [axes_explorer_view]
       │                                                                      │
       │                                                       (TspiClinicalEngine.get_all_axes)
       │                                                       (TspiClinicalEngine.match_recommendations)
       │                                                                      ▼
       │ ◀── แสดงผล 12 โดเมน, แกนวิกฤต, โมดูลแนะนำ ──────────── [axes_explorer.html]
       │
       ├─ (2) เปิดดูเรดาร์ชีวภาพ (GET /clinical/axis-graph/) ─────────────────┐
       │                                                                      ▼
       │                                                           [axis_graph_view]
       │                                                                      │
       │                                                       (คำนวณคะแนนเฉลี่ย 12 โดเมน)
       │                                                       (AuditLog.objects.create)
       │                                                                      ▼
       │ ◀── แผนผังเรดาร์ Chart.js (Vendored Offline) ─────────── [axis_graph.html]
       │
       └─ (3) สำรวจตำรับพฤกษเคมี 200 โมดูล ────────────────────────────────┐
                                                                              ▼
                                                                [therapeutic_matrix_view]
                                                                              ▼
           แสดงรายการโมดูลตามแกนเป้าหมาย ◀──────────────────── [therapeutic_matrix.html]
```

---

## 4. โครงสร้างไฟล์ที่สร้างและพัฒนา

| ตำแหน่งไฟล์ | คำอธิบายหน้าที่ |
|---|---|
| `apps/clinical/data/tspi_39_axes.json` | ฐานข้อมูลคำนิยาม 12 Domains, 39 Axes, Sub-axes A, B, C |
| `apps/clinical/data/200_module_tspi.json` | ฐานข้อมูล 200 โมดูลสารพฤกษเคมีและสารอาหารบำบัด |
| `apps/clinical/data/180_network.json` | โทโพโลยีเครือข่ายความสัมพันธ์ของระบบชีวภาพ |
| `apps/clinical/models.py` | โมเดล `BiologicalRecord` (39 แกน 0-100) และ `AnalysisRecord` (Immutable Snapshot) |
| `apps/clinical/engine.py` | Service Layer กลไก `TspiClinicalEngine` โหลดและประมวลผลพร้อม Memory Cache |
| `apps/clinical/forms.py` | `BiologicalRecordForm` และ `AnalysisApprovalForm` |
| `apps/clinical/views.py` | Controllers: Explorer, Topology Radar, Timeline, และ Therapeutic Matrix |
| `apps/clinical/urls.py` | Route ภายใต้เนมสเปซ `clinical` (`/clinical/...`) |
| `apps/clinical/tests.py` | ชุดทดสอบ 6 รายการ: Engine loading, Model methods, Domain average, RBAC 403, AuditLog, HTMX |
| `templates/clinical/axes_explorer.html` | หน้าสำรวจ 39 แกน 12 โดเมน พร้อมตัวเลขคะแนนและระบบจับคู่โมดูล |
| `templates/clinical/axis_graph.html` | หน้าจอแสดงผลเรดาร์ชาร์ต (Chart.js Radar) Dark Mode |
| `templates/clinical/axis_timeline.html` | เส้นเวลาสุขภาพ 4 เสาหลักชีวภาพย้อนหลัง |
| `templates/clinical/therapeutic_matrix.html` | หน้าค้นหาและกรองโมดูลสารพฤกษเคมี 200 โมดูล |

---

## 5. ผลการทดสอบ (Automated Test Verification)

รันคำสั่ง:
```bash
USE_SQLITE=True ./.venv/bin/python manage.py test clinical patients accounts core
```

ผลลัพธ์:
```text
Found 27 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
...........................
----------------------------------------------------------------------
Ran 27 tests in 2.234s

OK
Destroying test database for alias 'default'...
```
- ผ่านการทดสอบทั้งหมด **27/27 รายการ** (100% Pass)
- ตรวจสอบความถูกต้องของ Ontology: Axis 11 (DNA Repair), Axis 12 (Epigenetic) ถูกต้อง 100%
- ตรวจสอบระบบ RBAC สกัดกั้น Patient เข้าถึงโมดูลคลินิกด้วย 403 สำเร็จ
- ตรวจสอบ AuditLog บันทึกการเปิดดูเรดาร์และการประเมินคะแนนสำเร็จ

---

## 6. แผนการเชื่อมต่อ EP ถัดไป (EP 5: Streaming AI Physician & Clinical Copilot)
ใน EP 5 เราจะนำข้อมูลจาก `BiologicalRecord` 39 แกน และ `PatientHistory` ไปเป็น Context ให้กับ:
1. **Clinical AI Copilot:** ระบบผู้ช่วยแพทย์พร้อม Server-Sent Events (SSE) Streaming
2. **Deterministic Lab OCR Parser:** ระบบสกัดค่าแล็บและคำนวณคะแนนแกนชีวภาพอัตโนมัติ
3. **Double-Check Safety Boundary (Pillar 15):** ระบบตรวจสอบความปลอดภัยของคำแนะนำทางการแพทย์และขนาดยา ก่อนส่งผลลัพธ์ให้แพทย์ตรวจทาน (Artifact Review)
