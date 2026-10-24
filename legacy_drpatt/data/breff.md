TSPI AI Medical Platform
Scope of Work — Phase 0 & Phase 1
LINE OA Foundation · Telegram Bot · Patient Identity · Appointment AI

เอกสาร
Scope of Work — Phase 0 & Phase 1
เวอร์ชัน
v1.0  |  มีนาคม 2569
จัดทำโดย
ทีมพัฒนา TSPI Platform
ลูกค้า
ดร.ภัทร หนังสือ — TSPI Precision Medicine Clinic
สถานะ
Draft — รอยืนยัน Scope ก่อนเริ่ม Sprint
ระยะเวลารวม
Phase 0: 14 วัน  |  Phase 1: 30 วัน
งบประมาณ
Phase 0: รวมใน Phase 1  |  Phase 1: 25,000 บาท


Phase 0 — Pre-Development & Architecture Setup

ระยะเวลา
14 วัน
ไม่คิดแยก
รวมใน Phase 1

P0-01 · Unified Database Schema Design
รายละเอียดงาน
ออกแบบโครงสร้างฐานข้อมูลรวม โดยต่อยอดจาก DB เดิม (MariaDB — drpatrcl_system) และเพิ่ม schema ใหม่สำหรับ AI, Omics และ Multi-tenant รองรับการเติบโตในอนาคต

DB เดิมที่มี
MariaDB · 60 tables รวม user, appointment, his_medical, drug, formula, orders, chats
งานที่ต้องทำ
วิเคราะห์ table เดิม → ออกแบบ migration plan → เพิ่ม table ใหม่ที่จำเป็น
table ใหม่หลัก
bot_identity, ai_requests, ai_outputs, patient_consent, audit_logs, tspi_modules
เทคโนโลยี
MariaDB (เดิม) + PostgreSQL (ใหม่สำหรับ AI/Omics) + Redis (Cache/Queue)



สิ่งที่ลูกค้าจะได้รับ
    • ER Diagram ฉบับสมบูรณ์ (PDF + PNG)
    • Migration Script สำหรับ DB เดิม (ไม่กระทบข้อมูลที่มีอยู่)
    • Schema Document อธิบาย table ใหม่ทุกตัว

หมายเหตุ
    • ข้อมูลเดิมใน MariaDB ไม่ถูกแตะต้องหรือ migrate ในเฟสนี้
    • เพิ่ม table ใหม่แบบ additive ไม่แก้ไข table เดิม


P0-02 · Tech Stack & Environment Setup
รายละเอียดงาน
ติดตั้งและกำหนด Environment สำหรับทีม Dev พร้อม CI/CD pipeline เบื้องต้น

Backend API
PHP8 MVC & Python FastAPI — รองรับ async, AI integration, LINE/Telegram webhook
Frontend
NextJS (App Router) — Doctor Dashboard & Admin Panel
Database
MariaDB (เดิม) + PostgreSQL 16 (ใหม่) + Redis 7
AI Engine
Claude API (Anthropic) — claude-sonnet-4-6 & PlexityAI
Bot Channel
LINE Messaging API (OA หลัก) + Telegram Bot API (ขนาน)
File Storage
Cloudflare R2 หรือ AWS S3 (lab results, images, PDFs)
Deployment
Docker Compose (Dev) → VPS หรือ Cloud (Prod)
Dev Tools
Git, GitHub Actions CI, Postman, Swagger UI

สิ่งที่ลูกค้าจะได้รับ
    • Repository structure พร้อม README
    • Docker Compose file สำหรับ local dev
    • .env template ทุก service
    • Swagger/OpenAPI spec เบื้องต้น




P0-03 · LINE OA + Telegram Bot Planning
รายละเอียดงาน
วางแผนสถาปัตยกรรม Dual-channel Bot — LINE OA (หลัก) และ Telegram (รอง) โดยใช้ Webhook เดียวกัน รองรับการขยาย channel ในอนาคต

LINE OA
2 OA — Medical OA (คนไข้) + Commerce OA (ออเดอร์) → Channel Router ส่งไปถูก service
Telegram Bot
1 Bot — ช่องทางสำรองสำหรับคนไข้ที่ไม่ใช้ LINE หรือต่างชาติ
Channel Router
ตัวกลางรับ Message จากทุก channel → dispatch ไปยัง handler ที่ถูกต้อง
Patient Identity
LINE userId / Telegram chatId ผูกกับ userID ใน DB เดิม ผ่าน LIFF (LINE) / deep link (Telegram)

