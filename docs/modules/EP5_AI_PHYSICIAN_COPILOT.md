# EP 5: Streaming AI Physician & Clinical Copilot (ปัญญาประดิษฐ์ทางการแพทย์และเกตตรวจทาน)

## 1. ภาพรวมโมดูล (Module Overview)
โมดูลนี้ทำหน้าที่เป็นระบบผู้ช่วยแพทย์ปัญญาประดิษฐ์ (AI Physician Assistant & Clinical Copilot) สำหรับคลินิก TSPI โดยมุ่งเน้นการให้คำปรึกษาทางการแพทย์เชิงกลไก (Mechanistic Clinical Reasoning) ผ่านการส่งข้อมูลแบบสตรีมมิ่งสด **Server-Sent Events (SSE)** ร่วมกับระบบสกัดค่าผลแล็บแบบแม่นยำ (Deterministic Lab OCR) และระบบตรวจทานผลลัพธ์โดยแพทย์ก่อนนำเข้าสู่เวชระเบียนจริง (**Artifact Review Gate**)

แก้ปัญหาความเสี่ยงของระบบเดิมที่มีการส่ง Secret API Keys หลุดไปใน Next.js client-side และแก้ปัญหา LLM Hallucination ด้วยการผูกข้อมูลเข้ากับบริบทเวชระเบียนผู้ป่วย (EMR) และกลไก 39 แกนชีววิทยาอย่างเคร่งครัด

---

## 2. Security Pillars & Iron Rules ที่ควบคุม
- **Pillar 2 (Strict RBAC Authorization):** ป้องกันไม่ให้คนไข้ทั่วไป (`patient`) หรือผู้ไม่มีสิทธิ์เข้าถึงเครื่องมือวิเคราะห์ AI ของแพทย์ โดยบล็อกด้วย `403 Forbidden` 100%
- **Pillar 8 (AuditLog Trail):** ทุกการเปิดห้องสนทนา AI (`AI_PHYSICIAN_VIEW`), การสตรีมคำถาม (`AI_QUERY_STREAMED`), และการลงนามอนุมัติหรือปฏิเสธผลวิเคราะห์ (`ARTIFACT_APPROVED_BY_PHYSICIAN` / `ARTIFACT_REJECTED_BY_PHYSICIAN`) จะถูกบันทึก AuditLog อย่างละเอียดตามมาตรฐาน PDPA & HIPAA
- **Pillar 15 (Human-in-the-loop & Safety Boundary):**
  - **ห้าม AI แก้ไขเวชระเบียนโดยตรงเด็ดขาด:** ผลการวิเคราะห์จากแล็บหรือข้อเสนอแนะของ AI จะถูกสร้างเป็น `AgenticArtifact` ในสถานะ `pending` เท่านั้น
  - **แพทย์ต้องเป็นผู้ลงนามอนุมัติ (Physician Sign-Off):** ข้อมูลจะถูกนำไปอัปเดตลงใน `BiologicalRecord` ของคนไข้จริงก็ต่อเมื่อแพทย์กดปุ่ม "อนุมัติและปรับปรุงเข้าแฟ้ม EMR (Approve & Apply)"
  - **ระบบตรวจจับข้อห้ามทางการแพทย์ (Safety Checks):** แจ้งเตือนแบนเนอร์สีแดงทันทีหากผู้ป่วยมีประวัติแพ้ยา หรือมีคะแนนแกนวิกฤต (&ge; 85)

---

## 3. สถาปัตยกรรม & Data Flow

```
[Doctor Browser]
       │
       ├─ (1) พิมพ์คำถามในห้อง AI Copilot (GET /ai/stream/?q=...&session_id=...) ──┐
       │                                                                            ▼
       │                                                                [ai_physician_stream_api]
       │                                                                            │
       │                                                                 (EMR Context Injection)
       │                                                                 (ClinicalCopilotEngine.stream)
       │                                                                            ▼
       │ ◀── สตรีมข้อความแบบ Server-Sent Events (text/event-stream) ────────────────┘
       │
       ├─ (2) วางผลตรวจแล็บใน Lab OCR (POST /ai/lab-ocr/) ──────────────────────────┐
       │                                                                            ▼
       │                                                                 [DeterministicLabParser]
       │                                                                            │
       │                                                                 (Regex Biomarker Extraction)
       │                                                                 (Map to Target Biological Axes)
       │                                                                            ▼
       │ ◀── แสดงตารางผลแล็บและแกนที่ได้รับผลกระทบ ──────────────────────────────────┘
       │
       └─ (3) ส่งเข้าคิวตรวจทาน (Submit as Pending Artifact) ───────────────────────┐
                                                                                    ▼
                                                                        [AgenticArtifact: pending]
                                                                                    │
                                                                         [artifact_review_view]
                                                                                    │
                                              แพทย์กดอนุมัติ (Approve) ──────────────┤
                                                                                    ▼
                                                              [อัปเดต BiologicalRecord ใน EMR จริง]
                                                              [บันทึก AuditLog ความปลอดภัย]
```

