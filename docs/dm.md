# Handoff: TSPI EMR (Dr. Patt) — งานรอบ 9 พ.ย. 2026 (อัปเดตสถานะ 13 พ.ย.)

ไฟล์นี้สรุปงานให้ AI agent ตัวถัดไปทำต่อได้ทันที อ่านให้ครบก่อนแก้โค้ด

---

## 1. โปรเจกต์คืออะไร

ระบบเวชระเบียน (EMR) ของ TSPI Clinic (แพทย์แผนบูรณาการ "39 แกนชีววิทยา") + หน้าเว็บสาธารณะ + บอท LINE OA

- **Django 6** (`apps/`: patients, clinical, intelligence, accounts, core, portal_patient) + **Bootstrap 5.3 + Alpine.js 3 + HTMX** (ไฟล์ในเครื่องทั้งหมด ไม่โหลดจาก CDN, CSP = `'self'`)
- **FastAPI `ai_service/`** เป็นประตูไป LLM (Groq / Gemini / DeepSeek / OpenAI) เรียกจาก Django เท่านั้น ต้องส่ง header `X-Internal-Token`
- ฐานข้อมูล PostgreSQL (เครื่อง dev ใช้ค่าจาก `.env`), deploy ด้วย docker compose บน VPS ทดลอง: `cd /opt/tspi && ./scripts/deploy.sh` (ผู้ใช้ deploy เอง)
- ภาษาในระบบ: ไทยเป็นหลัก ผู้ใช้สื่อสารภาษาไทย

## 2. สถานะ git (อัปเดต 13 พ.ย. 2026)

- งานทั้งหมดในไฟล์นี้ **commit และ push แล้ว** (13 commit ต่อจาก e9f1d17 ถึง `552e60a`, 11 พ.ย.) รวมงานที่ AI อีกตัวทำต่อ:
  หน้าคุยกับ AI แบบ Gemini (`/ai/`, `/patient/assistant/`), Flex card / Quick Reply ใน LINE, ฟิลด์ยาประจำตัว (`Patient.current_medications`, migration 0009), ล้างข้อมูลปลอมในหน้าตั้งค่าแพทย์, แก้ HTTP 500 หลายหน้า — รายละเอียดใน `docs/sumsum.md`
- 13 พ.ย.: พบ `templates/portal_patient/assistant.html` ถูกแก้ค้างครึ่งทาง (ของเดิมกับของใหม่ซ้อนกันเป็นสองชุด, คลาส CSS ใหม่ยังไม่มี) จึง**คืนเป็นเวอร์ชันที่ commit แล้ว** ไอเดียที่ทิ้งไว้ในฉบับค้าง: ช่องพิมพ์บนหน้าแรก, ปุ่มเลือกโหมดคุย, ปุ่ม "ส่งให้ทีมแพทย์ตรวจ" — ถ้าจะทำต่อให้เริ่มใหม่จากไฟล์ปัจจุบัน
- กฎ: **อย่า commit/push จนกว่าผู้ใช้สั่ง**
- ไฟล์ที่ไม่เกี่ยว อย่าใส่ใน commit: `.claude/`, `39 แกนชีวภาพ × 42 หมวดผลิตภัณฑ์ — ตารางจับคู่ต.xlsx`
- เวลา commit ต้องปิดท้ายข้อความด้วย `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
- ไม่ทราบว่า VPS deploy ถึง commit ไหนแล้ว ถามผู้ใช้ก่อน (ต้องรัน migration patients 0008 และ 0009)

## 3. กฎที่ผู้ใช้กำหนด (ห้ามฝ่าฝืน)

- **ห้ามแตะ Rich Menu / ข้อความต้อนรับ / ตั้งค่าใน LINE OA Manager** ของ OA "Drpatt" (@505bfkpi) เป็นช่องทางขายของฝ่ายขาย บอทเปิดด้วยการพิมพ์ "เปิดบอท" และชวนคนไข้ผ่าน QR / ลิงก์ / เจ้าหน้าที่ของเราเอง
- **อย่าทำงานนาน ๆ เช่น build Docker / วนตรวจซ้ำยาว ๆ โดยไม่ถามก่อน**
- งาน VPS (backup, SMTP, ตั้งราคา AI) เลื่อนไว้ เพราะ VPS เป็นเครื่องทดลอง แต่ต้องตั้ง `AI_PRICE_*` ก่อนเปิด QR/ปุ่มบอทให้คนไข้ทั่วไป
- ผู้ใช้ต้องการคุณภาพ ("อย่าเน้นแต่งานไว") ทดสอบในเบราว์เซอร์จริงก่อนบอกว่าเสร็จ
- **AI ห้ามวินิจฉัยโรค** ทุกจุดที่ AI ร่างข้อมูล ต้องมีคนตรวจทานและยืนยันก่อนเข้าเวชระเบียนเสมอ
- **ห้ามแสดงข้อมูลตัวอย่าง/ค่าตั้งต้นที่ดูเหมือนข้อมูลจริงของคนไข้** ไม่มีข้อมูลต้องบอกตรง ๆ (เช่น "ยังไม่ได้บันทึกประวัติแพ้ยา — ต้องถาม")
- ห้ามลบข้อมูลทางการแพทย์ (โมเดลส่วนใหญ่เป็น `SoftDeleteModel`) ลบรูป/ทิ้งร่าง = ซ่อน ไม่ลบไฟล์

## 4. งานที่ทำในรอบ 9 พ.ย. (commit แล้ว)

### 4.1 UI ใหม่ (ดูรายละเอียด `docs/UI_REDESIGN_2026-11.md`)
- **หน้าเว็บสาธารณะ** แนว Meditex (เขียว `#4A7A06`, มุม 3px, หัวข้อสองน้ำหนัก): `static/css/site.css`, `templates/layouts/public_base.html`, `templates/core/home.html`
- **ระบบภายใน** แนว Medicare web admin (เมนูข้าง/แถบบนเป็นการ์ดลอยบนพื้น `#F3F3F3`, สีหลักส้มอิฐ `#A5633A`, มีโหมดมืด): `static/css/admin.css` (ทุกกฎอยู่ใต้ `body.adm`), `templates/layouts/doctor_base.html`, `templates/layouts/_doctor_nav.html` (เมนูใช้ร่วมจอใหญ่+มือถือ)
- ฟอนต์ Sarabun (Nunito/Inter ไม่มีตัวไทย) ไม่ได้คัดลอกโค้ด/รูปจากเทมเพลตต้นแบบ (เป็นของมีลิขสิทธิ์)
- หน้าที่ทำโครงใหม่แล้ว: Dashboard, รายชื่อคนไข้, แฟ้มคนไข้, แชท LINE (list + detail แบบ 3 แผง), ปฏิทินนัด, คิวคนไข้วันนี้, งานรอตรวจทาน หน้าอื่นใช้ธีมใหม่แต่ HTML เดิม