สิ่งที่ลูกค้าจะได้รับ
    • Architecture Diagram — Dual-channel Bot Flow
    • Channel Router Design Document
    • PDPA & Consent Planning Document




P0-04 · RBAC & Permission Planning
รายละเอียดงาน
ออกแบบระบบสิทธิ์ผู้ใช้งานทุกระดับ ครอบคลุม Web Dashboard, Bot, และ API

Super Admin
สิทธิ์ทุกอย่าง — ดู/แก้ไข/ลบ — จัดการ branch และ user ทุกระดับ
Medical Director
Review AI high-risk output, approve clinical templates, access all cases
Attending Physician
Full AI workspace สำหรับเคสที่รับผิดชอบ, สั่งวิเคราะห์ทุกเมนู
แพทย์แผนไทย
Analysis ด้าน symptoms/lifestyle/modules — ไม่ finalize ยาแผนปัจจุบันลำพัง
Case Manager
Timeline, symptom, adherence, QOL summaries — ไม่เข้า PGx/high-risk
คนไข้ (User)
Chat bot, นัดหมาย, ดูผลตัวเอง, สั่งซื้อสินค้า

สิ่งที่ลูกค้าจะได้รับ
    • RBAC Matrix Table (PDF)
    • Permission schema ในฐานข้อมูล


Phase 1 — LINE OA + Telegram Bot + Patient Identity + Appointment AI

ระยะเวลา
30 วัน
งบประมาณ
25,000 ฿

Phase 1 เป็นหัวใจของ Patient-facing System ทั้งหมด ทุก feature ใน Phase นี้เชื่อมกับ DB เดิมโดยตรง และถูกออกแบบให้รองรับ Phase 2 (AI Engine) ในอนาคต



P1-01 · LINE OA Foundation & Dual-Channel Integration
รายละเอียดงาน
เชื่อม LINE OA ทั้ง 2 ตัว (Medical + Commerce) เข้า Webhook server เดียวกัน พร้อม Channel Router ที่ทำงานอัตโนมัติ

ชื่องาน
LINE OA Foundation & Channel Router
LINE OA 1
Medical OA — รับ message เรื่องนัดหมาย ซักประวัติ ติดตามผล
LINE OA 2
Commerce OA — รับออเดอร์ ชำระเงิน ติดตามพัสดุ
Channel Router
รับ Webhook → ตรวจ OA source → dispatch ไปถูก handler
Patient Identity
LIFF Registration → ผูก LINE userId กับ userID ใน table `user` ของ DB เดิม
เทคโนโลยี
FastAPI Webhook + LINE Messaging API SDK + LIFF 2.0

สิ่งที่ลูกค้าจะได้รับ
    • LINE OA 2 ตัว เชื่อม Webhook พร้อมใช้งาน
    • Channel Router ที่ route message ถูก OA โดยอัตโนมัติ
    • LIFF Registration Page — คนไข้ผูก LINE กับระบบได้
    • Patient Identity linking เสร็จสมบูรณ์
หมายเหตุ
    • LINE OA ทั้ง 2 ต้องมี Channel Access Token แล้ว (หมอเตรียม)
    • สามารถเพิ่ม LINE OA ตัวที่ 3 ได้ในอนาคตโดยไม่ต้อง refactor
สิ่งที่แก้ไขได้
    • จำนวน LINE OA — เพิ่ม/ลดได้
    • ชื่อและ flow ของแต่ละ OA — ปรับได้ตาม feedback




P1-02 · Telegram Bot Foundation
รายละเอียดงาน
สร้าง Telegram Bot ขนานกับ LINE OA ใช้ codebase เดียวกัน แค่ต่าง adapter layer — รองรับคนไข้ต่างชาติหรือที่ไม่ได้ใช้ LINE

ชื่องาน
Telegram Bot Foundation
ฟังก์ชันใน Phase 1
รับ message, ผูก Patient Identity, นัดหมาย, ดูข้อมูลตัวเอง
ฟังก์ชันเพิ่ม Phase 2+
AI ซักประวัติ, ผล Lab, แนะนำ Module, สั่งซื้อ
Shared Logic
ใช้ Business Logic เดียวกับ LINE ทุกอย่าง — เพียงแต่ I/O ต่างกัน
เทคโนโลยี
python-telegram-bot (async) + Deep Link สำหรับ Patient Identity

สิ่งที่ลูกค้าจะได้รับ
    • Telegram Bot พร้อมใช้งาน — /start, /appointment, /myrecord, /help
    • Patient Identity linking ผ่าน Telegram deep link
    • Bot ตอบได้ทั้งภาษาไทยและอังกฤษ
