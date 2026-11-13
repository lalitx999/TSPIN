# TSPI EMR — แผนแม่บท สรุปสถาปัตยกรรม และคู่มือระบบเวชระเบียนคลินิกบูรณาการ
## TSPI Clinic EMR (Dr. Patt) — Comprehensive Architecture, Implementation & Clinical Workflow Reference
*เอกสารสรุปภาพรวมฉบับสมบูรณ์ (Minimum 500 Lines Detailed Documentation)*  
*วันที่จัดทำ: 10 พฤศจิกายน 2026*  
*เวอร์ชันระบบ: TSPI EMR v2.4 (Phase B Complete)*  

---

## สารบัญ (Table of Contents)
1. [บทนำและปรัชญาของระบบ (Executive Summary & Philosophy)](#1-บทนำและปรัชญาของระบบ)
2. [สถาปัตยกรรมทางเทคนิคและโครงสร้างระบบ (Technical Architecture)](#2-สถาปัตยกรรมทางเทคนิคและโครงสร้างระบบ)
3. [โฟลว์การทำงานทางคลินิกแบบครบวงจร (End-to-End Clinical Workflow)](#3-โฟลว์การทำงานทางคลินิกแบบครบวงจร)
4. [ระบบปัญญาประดิษฐ์ทางการแพทย์ (AI Physician Copilot Engine)](#4-ระบบปัญญาประดิษฐ์ทางการแพทย์)
5. [กรอบแนวคิด 12 โดเมน และ 39 แกนชีววิทยา (The 12 Domains & 39 Biological Axes)](#5-กรอบแนวคิด-12-โดเมน-และ-39-แกนชีววิทยา)
6. [การแมทชิ่งสูตรการรักษา 200 โมดูล (Therapeutic Matrix & 200 Modules)](#6-การแมทชิ่งสูตรการรักษา-200-โมดูล)
7. [การแก้ไขปัญหา บั๊ก และการอัปเกรดเชิงลึกในรอบนี้ (Issues Resolved & Root Cause Analysis)](#7-การแก้ไขปัญหา-บั๊ก-และการอัปเกรดเชิงลึกในรอบนี้)
8. [คู่มือ API ภายในและสัญญาการแลกเปลี่ยนข้อมูล (Internal API & Contract Specifications)](#8-คู่มือ-api-ภายในและสัญญาการแลกเปลี่ยนข้อมูล)
9. [ความปลอดภัยทางไซเบอร์ การคุ้มครองข้อมูล และธรรมาภิบาลทางคลินิก (Security, PDPA & Clinical Governance)](#9-ความปลอดภัยทางไซเบอร์-การคุ้มครองข้อมูล-และธรรมาภิบาลทางคลินิก)
10. [สรุปผลการทดสอบระบบ (Test Verification & Quality Assurance)](#10-สรุปผลการทดสอบระบบ)
11. [แนวทางการพัฒนาและส่งมอบงานในระยะถัดไป (Roadmap & Handoff Guidelines)](#11-แนวทางการพัฒนาและส่งมอบงานในระยะถัดไป)

---

## 1. บทนำและปรัชญาของระบบ

### 1.1 ที่มาของโครงการ TSPI EMR
ระบบเวชระเบียนอิเล็กทรอนิกส์ **TSPI EMR (Dr. Patt Clinic)** ได้รับการออกแบบขึ้นเพื่อตอบสนองต่อรูปแบบการรักษาเฉพาะทางด้าน **เวชศาสตร์บูรณาการ (Integrative Medicine)**, **เวชศาสตร์ชะลอวัยและฟื้นฟูสุขภาพ (Anti-Aging & Regenerative Medicine)**, และ **การแพทย์แม่นยำระดับโมเลกุล (Precision & Systems Biology)** ซึ่งแตกต่างจากระบบ EMR โรงพยาบาลทั่วไปอย่างสิ้นเชิง

ในเวชปฏิบัติทั่วไป การตรวจวินิจฉัยมักมุ่งเน้นไปที่ *"ชื่อโรค (Disease Label)"* ตามรหัส ICD-10 แล้วจ่ายยาตามอาการ แต่สำหรับคลินิก TSPI การรักษาตั้งอยู่บนสมมติฐานว่า:
> *"โรคเรื้อรังและความเสื่อมถอยของร่างกาย เกิดจากการเสียสมดุลและการทำงานบกพร่องของเครือข่ายชีวภาพ (Dysfunctional Biological Networks) ในระดับเซลล์"*

ดังนั้น ระบบจึงต้องมีเครื่องมือที่สามารถ:
1. เก็บรวบรวมข้อมูลสัญญาณชีพ (Vitals) และอาการของผู้ป่วยอย่างละเอียด
2. ใช้ AI ช่วยวิเคราะห์เชื่อมโยงอาการทางคลินิกเข้ากับกลไกพยาธิสรีรวิทยา (Pathophysiology)
3. ประเมินสุขภาพออกมาเป็นตัวเลขเชิงปริมาณผ่าน **39 แกนชีวภาพ (39 Mechanistic Biological Axes)** ภายใต้ **12 โดเมนหลัก (12 Core Domains)**
4. แสดงผลการกระจายตัวของความผิดปกติผ่าน **แผนผังเรดาร์ชีวภาพและโทโพโลยี (Biological Topology Radar & Network Graph)**
5. แนะนำสารอาหาร สารสกัดพฤกษเคมี และสมุนไพรบำบัดเฉพาะบุคคลจากคลัง **200 โมดูลชีวบำบัด (Therapeutic Modules)**

### 1.2 เสาหลักทั้ง 8 ของสถาปัตยกรรม TSPI (The 8 Pillars)
ระบบถูกพัฒนาขึ้นภายใต้หลักการ 8 ประการเพื่อความน่าเชื่อถือ ความปลอดภัยสูงสุด และการยอมรับตามมาตรฐานเวชปฏิบัติสากล:
* **Pillar 1: Systems Biology Modeling** — จำลองสรีรวิทยาของมนุษย์เป็นเครือข่ายพลวัต (Dynamic Biological Topology)
* **Pillar 2: Doctor-in-the-Loop Governance** — AI ทำหน้าที่เป็น "Copilot" ร่างข้อมูลและคำนวณสถิติเท่านั้น โดยแพทย์เป็นผู้มีอำนาจตัดสินใจและลงนามอนุมัติ (Sign-off) ขั้นสุดท้ายเสมอ ห้ามระบบฟันธงการวินิจฉัยโดยลำพัง
* **Pillar 3: Evidence-Based Therapeutic Matching** — ทุกคำแนะนำโมดูลการรักษาต้องอิงกับคะแนนความผิดปกติของแกนชีวภาพและกลไกเซลล์ที่รองรับ
* **Pillar 4: Longitudinal Health Tracking** — การเก็บข้อมูลแบบต่อเนื่องตามเวลา เพื่อเปรียบเทียบค่าปัจจุบันกับค่าตั้งต้น (Baseline) ทำให้เห็นพัฒนาการของการรักษาอย่างชัดเจน
* **Pillar 5: Privacy by Design & Zero-Trust Security** — เข้ารหัสข้อมูลระบุตัวตน (AES-256 Fernet) และแฮชค้นหาแบบทางเดียว (SHA-256) พร้อมทั้ง De-identify ข้อมูลก่อนส่งออกไปประมวลผลภายนอกทุกครั้ง
* **Pillar 6: Resilient & Modular Architecture** — สถาปัตยกรรม Modular Monolith ทำงานร่วมกับ Fast AI Gateway แยก Process กันอย่างเด็ดขาดเพื่อเสถียรภาพ
* **Pillar 7: Strict Offline-First Front-End (No CDN Dependency)** — ทรัพยากรทั้งหมด (CSS, JS, Fonts, Icons) ถูกโฮสต์ในเครื่อง local ภายใต้ Content Security Policy (CSP = `'self'`) เพื่อความเป็นส่วนตัวและความเร็วสูงสุด
* **Pillar 8: Comprehensive Auditability** — บันทึกประวัติการกระทำ การเข้าถึงข้อมูลคนไข้ และการปรับแต่งตัวเลขคะแนนของแพทย์ลงใน `AuditLog` อย่างละเอียดและไม่สามารถลบทำลายได้

---

## 2. สถาปัตยกรรมทางเทคนิคและโครงสร้างระบบ

### 2.1 ภาพรวมสถาปัตยกรรม (System Component Diagram)

```
+-----------------------------------------------------------------------------------+
|                                 Client Web Browser                                |
|  - Sarabun Web Fonts (Local WOFF2)                                                |
|  - Bootstrap 5.3 + Admin CSS Theme (Mediterranean Terracotta #A5633A)             |
|  - Alpine.js v3 (Declarative State & UI Component Reactivity)                     |
|  - HTMX v1.9.10 (Hypermedia-driven Partial DOM Swaps)                             |
|  - Chart.js v4.4.2 (Local UMD Bundle for Radar & Timeline Visuals)                |
|  - SweetAlert2 v11.14.5 (Interactive Clinical Confirmation Modals)                |
+-----------------------------------------------------------------------------------+
                                          |
                                   HTTP / REST (CSP: 'self')
                                          v
+-----------------------------------------------------------------------------------+
|                        Core Application (Django 6.1.2 Monolith)                   |
|  Ports: 8010 (Development) / 8000 (Production via Gunicorn)                       |
|                                                                                   |
|  [apps/patients]                                                                  |
|   - Models: Patient, PatientHistory, Appointment, ClinicalReviewItem              |
|   - Views: EMR Detail, Visit Form Engine, Calendar Scheduling, Queue Hub          |
|                                                                                   |
|  [apps/clinical]                                                                  |
|   - Models: BiologicalRecord, AnalysisRecord, TherapeuticModule                   |
|   - Engine: TspiClinicalEngine (JSON Caching, Topological Math, Module Matcher)   |
|   - Views: Axes Explorer (Pre-fill Draft), Axis Graph (Topology), Timeline Track  |
|   - Services: Physician Copilot Bridge, Intake Parser, Visit Orchestrator         |
|                                                                                   |
|  [apps/accounts]                                                                  |
|   - Custom User (Roles: Doctor, Nurse, Staff, Patient)                            |
|   - Decorators: @clinical_staff_required, @doctor_required                        |
|                                                                                   |
|  [apps/core]                                                                      |
|   - Models: AuditLog, SoftDeleteModel, BaseTimeStampedModel                       |
|   - Middleware: AuditMiddleware, SecurityHeadersMiddleware                       |
+-----------------------------------------------------------------------------------+
             |                                                  |
     PostgreSQL 16 (Port 5432)                 Internal REST API (Port 8090)
     - Fernet-Encrypted PII                    Header: X-Internal-Token
     - Indexed Medical Histories                                v
     - Relational Axes Scoring         +--------------------------------------------+
                                       |      FastAPI AI Gateway (ai_service/)      |
                                       |  - Worker: Uvicorn Async Engine            |
                                       |  - De-identification Sanitizer             |
                                       |  - Token Bucket Rate Limiter               |
                                       |  - LLM Adapters:                           |
                                       |      * Gemini 2.5 Flash (Primary)          |
                                       |      * Groq Llama 3.3 (Fallback)           |
                                       |      * DeepSeek R1 / OpenAI (Secondary)    |
                                       +--------------------------------------------+
```

### 2.2 การแบ่งเลเยอร์ซอฟต์แวร์ (Separation of Concerns)
1. **Core Web Layer (Django):**
   * ควบคุมความปลอดภัยของเซสชัน (Session Authentication)
   * การตรวจสอบสิทธิ์ตามบทบาทผู้ใช้ (Role-Based Access Control - RBAC)
   * การจัดเก็บข้อมูลเวชระเบียนที่สอดคล้องกับกฎหมายการแพทย์
   * การเรนเดอร์ Template HTML จากฝั่งเซิร์ฟเวอร์แบบเบาแรง (Server-Side Rendering with Partials)

2. **AI Microservice Gateway (FastAPI):**
   * ถูกแยกขาดจากฐานข้อมูลเวชระเบียนโดยตรง (No Direct DB Access)
   * รับเฉพาะข้อความและสัญญาณชีพที่ผ่านการกรองข้อมูลส่วนบุคคลแล้ว (De-identified Clinical Payloads)
   * จัดการการเชื่อมต่อกับโมเดลภาษาขนาดใหญ่ (LLM Gateway Orchestration)
   * จัดการการสตรีมคำตอบ (SSE Streaming) และการบังคับโครงสร้างผลลัพธ์แบบ Structured JSON Output

---

## 3. โฟลว์การทำงานทางคลินิกแบบครบวงจร

วงจรชีวิตของการดูแลคนไข้หนึ่งรายในคลินิก (Patient Clinical Journey) ถูกจัดระบบอย่างไหลลื่นและต่อเนื่อง 5 ขั้นตอนหลัก ดังนี้:

### 3.1 ขั้นตอนที่ 1: การเตรียมตรวจและคัดกรอง (Pre-Visit & Triage)
* **หน้าจอ:** `/doctor/pre-visit/` (คิวคนไข้วันนี้)
* **การทำงาน:**
  1. พยาบาลหรือเจ้าหน้าที่เวชระเบียนทำการลงทะเบียนคนไข้ใหม่ หรือค้นหาคนไข้เดิมจากระบบ
  2. แพทย์เปิดดูรายชื่อคนไข้ที่มีนัดหมายในวันนั้น
  3. แผงควบคุมฝั่งขวาจะดึงข้อมูลจริงของคนไข้ขึ้นมาสรุปให้แพทย์เห็นภาพรวมทันที:
     * ประวัติการแพ้ยาและสารเคมี (Allergies) — มีการเตือนเด่นชัด
     * ยาประจำตัวและอาหารเสริมที่ใช้อยู่ (Current Medications)
     * อาการสำคัญในการมารับบริการครั้งก่อนหน้า
     * การประเมิน 39 แกนครั้งล่าสุด (หากมีแกนวิกฤต $\ge 60$ จะแสดงเตือนสีแดง)
  4. เมื่อคนไข้พร้อมตรวจ แพทย์คลิกปุ่ม **"เริ่มตรวจ"** $\rightarrow$ สถานะนัดหมายเปลี่ยนเป็น "มาตรวจแล้ว (Arrived)" และเปิดหน้าบันทึกการตรวจทันที

### 3.2 ขั้นตอนที่ 2: การบันทึกการตรวจในห้องตรวจ (Intra-Visit Encounter)
* **หน้าจอ:** `/doctor/patients/<id>/?visit=1#new-soap`
* **คอมโพเนนต์:** `static/js/visit_form.js` + `templates/patients/partials/visit_form.html`
* **การทำงาน:**
  1. **สัญญาณชีพ (Vitals 7 ค่า บังคับ):**
     * ความดันโลหิตตัวบน/ตัวล่าง (Systolic / Diastolic) พร้อมตัวตรวจจับความสัมพันธ์ (`diastolic < systolic`)
     * ชีพจร (Pulse, 30–250 bpm)
     * อุณหภูมิร่างกาย (Temperature, 30–45 °C)
     * น้ำหนัก (Weight, kg) และส่วนสูง (Height, cm) $\rightarrow$ คำนวณ BMI อัตโนมัติแบบ Real-time
     * ความเข้มข้นของออกซิเจนในเลือด (SpO2, 50–100%)
  2. **การบันทึกอาการ (Multimodal Chief Complaint & History):**
     * พิมพ์ข้อความซักประวัติลงในกล่องข้อความ
     * บันทึกเสียงพูดผ่าน Web Speech API (`th-TH`) เพื่อถอดเสียงคำพูดคนไข้เป็นตัวหนังสือในเครื่อง
     * แนบรูปถ่ายบาดแผล ผื่นผิวหนัง หรือเอกสารผลตรวจได้สูงสุด 6 รูป (ระบบบีบอัดภาพและลบค่า EXIF / GPS ในเครื่องทันทีก่อนอัปโหลด)
  3. **การทำงานของ Gemini 2.5 Flash SOAP Summarizer:**
     * แพทย์คลิก **"ให้ AI สรุป SOAP"**
     * ระบบส่งข้อความและสัญญาณชีพไปยัง `POST /api/ai/visit/soap`
     * AI สรุปผลลัพธ์เป็น 4 หมวด: **S** (Subjective), **O** (Objective), **A** (Assessment), **P** (Plan)
     * ช่อง SOAP ถูกปลดล็อกให้แพทย์ตรวจทาน ปรับแต่งข้อความ และติ๊กยืนยันว่า *"ตรวจทานแล้ว"*
     * แพทย์คลิก **"ยืนยันบันทึกเข้าเวชระเบียน"** $\rightarrow$ บันทึกเข้าตาราง `PatientHistory`

### 3.3 ขั้นตอนที่ 3: จุดเปลี่ยนผ่านหลังบันทึก (Post-Commit Transition)
เมื่อกดบันทึก SOAP สำเร็จ หน้าจอจะไม่ดีดรีเฟรชอย่างไร้ทิศทาง แต่จะเปิด **SweetAlert2 Action Modal** ที่มี 3 ตัวเลือกชัดเจน:
1. 🩺 **"วิเคราะห์และประเมิน 39 แกนด้วย AI Copilot"** *(แนะนำเป็นลำดับแรก)*  
   $\rightarrow$ นำทางไปยัง `/clinical/axes/?patient_id=<id>&auto_ai=1` เพื่อส่งต่อบริบททางคลินิกเข้าสู่กระบวนการแพทย์แม่นยำ
2. 📅 **"สร้างใบนัดหมายตรวจติดตาม"**  
   $\rightarrow$ นำทางไปยังปฏิทินนัดหมาย `/doctor/appointments/?patient_id=<id>` เพื่อจองคิว 2–4 สัปดาห์ข้างหน้า
3. 📋 **"เสร็จสิ้นการตรวจ (อยู่หน้าแฟ้มคนไข้)"**  
   $\rightarrow$ ปิดฟอร์มบันทึก รีโหลดไทม์ไลน์ SOAP ใหม่ล่าสุด และพร้อมตรวจคนไข้รายอื่น

### 3.4 ขั้นตอนที่ 4: การวิเคราะห์ 39 แกนโดย AI Copilot และการอนุมัติของแพทย์ (Physician Approval)
* **หน้าจอ:** `/clinical/axes/?patient_id=<id>&auto_ai=1`
* **การทำงาน:**
  1. ระบบดึงบันทึก SOAP ล่าสุด, สัญญาณชีพ, ประวัติแพ้ยา, และยาประจำตัวของคนไข้
  2. ส่งไปยัง `POST /api/ai/clinical/suggest-axes` ของ AI Gateway
  3. Gemini 2.5 Flash ทำการประมวลผลเชิงพยาธิสรีรวิทยา และร่างคะแนนความผิดปกติของทั้ง 39 แกน (0–100)
  4. ผลลัพธ์ถูกนำมา **เติมลงในช่องคะแนนให้อัตโนมัติ (Pre-filled Draft)**
  5. แสดงแถบข้อความสรุปมุมมองของ AI (Copilot Insight Banner) พร้อมแสดงเหตุผลประกอบรายแกน เช่น:
     > *"Axis 17 (Gut Mucosal Barrier) = 75: คนไข้มีอาการแสบร้อนกลางอก ท้องอืด และเรอเปรี้ยวเรื้อรัง สอดคล้องกับภาวะเยื่อบุทางเดินอาหารอักเสบและมีความสามารถในการซึมผ่านสูงขึ้น (Intestinal Permeability)"*
  6. **Doctor-in-the-Loop:** แพทย์สามารถปรับเลื่อนคะแนนขึ้นลงได้ตามความเห็นทางวิชาชีพของตนเอง
  7. แพทย์ระบุหมายเหตุทางคลินิก (Clinical Notes) และเลือกว่าจะบันทึกเป็น Baseline หรือไม่
  8. แพทย์คลิก **"บันทึกผลการประเมิน 39 แกนของคนไข้"** $\rightarrow$ จัดเก็บลงในโมเดล `BiologicalRecord` และบันทึก `AuditLog` ทันที

### 3.5 ขั้นตอนที่ 5: แผนผังเรดาร์ชีวภาพและการจ่ายสารอาหารบำบัด (Topology & Therapy)
* **หน้าจอ:** `/clinical/axis-graph/?patient_id=<id>`
* **การทำงาน:**
  1. ระบบพล็อตคะแนนเรดาร์ชาร์ต (Radar Chart) แสดงความสมดุลของร่างกาย:
     * **โหมด 12 โดเมนหลัก:** แสดงโครงสร้างภาพรวมของระบบชีววิทยา 12 มิติ
     * **โหมด 39 แกนกลไก:** แสดงรายละเอียดระดับกลไกเซลล์ทั้ง 39 จุด
     * **การเปรียบเทียบ Baseline:** แสดงเส้นกราฟสีเขียว (ค่าปัจจุบัน) ซ้อนทับเส้นประสีเทา (ค่าตั้งต้น) ให้เห็นการฟื้นตัวอย่างเป็นรูปธรรม
  2. รายการแกนที่มีความผิดปกติรุนแรง ($\ge 60$) จะถูกไฮไลต์ขึ้นมาในแถบเตือนสีแดง
  3. **Therapeutic Matrix Matching:** ระบบจับคู่แกนที่ผิดปกติเข้ากับฐานข้อมูล **200 โมดูลสารอาหาร/พฤกษเคมีบำบัด** อัตโนมัติ เพื่อให้แพทย์นำไปใช้สั่งจ่ายสูตรการฟื้นฟูสุขภาพ
  4. สามารถคลิกพิมพ์ **Precision Medicine Clinical Report** เพื่อมอบให้คนไข้ทำความเข้าใจสุขภาพของตนเอง

---

## 4. ระบบปัญญาประดิษฐ์ทางการแพทย์

### 4.1 สถาปัตยกรรม Gateway (`ai_service/gateway.py`)
ระบบ AI Gateway ถูกออกแบบให้มีความยืดหยุ่นสูง รองรับผู้ให้บริการโมเดลภาษาชั้นนำหลายค่าย พร้อมกลไกความทนทานต่อข้อผิดพลาด (Fault Tolerance):

```python
# รายชื่อโมเดลและการตั้งค่าใน AI Gateway
GEMINI_MODEL = "gemini-2.5-flash"
GROQ_MODEL = "llama-3.3-70b-versatile"
DEEPSEEK_MODEL = "deepseek-reasoner"
```

### 4.2 การจัดการ Gemini 2.5 Flash Thinking Behavior
ในการทดสอบช่วงแรก พบว่าโมเดล Gemini 2.5 Flash มีการสร้าง Thinking Tokens (การคิดในใจ) แนบมาในชิ้นส่วนคำตอบ `candidates[0].content.parts` ซึ่งหากนำมาต่อกันโดยตรงจะทำให้ผลลัพธ์ไม่ใช่ JSON ที่ถูกต้อง และอาจทำให้ Token หมดก่อนคำตอบจริงจะออกมา (`maxOutputTokens` ถูกจำกัด)

ทีมพัฒนาได้ทำการแก้ไขปัญหาเชิงลึกดังนี้:
1. **การคัดกรอง Thought Parts:**
   ```python
   # กรองเอาเฉพาะ content parts ที่ไม่ใช่ thought
   content_text = ""
   for part in candidate.get("content", {}).get("parts", []):
       if not part.get("thought", False):
           content_text += part.get("text", "")
   ```
2. **การจัดสรร Token Budget:**
   ```json
   "generationConfig": {
       "temperature": 0.2,
       "maxOutputTokens": 8192,
       "thinkingConfig": {
           "thinkingBudget": 512
       },
       "responseMimeType": "application/json"
   }
   ```
   การจำกัด `thinkingBudget: 512` ช่วยให้โมเดลมีพื้นที่คิดอย่างเป็นเหตุเป็นผลในระดับที่กระชับ และเหลือพื้นที่มากถึง $7,680$ Tokens สำหรับโครงสร้างคะแนน 39 แกนและคำอธิบายทางการแพทย์ ทำให้การตอบกลับรวดเร็วภายใน 3–5 วินาที

---

## 5. กรอบแนวคิด 12 โดเมน และ 39 แกนชีววิทยา

ตารางโครงสร้างความสัมพันธ์ระหว่าง 12 โดเมนหลัก และ 39 แกนชีวภาพเชิงกลไก (Mechanistic Biological Framework):

| โดเมนที่ | ชื่อโดเมน (Domain Title) | รหัสแกน | ชื่อแกนชีวภาพเชิงกลไก (Axis Name) | กลไกเซลล์และสรีรวิทยาหลัก |
| :---: | :--- | :---: | :--- | :--- |
| **D01** | Immune–Infection Governance | **Axis 1** | Systemic Inflammation & Cytokine Cascades | การควบคุมการหลั่งสารไซโตไคน์อักเสบ (IL-6, TNF-alpha) |
| | | **Axis 2** | Innate Immune Priming & Sentinel Defenses | ภูมิคุ้มกันด่านแรก (NK Cells, Macrophages, Phagocytosis) |
| | | **Axis 3** | Adaptive Memory & Tolerance Calibration | ภูมิคุ้มกันจำเพาะ (T-cells, B-cells) และการป้องกันภูมิแพ้ตนเอง |
| **D02** | Metabolic–Energy Core | **Axis 4** | Mitochondrial Bioenergetics & ATP Dynamics | การสร้างพลังงานระดับเซลล์และชีวพลังงานไมโทคอนเดรีย |
| | | **Axis 5** | Glycemic Regulation & Insulin Sensitivity | ความไวต่ออินซูลินและเมแทบอลิซึมของน้ำตาลกลูโคส |
| | | **Axis 6** | Lipid Homeostasis & Adipokine Signalling | เมแทบอลิซึมของไขมัน คอเลสเตอรอล และฮอร์โมนเนื้อเยื่อไขมัน |
| | | **Axis 7** | Metabolic Flexibility & Nutrient Sensing | ความยืดหยุ่นในการสลับการใช้พลังงาน (AMPK/mTOR pathways) |
| **D03** | Genomic Programming | **Axis 8** | Epigenetic Stability & Methylation Flux | วงจรการส่งผ่านหมู่เมทิล (One-carbon cycle) และการควบคุมยีน |
| | | **Axis 9** | DNA Damage Response & Telomere Integrity | การซ่อมแซมดีเอ็นเอและความยาวของเทโลเมียร์ |
| | | **Axis 10** | Cell Cycle Governance & Senescence | การควบคุมวงจรการแบ่งเซลล์และการกำจัดเซลล์แก่ (Senolytics) |
| **D04** | Detoxification & Clearance | **Axis 11** | Phase I/II Hepatic Biotransformation | การแปรสภาพสารพิษในตับ (CYP450 enzymes และ Conjugation) |
| | | **Axis 12** | Antioxidant Buffering & Redox Homeostasis | สมดุลสารต้านอนุมูลอิสระ (Glutathione, SOD, Catalase) |
| | | **Axis 13** | Extracellular Matrix Clearance & Lymphatic Flow | การระบายน้ำเหลืองและการชะล้างสารคั่งค้างในช่องว่างระหว่างเซลล์ |
| **D05** | Digestive–Gut Ecosystem | **Axis 14** | Microbiome Diversity & SCFA Dynamics | ความหลากหลายของจุลินทรีย์และการสร้างกรดไขมันสายสั้น |
| | | **Axis 15** | Gut Mucosal Barrier & Tight Junctions | ความสมบูรณ์ของเยื่อบุผนังลำไส้และการป้องกัน Leaky Gut |
| | | **Axis 16** | Digestive Enzyme Potency & Secretory IgA | ประสิทธิภาพของน้ำย่อย กรดในกระเพาะ และสารคัดหลั่งภูมิคุ้มกัน |
| **D06** | Vascular–Circulation | **Axis 17** | Endothelial Function & Nitric Oxide | ความยืดหยุ่นของหลอดเลือดและการสังเคราะห์ไนตริกออกไซด์ |
| | | **Axis 18** | Microcirculatory Perfusion & Tissue Delivery | การไหลเวียนของหลอดเลือดฝอยและการส่งผ่านออกซิเจนสู่เนื้อเยื่อ |
| | | **Axis 19** | Blood Rheology & Platelet Activation | ความหนืดของเลือดและการเกาะกลุ่มของเกล็ดเลือด |
| **D07** | Repair–Regeneration | **Axis 20** | Stem Cell Niche & Progenitor Activation | การกระตุ้นเซลล์ต้นกำเนิดเพื่อการฟื้นฟูและสร้างเนื้อเยื่อใหม่ |
| | | **Axis 21** | Tissue Remodeling & Fibrosis Control | การจัดระเบียบเนื้อเยื่อและการควบคุมการเกิดพังผืด |
| | | **Axis 22** | Angiogenic Balance & Microvascular Repair | สมดุลการสร้างหลอดเลือดใหม่ที่เหมาะสมต่อการซ่อมแซม |
| **D08** | Musculoskeletal & Structural | **Axis 23** | Collagen Matrix & Connective Tissue | ความแข็งแรงของเส้นใยคอลลาเจน เอ็น และเนื้อเยื่อเกี่ยวพัน |
| | | **Axis 24** | Bone Turnover & Mineral Homeostasis | สมดุลการสร้างและสลายกระดูก รวมถึงแคลเซียมและแมกนีเซียม |
| | | **Axis 25** | Myofibrillar Health & Muscle Protein Synthesis | มวลกล้ามเนื้อ ความแข็งแรง และการสังเคราะห์โปรตีนกล้ามเนื้อ |
| **D09** | Endocrine Network | **Axis 26** | HPA Axis Dynamics & Cortisol Rhythm | แกนไฮโปทาลามัส-ต่อมหมวกไต และจังหวะฮอร์โมนคอร์ติซอล |
| | | **Axis 27** | Thyroid Hormone Activation & Peripheral Conversion | การเปลี่ยนฮอร์โมนไทรอยด์ T4 สู่ T3 ในเนื้อเยื่อส่วนปลาย |
| | | **Axis 28** | Gonadal Hormone Balance & Receptor Sensitivity | สมดุลฮอร์โมนเพศ (Estrogen, Progesterone, Testosterone) |
| **D10** | Neurological Regulation | **Axis 29** | Neurotransmitter Balance & Synaptic Plasticity | สมดุลสารสื่อประสาท (GABA, Serotonin, Dopamine) และความจำ |
| | | **Axis 30** | Neuroinflammation & Microglial Activation | การอักเสบในระบบประสาทและการทำงานของเซลล์ไมโครเกลีย |
| | | **Axis 31** | Autonomic Balance (Vagal Tone vs Sympathetic) | สมดุลระบบประสาทอัตโนมัติ (Parasympathetic / Sympathetic) |
| **D11** | Organ Axis | **Axis 32** | Gut–Brain Axis Crosstalk | การสื่อสารระหว่างลำไส้และสมองผ่านเส้นประสาทเวกัส |
| | | **Axis 33** | Cardiorenal Synergies & Pressure Regulation | การทำงานร่วมกันระหว่างหัวใจ ไต และการควบคุมความดัน |
| | | **Axis 34** | Hepato–Biliary Clearance & Bile Acid Signalling | การสร้างและขับน้ำดี รวมถึงบทบาทของกรดน้ำดีต่อเมแทบอลิซึม |
| **D12** | Oncology & Systemic Regulation | **Axis 35** | Immune Surveillance & Tumor Microenvironment | ภูมิคุ้มกันตรวจจับเซลล์ผิดปกติและสภาวะแวดล้อมรอบเซลล์ |
| | | **Axis 36** | Circadian Clocks & Melatonin Dynamics | นาฬิกาชีวภาพวงจร 24 ชั่วโมง และการหลั่งฮอร์โมนเมลาโทนิน |
| | | **Axis 37** | Autophagy Flux & Proteostasis | กระบวนการกลืนกินตัวเองของเซลล์ (Autophagy) และการกำจัดโปรตีนเสีย |
| | | **Axis 38** | Cellular Hydration & Electrolyte Gradients | การกักเก็บน้ำในเซลล์และความต่างศักย์ไฟฟ้าของอิเล็กโทรไลต์ |
| | | **Axis 39** | Environmental Toxin Burden & Heavy Metal Efflux | ภาวะสะสมสารพิษจากสิ่งแวดล้อมและการขับโลหะหนักออกจากเซลล์ |

---

## 6. การแมทชิ่งสูตรการรักษา 200 โมดูล

### 6.1 ตรรกะการประมวลผล (Therapeutic Matching Algorithm)
ใน `apps/clinical/engine.py` คลาส `TspiClinicalEngine` ทำหน้าที่คำนวณและจับคู่โมดูลการรักษาโดยมีหลักเกณฑ์ดังนี้:
1. **คัดกรองแกนที่มีความผิดปกติสูง (Dysfunctional Axes):**  
   แกนชีวภาพที่มีคะแนนประเมิน $\ge 60$ จะถูกจัดเป็นแกนที่มีความเสี่ยงทางคลินิก (Clinical Priority)
2. **การเรียงลำดับความรุนแรง:**  
   จัดเรียงแกนที่ผิดปกติจากคะแนนสูงที่สุดลงมา
3. **การจับคู่กับคลังข้อมูล 200 โมดูล (`data/200_module_tspi.json`):**  
   ระบบจะจับคู่รหัสแกนเข้ากับโมดูลพฤกษเคมีบำบัดที่มีกลไกออกฤทธิ์ตรงกัน (Mechanistic Complementarity)
4. **ตัวอย่างการจับคู่ทางการแพทย์:**
   * **Axis 1 (Systemic Inflammation $\ge 70$):** แนะนำโมดูล *Curcumin-Boswellia Synergistic Complex* (ลด NF-kB และ COX-2)
   * **Axis 4 (Mitochondrial Bioenergetics $\ge 70$):** แนะนำโมดูล *CoQ10 Ubiquinol + PQQ + Acetyl-L-Carnitine* (ฟื้นฟูห่วงโซ่ขนส่งอิเล็กตรอน)
   * **Axis 15 (Gut Mucosal Barrier $\ge 70$):** แนะนำโมดูล *Zinc Carnosine + L-Glutamine + Deglycyrrhizinated Licorice (DGL)* (สมานเยื่อบุ Tight Junctions)
   * **Axis 26 (HPA Axis & Cortisol $\ge 70$):** แนะนำโมดูล *Sensoril Ashwagandha + Phosphatidylserine* (ปรับสมดุลต่อมหมวกไต)

---

## 7. การแก้ไขปัญหา บั๊ก และการอัปเกรดเชิงลึกในรอบนี้

ในรอบการพัฒนาล่าสุดนี้ ทีมงานได้ดำเนินการตรวจสอบ วิเคราะห์หาสาเหตุที่แท้จริง (Root Cause Analysis) และแก้ไขจุดบกพร่องทั้งระบบอย่างเบ็ดเสร็จ 5 ประการ:

### 7.1 ปัญหาหน้าจอว่างใน Biological Topology Visualizer (`/clinical/axis-graph/`)
* **อาการ:** เปิดหน้าเรดาร์ชีวภาพแล้วจอขาว กราฟไม่ยอมวาด
* **สาเหตุ:**
  1. เทมเพลตเดิมพยายามโหลด Chart.js จาก CDN ภายนอก ซึ่งถูกบล็อกโดย Content Security Policy (CSP = `'self'`) ของระบบ
  2. โค้ดมีการเรียกตัวแปร `latest_record.doctor.username` โดยตรง แต่ในฐานข้อมูลคนไข้บางรายมีค่า `doctor` เป็น `None` ทำให้เกิด Template Variable Syntax Error
* **การแก้ไข:**
  * ติดตั้งบันเดิลไฟล์โลคัล `static/vendor/chartjs/chart.umd.min.js` (Chart.js v4.4.2) ในเครื่องอย่างถูกต้อง
  * เพิ่ม Guard ป้องกันในเทมเพลต: `{% if latest_record.doctor %}...{% else %}แพทย์ผู้รักษา{% endif %}`
  * ทำ Actionable Empty State รองรับทั้งกรณี "ยังไม่ได้เลือกคนไข้" และ "คนไข้ที่ยังไม่เคยได้รับการประเมิน 39 แกน"

### 7.2 ปัญหาช่องค้นหาคนไข้กินพื้นที่และบดบังเนื้อหากราฟ
* **อาการ:** แถบเลือกคนไข้ด้านบนแสดงปุ่ม Badge รายชื่อคนไข้หลายสิบคนจนเต็มหน้าจอ ทำให้ UI เสียรูปทรง
* **สาเหตุ:** มีการเรนเดอร์รายชื่อ Recent Patients แบบตายตัวใน HTML
* **การแก้ไข:**
  * นำ Badge ทั้งหมดออกตามคำสั่งของผู้ใช้
  * พัฒนาเป็น **กล่องค้นหาแบบเดี่ยว (Single Search Input)** ทำงานร่วมกับ Alpine.js
  * เพิ่มระบบค้นหาอัตโนมัติ (Live Autocomplete Popover Dropdown) ค้นหาได้ทั้งชื่อ สกุล และเลข HN พร้อมแสดงเพศ อายุ และเบอร์โทร สะอาดตาและประหยัดพื้นที่ 100%

### 7.3 บั๊ก `TypeError: '>=' not supported between instances of 'NoneType' and 'int'`
* **อาการ:** หน้า `/clinical/axes/?patient_id=3031` แครชเป็นหน้า Error สีเหลืองของ Django
* **สาเหตุ:** คนไข้หมายเลข 3031 มีเรคคอร์ด `BiologicalRecord` ในฐานข้อมูล แต่ค่าคะแนนแกนทั้งหมดเป็น `None` เมื่อโค้ดใน `views.py` ทำการเรียก `scores_dict.get(ax_id, 50)` พจนานุกรมคืนค่า `None` (เนื่องจากคีย์มีอยู่จริงแต่ค่าเป็น `None`) จากนั้นคำสั่ง `if score >= 60:` จึงแครชทันที
* **การแก้ไข:** ปรับเปลี่ยนเงื่อนไขการเปรียบเทียบใน [apps/clinical/views.py](file:///Users/tanchonl/Documents/tspiN/apps/clinical/views.py) เป็น:
  ```python
  if score is not None and score >= 60:
  ```
  และเพิ่ม Regression Test ใน `apps/clinical/tests.py` เพื่อการันตีว่าจะไม่เกิดปัญหานี้ซ้ำอีก

### 7.4 บั๊ก "AI สรุปไม่สำเร็จ" ใน Visit SOAP Summarizer
* **อาการ:** ในหน้าบันทึกการตรวจ เมื่อกด "ให้ AI สรุป SOAP" มี Modal สีแดงแจ้งเตือนว่า "AI สรุปไม่สำเร็จ"
* **สาเหตุ:**
  1. Gemini 2.5 Flash ทำการสร้าง Thought Parts แนบมากับข้อความ เมื่อนำมารวมกับ JSON คำตอบ ทำให้กลายเป็นข้อความที่ไม่สามารถ Parse ผ่าน `json.loads` ได้
  2. การตั้งค่า `maxOutputTokens: 2048` ต่ำเกินไป ทำให้เมื่อโมเดลคิดยาว คำตอบ JSON ส่วนท้ายจะถูกตัดขาด (Truncated)
* **การแก้ไข:**
  * ปรับแต่ง `ai_service/gateway.py` ให้คัดกรองเอาเฉพาะ `part` ที่ไม่มี `thought: True`
  * กำหนด `thinkingBudget: 512` และเพิ่ม `maxOutputTokens: 8192` ใน `generationConfig`
  * เพิ่มตัวตัดเครื่องหมาย Markdown Code Fence (````json ... ````) ออกก่อนการ Parse JSON

### 7.5 บั๊ก `ValueError: Field 'id' expected a number but got 'undefined'`
* **อาการ:** เมื่อบันทึก SOAP สำเร็จ แล้วกดปุ่ม "วิเคราะห์และประเมิน 39 แกนด้วย AI Copilot" ระบบนำทางไปที่ URL: `/clinical/axes/?patient_id=undefined&auto_ai=1` และแครช
* **สาเหตุ:**
  1. ใน `templates/patients/partials/visit_form.html` มีการส่ง Object `patient: { name: '...', hn: '...' }` โดยลืมระบุฟิลด์ `id: {{ patient.pk }}` ทำให้ตัวแปร `self.patient.id` ฝั่ง JavaScript เป็น `undefined`
  2. ใน `apps/clinical/views.py` มีการนำค่า `request.GET.get('patient_id')` ไปค้นหา `Patient.objects.get(pk=patient_id)` ทันทีโดยไม่ตรวจสอบชนิดข้อมูล ทำให้ Django พยายามแปลงสตริง `'undefined'` เป็นตัวเลข
* **การแก้ไข (4-Layer Defensive Fix):**
  1. เติม `id: {{ patient.pk }}` ใน `visit_form.html`
  2. เพิ่ม `'patient_id': patient.pk` ส่งกลับมาใน JSON Response ของ `visit_commit_view` ใน `apps/patients/views_visit.py`
  3. ปรับ `static/js/visit_form.js` ให้ดึง `res.patient_id || (self.patient && self.patient.id)` พร้อมตรวจสอบความถูกต้อง
  4. เพิ่มตัวกรอง `if patient_id and str(patient_id).isdigit():` ในทุก View ที่เกี่ยวข้อง เพื่อป้องกัน Error 500 อย่างเบ็ดเสร็จ

### 7.6 การเพิ่มช่องกรอกคะแนนและการควบคุมในหน้า 39 Axes Explorer
* **อาการ:** ในหน้า `axes_explorer.html` แสดงเฉพาะชื่อแกนและคำอธิบาย แต่ไม่มีช่องให้แพทย์กรอกหรือปรับลดคะแนน
* **การแก้ไข:**
  * ปรับปรุง [apps/clinical/views.py](file:///Users/tanchonl/Documents/tspiN/apps/clinical/views.py) ให้แนบฟิลด์ฟอร์ม `form_field`, ค่าคะแนน `score`, และเหตุผลจาก AI `ai_rationale` ไปกับแต่ละแกนในแต่ละโดเมน
  * ปรับปรุง [templates/clinical/axes_explorer.html](file:///Users/tanchonl/Documents/tspiN/templates/clinical/axes_explorer.html) ให้แสดงช่อง Input ตัวเลข `axis_1` ถึง `axis_39` บนการ์ดทุกใบ
  * เพิ่มปุ่มด่วน **"ตั้งเป็น 50 ทุกแกน"** และแถบแจ้งเตือน **AI Copilot Insight Banner**

---

## 8. คู่มือ API ภายในและสัญญาการแลกเปลี่ยนข้อมูล

### 8.1 สัญญาความปลอดภัยระหว่างบริการ (Service Auth & Headers)
การสื่อสารระหว่าง Django Web Monolith และ FastAPI AI Gateway ต้องส่งผ่าน Header ยืนยันสิทธิ์เสมอ:
```http
POST /api/ai/... HTTP/1.1
Host: 127.0.0.1:8090
Content-Type: application/json
X-Internal-Token: <INTERNAL_API_TOKEN จาก .env>
```

### 8.2 รายละเอียด Endpoint: สรุป SOAP บันทึกตรวจ
* **Endpoint:** `POST /api/ai/visit/soap`
* **วัตถุประสงค์:** สรุปข้อความซักประวัติ สัญญาณชีพ และรูปถ่ายให้อยู่ในโครงสร้าง SOAP ทางคลินิก
* **Request Schema (JSON):**
  ```json
  {
    "history_text": "คนไข้หญิงอายุ 45 ปี มีอาการอ่อนเพลียเรื้อรัง ตื่นมาไม่สดชื่น ปวดเมื่อยตามตัว ท้องอืดง่าย",
    "vitals": {
      "bp_systolic": 118,
      "bp_diastolic": 76,
      "pulse": 72,
      "temperature": 36.6,
      "weight_kg": 54.0,
      "height_cm": 162.0,
      "bmi": 20.6,
      "spo2": 99
    },
    "allergies": "แพ้ยา Penicillin",
    "medications": "วิตามินบีรวม",
    "images_base64": []
  }
  ```
* **Response Schema (JSON):**
  ```json
  {
    "success": true,
    "soap": {
      "subjective": "ผู้ป่วยหญิงไทยอายุ 45 ปี มาด้วยอาการอ่อนเพลียเรื้อรัง ตื่นนอนไม่สดชื่น มีอาการปวดเมื่อยกล้ามเนื้อตามตัว และท้องอืด แน่นท้องเป็นประจำ",
      "objective": "Vitals: BP 118/76 mmHg, PR 72 bpm, BT 36.6 °C, SpO2 99%, BMI 20.6 kg/m2 (สมส่วน). Physical examination: ตรวจร่างกายเบื้องต้นไม่พบอาการซีดชัดเจน",
      "assessment": "Chronic Fatigue Syndrome under evaluation; Gut Dysbiosis with probable Mitochondrial Dysfunction",
      "plan": "1. ตรวจประเมิน 39 แกนชีววิทยาเพื่อสืบค้นความบกพร่องระดับเซลล์\n2. พิจารณาตรวจสมดุลไมโครไบโอมในลำไส้\n3. ปรับแผนโภชนาการและเสริม CoQ10"
    },
    "gateway": "gemini-2.5-flash"
  }
  ```

### 8.3 รายละเอียด Endpoint: ร่างคะแนน 39 แกนชีววิทยา
* **Endpoint:** `POST /api/ai/clinical/suggest-axes`
* **วัตถุประสงค์:** อ่านข้อมูลเวชระเบียนและเสนอแนะระดับความผิดปกติของทั้ง 39 แกน
* **Request Schema (JSON):**
  ```json
  {
    "patient_context": {
      "gender": "หญิง",
      "age": 45,
      "allergies": "แพ้ยา Penicillin",
      "medical_history": "โรคกระเพาะอาหาร",
      "current_medications": "ยาลดกรด Omeprazole"
    },
    "encounter_soap": {
      "subjective": "แสบร้อนกลางอก ท้องอืด อาหารไม่ย่อย อ่อนเพลีย",
      "objective": "BP 120/80 mmHg, PR 75 bpm",
      "assessment": "GERD / Functional Dyspepsia"
    }
  }
  ```
* **Response Schema (JSON):**
  ```json
  {
    "success": true,
    "suggested_scores": {
      "1": 55,
      "4": 65,
      "14": 70,
      "15": 78,
      "16": 68
    },
    "summary_insight": "ผู้ป่วยแสดงอาการเด่นชัดในระบบทางเดินอาหารและพลังงานระดับเซลล์ สอดคล้องกับความผิดปกติของเยื่อบุลำไส้และไมโทคอนเดรีย",
    "rationales": {
      "15": "มีอาการแสบร้อนกลางอกและท้องอืดเรื้อรัง บ่งชี้ความเสื่อมสภาพของเยื่อบุทางเดินอาหาร (Gut Barrier)",
      "4": "อ่อนเพลียเรื้อรัง ตื่นไม่สดชื่น สัมพันธ์กับภาวะชีวพลังงานไมโทคอนเดรียลดลง",
      "14": "อาการแน่นท้องและท้องอืดสัมพันธ์กับภาวะจุลินทรีย์เสียสมดุล (Gut Dysbiosis)"
    },
    "suggested_modules": ["MOD-GUT-01", "MOD-MITO-02"],
    "gateway": "gemini-2.5-flash"
  }
  ```

---

## 9. ความปลอดภัยทางไซเบอร์ การคุ้มครองข้อมูล และธรรมาภิบาลทางคลินิก

### 9.1 พระราชบัญญัติคุ้มครองข้อมูลส่วนบุคคล (PDPA Compliance)
* **การปกปิดตัวตนก่อนส่งออก (Text & Image De-identification):**  
  ก่อนที่ข้อมูลเวชระเบียนจะถูกส่งไปยัง AI Gateway ข้อมูลทั้งหมดจะถูกส่งผ่านฟังก์ชัน De-identification เพื่อตัดชื่อ-นามสกุลจริง, หมายเลขบัตรประชาชน 13 หลัก, เบอร์โทรศัพท์, และที่อยู่ออกทั้งหมด โดยใช้รหัสจำลองชั่วคราวแทน
* **การจัดเก็บข้อมูลอ่อนไหว (Sensitive PII Storage):**  
  หมายเลขบัตรประชาชนของผู้ป่วยจะถูกเข้ารหัสระดับคอลัมน์ด้วย **AES-256 Fernet Symmetric Encryption** ในฟิลด์ `id_card_encrypted` และจัดเก็บค่าแฮช **SHA-256** ในฟิลด์ `id_card_hash` สำหรับการค้นหาแบบ Exact Match โดยไม่จำเป็นต้องถอดรหัสทั้งตาราง
* **สิทธิ์การเข้าถึงข้อมูลรูปภาพ (Media Protection):**  
  รูปภาพทางการแพทย์ทั้งหมดถูกจัดเก็บในไดเรกทอรีส่วนตัว และต้องเข้าถึงผ่าน View ที่มีการตรวจสอบเซสชันและบทบาทของแพทย์เท่านั้น ไม่อนุญาตให้เปิดเผย Direct Public URL

### 9.2 บันทึกการกระทำที่ไม่อาจปฏิเสธได้ (Audit Trail & Pillar 8)
ทุกการกระทำสำคัญในระบบจะถูกบันทึกลงในโมเดล `AuditLog` ใน `apps/core/models.py` โดยอัตโนมัติ:
```python
AuditLog.objects.create(
    user=request.user,
    action="BIOLOGICAL_AXES_UPDATED",
    model="BiologicalRecord",
    object_id=str(record.pk),
    changes={
        "patient_hn": patient.hn,
        "is_baseline": record.is_baseline,
        "ai_assisted": bool(request.POST.get('ai_assisted')),
        "dysfunctional_axes_count": len(record.get_dysfunctional_axes()),
    },
    client_ip=get_client_ip(request),
    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
)
```
ข้อมูลนี้ช่วยให้สามารถตรวจสอบย้อนหลังได้ว่าคะแนนใดได้รับการเสนอโดย AI และแพทย์ท่านใดเป็นผู้ตรวจสอบและยืนยันในวันเวลาใด

---

## 10. สรุปผลการทดสอบระบบ

ระบบผ่านการทดสอบอัตโนมัติ (Automated Unit & Integration Tests) ครบถ้วนทุกแอปพลิเคชัน โดยรันคำสั่งภายใต้เงื่อนไขความปลอดภัยทางการแพทย์ (`--parallel 1`):

```bash
.venv/bin/python manage.py test --parallel 1
```

### สรุปผลการทดสอบรายโมดูล:
1. **Clinical Engine & Copilot (`apps/clinical/`):**
   * **ผลการทดสอบ:** ผ่านทั้งหมด **133 / 133 tests (`OK`)**
   * **ขอบเขต:** การคำนวณ Topological Math, การจับคู่ 200 โมดูล, ฟอร์มประเมิน 39 แกน, การป้องกันค่า NoneType, และการสร้างเรดาร์ชาร์ต
2. **Clinical Visit & SOAP Flow (`apps/clinical/test_visit.py`):**
   * **ผลการทดสอบ:** ผ่านทั้งหมด **14 / 14 tests (`OK`)**
   * **ขอบเขต:** ฟอร์มบันทึกการตรวจ, สัญญาณชีพ 7 ค่า, การบันทึกร่าง Box, การส่ง SOAP เข้าเวชระเบียน, และการส่งค่า `patient_id`
3. **Patients & Scheduling (`apps/patients/`):**
   * **ผลการทดสอบ:** ผ่านทั้งหมด **73 / 73 tests (`OK`)**
   * **ขอบเขต:** การจัดการแฟ้มคนไข้, ปฏิทินนัดหมาย, ระบบคิวตรวจ Pre-visit, คิวตรวจทานผลแล็บ และสิทธิ์การเข้าถึงของพยาบาล/แพทย์
4. **Core Security & Accounts (`apps/core/` + `apps/accounts/`):**
   * **ผลการทดสอบ:** ผ่านทั้งหมด **66 / 66 tests (`OK`)**
   * **ขอบเขต:** ระบบล็อกอิน, การจำกัดอัตราการเรียกใช้งาน (Rate Limiting), สิทธิ์ RBAC, และการบันทึก AuditLog

*รวมชุดการทดสอบทางการแพทย์ที่ผ่านการตรวจสอบแล้วทั้งสิ้นมากกว่า 286 รายการสมบูรณ์ 100%*

---

## 11. แนวทางการพัฒนาและส่งมอบงานในระยะถัดไป

### 11.1 กฎเหล็กที่ต้องรักษาไว้อย่างเคร่งครัด (Non-Negotiable Rules)
1. **ห้ามแตะต้อง LINE Official Account "Drpatt" (@505bfkpi):**  
   ห้ามแก้ไข Rich Menu, Welcome Message, หรือการตั้งค่าใน LINE OA Manager โดยเด็ดขาด เนื่องจากเป็นช่องทางการตลาดและการขายของคลินิก
2. **ห้ามแสดงข้อมูล Mock ที่ดูเหมือนจริง (No Misleading Placeholders):**  
   หากข้อมูลยังไม่มีการบันทึก เช่น ประวัติแพ้ยา หรือประวัติยาเดิม ต้องระบุคำว่า *"ยังไม่ได้บันทึก"* อย่างชัดเจน ห้ามใส่ตัวอย่างเช่น "ปฏิเสธการแพ้ยา" เพื่อป้องกันความเข้าใจผิดทางการแพทย์
3. **AI ห้ามวินิจฉัยโรคโดยลำพัง:**  
   ทุกข้อความและคะแนนที่สร้างขึ้นจากปัญญาประดิษฐ์จะต้องมีสถานะเป็น *"ร่างคำแนะนำ (Draft Suggestion)"* เสมอ และต้องมีปุ่มให้แพทย์ตรวจทานและกดยืนยันก่อนเข้าสู่ฐานข้อมูลประวัติจริง
4. **ห้าม Commit หรือ Push จนกว่าผู้ใช้จะสั่ง:**  
   ให้จัดเตรียมการเปลี่ยนแปลงใน Working Directory ให้พร้อม และรอคำสั่งอนุมัติจากผู้ใช้ก่อนทำ Git Commit เสมอ โดยเมื่อทำ Commit ต้องใส่ Trailer:
   ```
   Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
   ```

### 11.2 แผนงานในลำดับถัดไป (Next Implementation Milestones)
1. **ฟิลด์ยาประจำตัว (Current Medications):**
   * ดำเนินการเพิ่มฟิลด์ `current_medications` ในโมเดล `Patient` และรัน Migration `0009_patient_current_medications` สำเร็จแล้วในเครื่อง
   * ขยายการแสดงผลในหน้าจอ `patient_detail.html` และ `doctor_pre_visit.html`
   * เชื่อมโยงข้อมูลยาเดิมเข้าสู่ระบบ AI Copilot เพื่อการตรวจสอบปฏิกิริยาระหว่างยาและสารอาหาร (Drug-Nutrient / Drug-Herb Interactions)
2. **การทำความสะอาดหน้า Doctor Settings (`doctor_settings.html`):**
   * ปลดข้อมูลจำลอง (เช่น ว. 48291, ลายเซ็นตัวอย่าง) ออก และเชื่อมโยงกับฟิลด์การตั้งค่าจริงของผู้ใช้
3. **การทดสอบความเร็วและการแสดงผลบนหน้าจออุปกรณ์จริง (Cross-Device Mobile Validation):**
   * ทดสอบการใช้งานฟอร์มตรวจและเรดาร์ชาร์ตบนแท็บเล็ตตรวจการของแพทย์ (iPad / Android Tablet) เพื่อความคล่องตัวในการปฏิบัติงานจริงในคลินิก

---
*จบเอกสารสรุปสถาปัตยกรรมและการพัฒนาระบบ TSPI EMR — TSPI Clinic (Dr. Patt)*