### 4.2 ฟอร์มบันทึกการตรวจ (หน้าแฟ้มคนไข้)
สัญญาณชีพ 7 ช่อง (บังคับ มีช่วงค่า) → ช่องซักประวัติ (พิมพ์ / ไมค์ถอดเสียงในเบราว์เซอร์ th-TH / กล้อง / อัปโหลด ≤6 รูป) → **Gemini สรุป SOAP** ลงช่อง SOAP ที่ล็อกเทาไว้ → ติ๊ก "ตรวจทานแล้ว" + SweetAlert ยืนยัน → `PatientHistory` (มี vitals + BMI)
- ร่าง = `Box` (source CLINIC, `contents.origin='visit'`, DRAFT) หนึ่งกล่องต่อผู้ใช้ต่อคนไข้ บันทึกอัตโนมัติ
- โค้ด: `apps/clinical/services_visit.py`, `apps/patients/views_visit.py`, `templates/patients/partials/visit_form.html`, `static/js/visit_form.js`, `VisitVitalsForm` ใน `apps/patients/forms.py`
- ai_service: `POST /api/ai/visit/soap` (Gemini เสมอ ไม่ขึ้นกับ `AI_SOAP_PROVIDER`), ลบข้อมูลระบุตัวตนในข้อความ + ลบ EXIF/เบลอหน้าในรูปก่อนส่ง, guardrail ห้ามฟันธงโรค; `gateway.call_gemini_json()` ส่ง key ทาง header
- พยาบาลและแพทย์บันทึกได้ทั้งคู่ ไมค์/กล้องจริงยังไม่ได้ทดสอบ (ต้องกดอนุญาตในเบราว์เซอร์)
- `?visit=1#new-soap` ใน URL แฟ้มคนไข้ = เปิดฟอร์มทันที

### 4.3 ปฏิทินนัดหมาย (`/doctor/appointments/`)
ปฏิทินรายเดือน (พ.ศ.) กดวันแล้วเลื่อนลงไปรายการของวันนั้น (ข้อมูลทั้งเดือนส่งมากับหน้า ไม่โหลดใหม่), เปลี่ยนสถานะนัด (รอยืนยัน/ยืนยันแล้ว/มาตรวจแล้ว/ยกเลิก), ฟอร์มสร้างนัดใหม่: เลือกแพทย์ (เดิมบั๊กใส่ชื่อคนกด), ปุ่มเวลาทุก 30 นาที, กันนัดย้อนหลัง/ชนคิวแพทย์/คนไข้ซ้ำ
- โค้ด: `apps/patients/views_appointments.py`, `AppointmentForm` ใน forms.py, `static/js/appointments.js`
- `api_patient_search` ค้นชื่อเต็มหลายคำได้ + คืน `gender_code`