หมายเหตุ
    • ต้องสร้าง Bot Token ผ่าน @BotFather ก่อน (5 นาที)
    • Telegram Bot ใช้ feature เดียวกับ LINE แต่ UI/UX ต่างกันตามข้อจำกัด platform
สิ่งที่แก้ไขได้
    • ชื่อ Bot, คำทักทาย, เมนู /command — ปรับได้
    • ภาษาที่รองรับ — เพิ่มได้ในอนาคต

P1-03 · AI Patient Intake — ซักประวัติผ่านแชท
รายละเอียดงาน
AI ซักประวัติเบื้องต้นผ่าน LINE/Telegram ก่อนพบแพทย์ — บันทึกลง his_medical ของ DB เดิมอัตโนมัติ

ชื่องาน
AI Patient Intake Chatbot
ขั้นตอน
1) คนไข้เริ่มแชท → 2) AI ถามอาการ → 3) AI QC ตรวจความครบถ้วน → 4) บันทึก his_medical
AI Engine
Claude API — Prompt Engineering สำหรับซักประวัติแพทย์แผนไทย
เชื่อมกับ DB เดิม
table: his_medical, user, appointment — ใช้ userID เดิมทุกตัว
ภาษา
ไทย (หลัก) + อังกฤษ (รอง)
AI QC
ตรวจว่าข้อมูลครบหรือไม่ ถามซ้ำถ้าคำตอบไม่ชัดเจน

สิ่งที่ลูกค้าจะได้รับ
    • AI Intake Bot ทำงานผ่าน LINE และ Telegram
    • ข้อมูลซักประวัติบันทึกลง his_medical อัตโนมัติ
    • Prompt Library สำหรับโรคหลักที่คลินิกรักษา
    • AI QC ตรวจความครบถ้วนก่อนส่งแพทย์
หมายเหตุ
    • ต้องการ Prompt Template จากหมอสำหรับโรคแต่ละกลุ่ม (หมอเตรียม)
    • AI Intake ไม่วินิจฉัยโรค — ทำหน้าที่เก็บข้อมูลเท่านั้น
สิ่งที่แก้ไขได้
    • คำถามในแต่ละ Flow — แก้ไขได้ไม่จำกัดครั้ง
    • เพิ่ม Flow ใหม่สำหรับโรคเพิ่มเติมได้ใน Phase 2


P1-04 · Voice-to-Form — บันทึกเสียงสนทนาแพทย์-คนไข้
รายละเอียดงาน
แพทย์หรือคนไข้ส่ง Voice Message ผ่าน LINE/Telegram → ระบบแปลงเป็น Text → AI สรุปเป็น Structured Data → บันทึกลง his_medical

ชื่องาน
Voice-to-Form Medical Transcription
Input
Voice Message จาก LINE หรือ Telegram (ไฟล์ .m4a / .ogg)
STT Engine
OpenAI Whisper API (Thai support ดีมาก) หรือ Google Speech-to-Text
AI Processing
Claude API แปลง transcript เป็น structured medical note
Output
JSON → บันทึกลง his_medical อัตโนมัติ

สิ่งที่ลูกค้าจะได้รับ
    • รับ Voice Message ผ่านทั้ง LINE และ Telegram
    • แปลงเสียงเป็น Medical Note อัตโนมัติ
    • บันทึกลงฐานข้อมูลพร้อม timestamp
หมายเหตุ
    • ค่าใช้จ่าย STT API คิดแยกตาม usage (ไม่รวมในค่าพัฒนา)
    • ความแม่นยำขึ้นกับคุณภาพเสียงและสำเนียง
สิ่งที่แก้ไขได้
    • เลือก STT provider ได้ตามความต้องการ
    • format ของ Medical Note ที่ได้ — ปรับ template ได้



P1-05 · Lab Result OCR — อ่านผลแล็บจากรูปภาพ
รายละเอียดงาน
คนไข้ถ่ายรูปผลแล็บส่งมาทาง LINE/Telegram → AI อ่านค่าจากรูป → บันทึกลง doc_blood_test ของ DB เดิม

ชื่องาน
Lab Result OCR & Auto-Import
Input
รูปภาพ (.jpg/.png) ผลเลือด, ผลแล็บ, ใบรายงานแพทย์
OCR Engine
Claude Vision API (อ่านภาษาไทย-อังกฤษ) + structured extraction
เชื่อมกับ DB เดิม
table: doc_blood_test_th, doc_blood_test_en
AI QC
ตรวจสอบค่าที่อ่านได้ — แจ้งถ้าไม่ชัดเจน
Output
ค่าแล็บ structured JSON → บันทึก DB + แจ้งแพทย์

