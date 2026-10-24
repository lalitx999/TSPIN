# Module: EP5 — Bounded 18-role workflow controller

## สถานะจริง

เขียนตัวควบคุมลำดับงานและ synthetic tests แล้ว ยังไม่ได้รัน tests
ยังไม่เชื่อม handlers จริง, LLM providers, queue, persistent trace หรือ production endpoints
ไม่มี migration/deploy ใหม่ในรอบนี้ และไม่ได้ถือว่าครบ EP5 แล้ว

## ทำอะไร

| Role | หน้าที่ตาม contract |
|---|---|
| A01–A04 | Identity/source, completeness, provenance, registry |
| A05–A08 | Scoring, contradiction, clinical logic, safety |
| A09–A12 | Standard of care, research, cases, module matching |
| A13 | Compose structured draft |
| A14–A16 | Independent audit, red team, cross-report consistency |
| A17–A18 | Patient communication validation, physician approval adapter |

- แต่ละ handler ต้องมี version และคืน role/input_hash/decision/payload/issues ตาม schema
- Decisions รับเฉพาะ PASS/FAIL/DEFER/ESCALATE/STOP; PASS ที่ยังมี issues ถูกปฏิเสธ
- Missing handler คืน HUMAN_REVIEW_REQUIRED ไม่ใส่ PASS แทน
- Handler error/invalid output หยุด BLOCKED โดยไม่คัดลอก exception text ที่อาจมี PHI/token
- Retry เฉพาะ FAIL ของ A14–A16; safety escalation/identity failure ไม่ retry เพื่อให้ผ่านเอง
- Draft ใหม่จะเริ่มรอบใหม่และรันทุก role ใหม่ จึงไม่ reuse audit ของ draft เก่า
- จำกัด 1–3 รอบ รวมมากสุด 54 role invocations ไม่มี while-loop ไม่จำกัด
- A14–A18 ต้องระบุ reviewed_draft_hash ให้ตรงร่างปัจจุบัน
- A17/A18 ห้ามส่ง draft ใหม่มาทับร่างที่ตรวจแล้ว
- Input/output แยกสำเนา; handler แก้ input ของตัวเองไม่ได้เปลี่ยน canonical manifest
- Trace เก็บ role/version/round/decision/input-output hashes/draft hash/timestamps และ structured output
- แม้ workflow checks ผ่าน ก็ยัง clinical_use_authorized=false ไม่ออก approval token

## ทำไมถึงทำแบบนี้ / ทางเลือก

ใช้ controller ที่ไม่เรียก tools/network เอง แล้วให้ trusted backend adapters ทำแต่ละหน้าที่
อีกทางคือให้ model วางลำดับเรียก agents/tools เอง แต่ควบคุม retries, missing gates และ
ขอบเขต authority ยากกว่า จึงใช้ fixed workflow ก่อน

## โครงสร้างไฟล์

- agentic_orchestrator.py: fixed role order, envelope validation, draft binding, bounded retries
- tests_agentic_orchestrator.py: synthetic handlers สำหรับทดสอบ control flow เท่านั้น

## วิธีทดสอบโดยผู้ใช้

จาก backend:

```sh
python -m unittest patients.tests_agentic_orchestrator -v
```

ไม่ใช้ Django test DB ไม่มี network/LLM calls ในชุดนี้
agent ยังไม่ได้รันตามกฎโปรเจกต์ จึงยังไม่มีผลผ่าน/ไม่ผ่าน

## Trust boundary และข้อจำกัด

- ห้ามรับ handlers/callables จาก HTTP payload หรือผู้ป่วย ต้อง register ผ่าน backend code เท่านั้น
- Handler input_hash ป้องกันผลค้าง/สลับบทบาท ไม่ได้พิสูจน์ว่าผล reasoning ถูกต้อง
- ยังไม่มี claim validator: tests ที่จำลอง red-team FAIL พิสูจน์ control flow ไม่ใช่ hallucination detection
- ชื่อ independent auditor ยังไม่พิสูจน์ความเป็นอิสระของ model/credentials; ต้องกำหนด adapters ภายหลัง
- ทุก handler ต้องมี timeout และ side-effect policy ของตัวเอง controller แบบ synchronous ไม่สามารถ
  ตัด handler ที่ค้างได้เอง รอบที่จำกัดไม่เท่ากับ wall-clock timeout
- ทุก role อาจถูกรันใหม่เมื่อ retry; adapters ต้องเป็น read-only/idempotent ห้ามส่ง LINE/อีเมล/สั่งรักษา
- A17 เป็นการตรวจ communication draft ไม่ใช่ send; A18 ต้องตรวจ physician auth/licence/signed version จริง
- การหยุดก่อนถึง A08 หมายถึงยังไม่ได้ตรวจ safety; workflow นี้ไม่ใช่ emergency screening service
- Trace ตอนนี้อยู่ใน return value ยังไม่ persist ต้องเพิ่ม durable audit และ retention/access control
- Return draft เป็น debugging artifact แม้สถานะ BLOCKED ห้ามส่งผู้ป่วยหรือ render เป็น approved report
- ผล PASS จาก test handlers ทั้ง 18 ไม่ใช่ acceptance ของระบบคลินิกหรือการปล่อยใช้งาน

## งานถัดไป

เชื่อม trusted input/scoring/safety adapters, durable workflow run/trace, queue deadlines,
report claim validators, physician approval gate และทดสอบ integration ก่อนเปิด endpoint จริง

## อ้างอิง

ส่วน control flow ของ AT18/AT19; ยังไม่ครบ model red-team หรือ clinical acceptance