### 4.4 คิวคนไข้วันนี้ (`/doctor/pre-visit/`, เดิม "ซักประวัติล่วงหน้า")
เดิมแสดงข้อความตัวอย่างเหมือนจริง (เช่น "ปฏิเสธการแพ้ยา") → ทำใหม่: ซ้าย = นัดของวัน (+ค้นหาคนไข้ walk-in), ขวา = สรุปจากข้อมูลจริง (แพ้ยา, อาการ, การตรวจล่าสุด, แชท LINE ค้าง, แกนผิดปกติ ≥60, ผลแล็บรอตรวจ, นัดถัดไป), ปุ่ม "เริ่มตรวจ" = นัด→มาตรวจแล้ว แล้วเปิดฟอร์มบันทึกการตรวจ
- โค้ด: `apps/patients/views_previsit.py`

### 4.5 งานรอตรวจทาน (`/staff/review-queue/`, เดิม "ตรวจทานเคส")
รวม 3 อย่าง: แชท LINE มีอาการ (ไปหน้าแชท) / ข้อความอาการที่คนไข้พิมพ์ตอนบอทปิด (`ClinicalReviewItem`) / ผลแล็บ-ผล AI รออนุมัติ (`AgenticArtifact` pending)
- อนุมัติ = เขียน SOAP เอง (S เติมข้อความคนไข้ให้) + ติ๊กตรวจทาน + SweetAlert (เดิมเขียนข้อความสำเร็จรูปลงแฟ้ม) — `ClinicalReviewItem.approve(..., soap=...)`
- ข้อความด่วน (Level 2) แพทย์เท่านั้นที่บันทึกหรือปิดได้ (ปิดทิ้งเดิมพยาบาลทำได้ = ช่องโหว่ แก้แล้ว)
- ตอนบอทเปิด ข้อความอาการเข้ารอบแชท LINE อย่างเดียว ไม่สร้าง `ClinicalReviewItem` ซ้ำ (`views_line_internal.ingest_line_event` คืน `routed_to_chat`)
- โค้ด: `apps/patients/views_staff.py` (`staff_review_queue_view`, `_review_hub_data`), `static/js/review_hub.js`

### 4.6 แก้บั๊กทั้งระบบ
- `[x-cloak]` ไม่เคยมีใน CSS + `x-show` แพ้คลาส `d-flex`/`d-block` ของ Bootstrap (`!important`) → เพิ่มกฎกลางใน `static/css/theme.css`: `[x-show][style*="display: none"] { display: none !important; }`
- `.list-group-item` ในธีมใหม่เคยโปร่งใส (dropdown ทับฟอร์ม) → พื้นทึบ
- เพิ่ม utility `.min-w-0` (Bootstrap ไม่มี)
- แถบบนลอย: เนื้อหาโผล่เหนือแถบตอนเลื่อน → แก้ด้วย `::before`
- SweetAlert2 v11.14.5 อยู่ที่ `static/vendor/sweetalert2/` โหลดทุกหน้าภายใน ถ้าเปิดบน Bootstrap modal ต้องใส่ `target: document.querySelector('.modal.show')` ไม่งั้น focus trap แย่งโฟกัส (ทำแล้วใน appointments.js / review_hub.js)
- Dashboard นับนัดวันนี้ไม่รวมนัดที่ยกเลิก

## 5. ข้อควรระวังเชิงเทคนิค (เจอมาแล้ว)

- **Alpine**: `:disabled="busy"` ที่ `busy = ''` จะถูกปิดใช้งาน → ใช้ `!!busy`; `$el` ใน method คือ element ที่กด ไม่ใช่ root
- **CSS ในหน้าภายใน** ใส่ใน `{% block extra_doctor_head %}` เท่านั้น ห้าม override `extra_head` (จะทำให้ admin.css หาย มีเทสต์จับ)
- สีลิงก์ใช้ `.adm :where(a:not(.btn,...))` เพื่อไม่ทับสีคอมโพเนนต์
- Static มี `?v={{ ASSET_VERSION }}` (ค่าตั้งตอนเปิดเซิร์ฟเวอร์) เบราว์เซอร์แคชไว้ ตอนทดสอบต้อง `fetch(url, {cache:'reload'})` แล้ว reload
- JSONField: `~Q(contents__key=True)` ตัดแถวที่ไม่มี key ทิ้ง → ใช้ `~Q(pk__in=subquery)`
- เทสต์ต้องรันแบบ `--parallel 1` (แบบขนานพังเพราะ pickle traceback)
- `Box.contents` ไม่ได้เข้ารหัส แต่หน้าแชท/กล่องต้อง "ปลดล็อก" ด้วยรหัสเปิดกล่องส่วนตัว (`request.session['box_unlocked_<id>']`) ห้ามแสดงเนื้อหาข้อความของกล่องที่ยังล็อกในหน้ารวม