สิ่งที่ลูกค้าจะได้รับ
    • ระบบรับรูปผลแล็บผ่าน LINE และ Telegram
    • AI อ่านค่าและบันทึกลง DB อัตโนมัติ
    • แจ้งเตือนแพทย์เมื่อมีผลแล็บใหม่เข้า
    • แจ้งคนไข้ถ้ารูปไม่ชัด/ต้องถ่ายใหม่
หมายเหตุ
    • รองรับผลแล็บมาตรฐานของไทยเป็นหลัก
    • ผลแล็บบางรูปแบบอาจต้อง manual review
สิ่งที่แก้ไขได้
    • เพิ่ม template สำหรับแล็บรูปแบบใหม่ได้
    • ปรับ confidence threshold สำหรับ auto-accept




P1-06 · PDPA Consent Management
รายละเอียดงาน
ระบบ Consent สำหรับ PDPA ครอบคลุมทุก channel — LINE, Telegram, Web — บันทึก audit trail ทุกครั้งที่ consent

ชื่องาน
PDPA Consent Management System
Consent Types
การเก็บข้อมูลสุขภาพ / การใช้ AI วิเคราะห์ / การจัดเก็บระยะยาว / การวิจัย (de-identified)
Channel
LINE (Flex Message) + Telegram (Inline Keyboard) + Web (LIFF)
Audit Trail
บันทึก consent_at, channel, version, ip ทุกครั้ง
Withdraw
คนไข้สามารถ withdraw consent ได้ — ระบบ mask data ที่เกี่ยวข้อง

สิ่งที่ลูกค้าจะได้รับ
    • Consent Flow ทำงานทุก channel ก่อนใช้งานระบบ
    • Consent Version Management — อัปเดต policy ได้
    • Audit Log ทุก consent action
    • Withdraw consent flow
หมายเหตุ
    • ต้องการ Consent Text ภาษาไทยจากหมอหรือทนายความ (หมอเตรียม)
    • ระบบนี้เป็น baseline สำหรับ Genomics/Omics consent ใน Phase 2

P1-07 · Appointment Intelligence Module
รายละเอียดงาน
ระบบนัดหมายอัจฉริยะผ่าน LINE/Telegram เชื่อมกับ table appointment และ doctor_schedule ของ DB เดิม

ชื่องาน
Smart Appointment Bot
เชื่อมกับ DB เดิม
table: appointment, doctor, doctor_schedule, doctor_schedule_limit
Smart Scheduling
Bot แนะนำเวลาว่างที่เหมาะสม ไม่ double-book
Pre-visit Summary
ดึงประวัติคนไข้ส่งแพทย์ก่อนพบ 30 นาที อัตโนมัติ
Auto Follow-up
Bot ทักทายหลังพบแพทย์ 3/7/30 วัน
No-show Alert
แจ้งเตือนแพทย์และ admin ถ้าคนไข้ไม่มาตามนัด
Reminder
แจ้งเตือนคนไข้ก่อนนัด 1 วันและ 1 ชั่วโมงผ่าน LINE + Telegram

สิ่งที่ลูกค้าจะได้รับ
    • Bot รับนัดหมายอัตโนมัติ 24/7 ผ่าน LINE และ Telegram
    • ตรวจสอบตารางแพทย์แบบ real-time
    • Pre-visit Summary ส่งแพทย์อัตโนมัติ
    • Reminder + Follow-up ครบทุก touchpoint
    • Admin Dashboard ดูสถานะนัดหมายทั้งหมด
หมายเหตุ
    • ข้อมูลตารางแพทย์ (doctor_schedule) ต้องอัปเดตในระบบก่อน
    • Pre-visit Summary อิงจากข้อมูลที่มีใน his_medical เท่านั้น
สิ่งที่แก้ไขได้
    • ระยะเวลา reminder — ปรับได้ตามต้องการ
    • รูปแบบ Pre-visit Summary — ปรับ template ได้
    • เพิ่มแพทย์ได้ไม่จำกัด


P1-08 · Module Master Data Entry System
รายละเอียดงาน
Admin UI สำหรับกรอกข้อมูล TSPI Modules ทั้ง 200 Module — เป็นฐานข้อมูลที่ AI Phase 2 จะใช้แนะนำการรักษา