---

## 4. โครงสร้างไฟล์ที่สร้างและพัฒนา

| ตำแหน่งไฟล์ | คำอธิบายหน้าที่ |
|---|---|
| `apps/intelligence/models.py` | โมเดล `AIConsultationSession`, `AIConsultationMessage`, และ `AgenticArtifact` |
| `apps/intelligence/services.py` | `DeterministicLabParser` (สกัดค่าแล็บ), `ClinicalCopilotEngine` (SSE Stream), และ `ClinicalSafetyChecker` |
| `apps/intelligence/views.py` | Controllers: AI Copilot Room, SSE Stream API, Lab OCR, และ Artifact Review Gate |
| `apps/intelligence/urls.py` | กำหนด Route ภายใต้เนมสเปซ `intelligence` (`/ai/...`) |
| `apps/intelligence/tests.py` | ชุดทดสอบ 6 รายการ: Lab Parser, Safety Checker, SSE Generator, RBAC 403, AuditLog, Artifact Approval |
| `templates/intelligence/ai_physician.html` | หน้าจอแชตผู้ช่วยแพทย์ รองรับการสตรีมคำตอบแบบพิมพ์สด (SSE EventSource) |
| `templates/intelligence/lab_ocr.html` | หน้าจอสกัดค่าแล็บ พร้อมปุ่มโหลดตัวอย่างและคำนวณแกนอัตโนมัติ |
| `templates/intelligence/artifact_review.html` | เกตตรวจทานผลวิเคราะห์ AI พร้อมปุ่มลงนามอนุมัติ (Approve & Apply) หรือปฏิเสธ (Reject) |

---

## 5. ผลการทดสอบ (Automated Test Verification)

รันคำสั่ง:
```bash
USE_SQLITE=True ./.venv/bin/python manage.py test intelligence clinical patients accounts core
```

ผลลัพธ์:
```text
Found 33 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
.................................
----------------------------------------------------------------------
Ran 33 tests in 3.996s

OK (100% ผ่านทุกการทดสอบ)
```
- ผ่านการทดสอบทั้งหมด **33/33 รายการ** (100% Pass)
- ตรวจสอบการสกัดค่าแล็บ FBS, HbA1c, hs-CRP, Cholesterol เชื่อมโยงแกน 1, 5, 6 ได้แม่นยำ
- ตรวจสอบ Safety Boundary ดักจับประวัติแพ้ยาและคะแนนวิกฤตสำเร็จ
- ตรวจสอบกระบวนการ Artifact Review: คะแนนเข้าสู่ EMR จริงเมื่อแพทย์อนุมัติเท่านั้น

---

## 6. แผนการเชื่อมต่อ EP ถัดไป (EP 6: Precision Report Generator & Multi-Omics PDF)
ใน EP 6 เราจะนำข้อมูลจาก `Patient`, `PatientHistory`, `BiologicalRecord`, และ `AnalysisRecord` เข้าสู่:
1. **WeasyPrint PDF Engine:** ออกแบบและเรนเดอร์รายงานการแพทย์แม่นยำระดับพรีเมียม 30 หน้าแบบความละเอียดสูง (Print-ready 300 DPI)
2. **3 Report Editions:** Physician Edition (ฉบับแพทย์ละเอียดสูง), Patient Edition (ฉบับคนไข้เข้าใจง่าย), และ Multi-Omics Edition
3. **State Machine Approval & Watermark:** ระบบประทับลายน้ำ (DRAFT vs FINAL APPROVED) และ QR Code ตรวจสอบความถูกต้องของรายงาน