## 6. รันและทดสอบในเครื่อง

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py test --parallel 1      # ล่าสุด: 319 tests OK
```
- `.claude/launch.json` มี `tspi-web` (Django :8010, ตั้ง `AI_SERVICE_URL=http://127.0.0.1:8090`) และ `tspi-ai` (FastAPI :8090) — ใช้ preview_start ไม่ใช้ bash รันเซิร์ฟเวอร์
- `.env` ในเครื่องมี `GEMINI_API_KEY` และ `INTERNAL_API_TOKEN` แล้ว (Gemini สรุปจริงทดสอบผ่าน ~5 วิ)
- ล็อกอินทดสอบโดยไม่ใช้รหัสผ่าน: สร้าง session ด้วย `SessionStore` ใน `manage.py shell` (user เช่น `nurse`, `d_test`) แล้วตั้งคุกกี้ `sessionid` ผ่าน JS บน `127.0.0.1:8010` (เปิดหน้า login ก่อนเพื่อล้างคุกกี้ HttpOnly เก่า) ใช้เสร็จลบ session ทิ้ง
- ข้อมูลทดสอบในฐานข้อมูลเครื่อง (ลบได้): คนไข้ `TEST-UI-001` (pk 3033) มีบันทึกตรวจ 2 รายการ, นัด 13 พ.ย. 10:30 และนัดวันนี้ 23:30, ข้อความทดสอบ `test_ui_msg_1` (บันทึกแล้ว) / `test_ui_msg_2` (ด่วน ค้างอยู่), LineUser `U_TEST_UI_001`
- migration `patients 0008` รันในเครื่องแล้ว ยังไม่ได้รันบน VPS

## 7. งานค้าง / ไอเดียถัดไป (13 พ.ย.)

ทำเสร็จแล้วจากรายการเดิม: commit + push ทั้งหมด, ฟิลด์ยาประจำตัว, ล้างข้อมูลปลอมในหน้าตั้งค่าแพทย์

**ผู้ใช้ต้องทำเอง**
1. deploy VPS (`./scripts/deploy.sh` รัน migration 0008, 0009) + ทดสอบบนมือถือจริงตาม checklist A8 ใน `docs/DEVELOPMENT_PLAN_2026-11.md`, ไมค์/กล้องในฟอร์มบันทึกการตรวจ, แท็บเล็ต
2. ตั้ง `GEMINI_API_KEY` และ `AI_PRICE_*` บน VPS ก่อนเปิดบอทให้คนไข้ทั่วไป
3. ส่งข้อมูลคลินิกจริง (เบอร์ เวลา ที่อยู่) — หน้าเว็บยังใช้ค่าชั่วคราว

**รอผู้ใช้ตัดสินใจ**
4. **"จุดถัดไป" หลังบันทึกเวชระเบียน** (เช่น จ่ายยา/ชำระเงิน) — ถามก่อนวางแผน
5. ถอดเสียงข้อความเสียงใน LINE (ส่งเสียงดิบให้ Gemini) ต้องให้คลินิกอนุมัติ — AI อีกตัวแก้ส่วนนี้ไปแล้ว ให้เช็กว่าตอนนี้เปิดอยู่หรือไม่

**ยังไม่ได้ทำ**
6. แจ้งคนไข้ทาง LINE ตอนสร้างนัด
7. หน้าที่ยังใช้ HTML เดิม (มีแค่ธีม): กล่องข้อความรวม LINE, ฟอร์มเพิ่ม/แก้ไขคนไข้, บันทึกเสียง Voice SOAP, หน้าในเมนู 39 แกน
8. portal คนไข้ (`patient_base.html`) ยังไม่ได้ทำ UI ใหม่ (ยกเว้นหน้าผู้ช่วย AI)
9. งาน VPS ที่เลื่อนไว้: backup, SMTP
10. เฟส B–D ในแผนพัฒนา

## 8. เอกสารอ้างอิงในโปรเจกต์

- `docs/DEVELOPMENT_PLAN_2026-11.md` — แผนเฟส A–D, การตัดสินใจเรื่อง LINE
- `docs/UI_REDESIGN_2026-11.md` — ค่าดีไซน์ที่แกะจาก Meditex / Medicare
- `docs/sumsum.md` — ภาพรวมสถาปัตยกรรมและงานที่ AI อีกตัวทำ (10–11 พ.ย.) เขียนโดย AI ตัวนั้น ยังไม่ได้ตรวจทุกข้ออ้าง