ชื่องาน
TSPI Module Master Data Admin
ข้อมูลต่อ Module
ชื่อ, หมวด, สรรพคุณ, ข้อบ่งชี้, ข้อห้าม, ค่าเลือดที่คาดว่าจะเปลี่ยน, ความปลอดภัย
จำนวน Module
200 Modules (หมอเตรียมข้อมูล → กรอกผ่าน Admin UI)
Import
รองรับ Excel/CSV import สำหรับกรอกจำนวนมาก
เชื่อมกับ
table: tspi_modules (ใหม่) เตรียมไว้สำหรับ Phase 2 AI Engine

สิ่งที่ลูกค้าจะได้รับ
    • Admin UI กรอก/แก้ไข Module ได้ง่าย
    • Excel Import สำหรับกรอกข้อมูลครั้งเดียวจำนวนมาก
    • Module Database พร้อมสำหรับ AI Engine Phase 2
หมายเหตุ
    • ข้อมูล Module ทั้ง 200 ตัว — หมอต้องเตรียมก่อน Phase 1 สิ้นสุด
    • Module data เป็น foundation ของ Phase 2 ทั้งหมด — ยิ่งครบยิ่งดี
สิ่งที่แก้ไขได้
    • เพิ่ม field ใหม่ใน Module ได้ใน Phase 2
    • จำนวน Module — ไม่จำกัด


P1-09 · Basic AI Audit Trail
รายละเอียดงาน
ระบบบันทึก log ทุก action ของ AI และ user ใน Phase 1 — เป็น foundation สำหรับ Governance ใน Phase 2+

ชื่องาน
Basic AI Audit Trail
บันทึกอะไร
user action, AI request/response, channel, timestamp, patient_id, model_version
Storage
PostgreSQL table: audit_logs (append-only)
Viewer
Admin Dashboard — filter/search audit log
Retention
เก็บ 2 ปี (configurable)

สิ่งที่ลูกค้าจะได้รับ
    • Audit Log ทุก AI action จาก Phase 1 เป็นต้นไป
    • Admin Audit Viewer — ค้นหาตาม user/date/action

สรุปงาน Phase 0 & Phase 1

รหัส
ชื่องาน
ระยะเวลา
LINE
Telegram
P0-01
Database Schema Design
3–4 วัน
—
—
P0-02
Tech Stack & Environment
2–3 วัน
—
—
P0-03
Bot Planning & Architecture
2–3 วัน
✓
✓
P0-04
RBAC & Permission Planning
2–3 วัน
—
—
P1-01
LINE OA Foundation & Channel Router
10–14 วัน
✓
—
P1-02
Telegram Bot Foundation
7–10 วัน
—
✓
P1-03
AI Patient Intake Bot
10–14 วัน
✓
✓
P1-04
Voice-to-Form Transcription
7–10 วัน
✓
✓
P1-05
Lab Result OCR
7–10 วัน
✓
✓
P1-06
PDPA Consent Management
5–7 วัน
✓
✓
P1-07
Appointment Intelligence
10–14 วัน
✓
✓
P1-08
Module Master Data Admin
7–10 วัน
—
—
P1-09
Basic AI Audit Trail
3–5 วัน
✓
✓


สิ่งที่หมอต้องเตรียมก่อนเริ่ม Phase 1

#
รายการ
รายละเอียด
ต้องการก่อน
1
LINE OA Channel Access Token (2 ตัว)
Medical OA + Commerce OA
วันแรก Phase 0
2
Telegram Bot Token
สร้างผ่าน @BotFather
วันแรก Phase 0
3
Claude API Key (Anthropic)
สมัครที่ console.anthropic.com
ก่อน P1-03
4
PDPA Consent Text ภาษาไทย
ร่างโดยหมอหรือทนายความ
ก่อน P1-06
5
Intake Questions ต่อกลุ่มโรค
คำถามซักประวัติแต่ละโรค
ก่อน P1-03
6
Module Master Data (200 Modules)
Excel/CSV พร้อมทุก field
ก่อนสิ้นสุด P1
7
Server / VPS สำหรับ Deploy
Linux VPS มี public IP
ก่อน P1-01


TSPI AI Medical Platform — Phase 0 & Phase 1 Scope of Work
เอกสารนี้เป็นส่วนหนึ่งของ Proposal v3 Final  ·  จัดทำโดยทีมพัฒนา TSPI
เอกสารนี้เป็นส่วนหนึ่งของ Proposal v3 Final  ·  จัดทำโดยทีมพัฒนา TSPI