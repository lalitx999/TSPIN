# Module: Agentic EP1 — Canonical evidence snapshot

## สถานะจริง

เขียนตัวตรวจโครงสร้าง, model เก็บหลักฐาน, migration 0021, transactional service,
API อ่านประวัติ และชุดทดสอบแล้ว ยังไม่ได้รันทดสอบหรือ migration จริง
ยังไม่ได้เชื่อม source import, scoring engine หรือ report release เดิม จึงยังไม่ถือว่า
EP1 เสร็จหรือผ่าน AT แบบ end-to-end และไม่มีการ deploy/migrate ในรอบนี้

## ทำอะไร

- ผูกทุกหลักฐานกับ patient ID และ HN; ไม่ใช้ข้อมูลข้ามผู้ป่วย
- บังคับ provenance, timezone, version, source classification และ verifier
- หน่วยไม่ตรงหรือ concept ไม่รู้จักให้ BLOCKED ไม่เดาหรือแปลงเอง
- ตัดหลักฐานนำเข้าซ้ำจาก active set แต่คง history
- ตรวจความขัดแย้งของข้อมูล verified ใน concept และเวลาเดียวกัน
- ข้อมูลต่างวันเป็น longitudinal observations ไม่ใช่ conflict อัตโนมัติ
- correction ต้องมี parent, version ต่อเนื่อง, เหตุผล, เวลาใหม่ และ verification
- hash เปลี่ยนตามหลักฐาน/ประวัติ/หน่วย; ไม่แก้ input ของ caller
- VALIDATED_STRUCTURE ไม่ใช่การรับรองทางการแพทย์หรืออนุมัติส่งผู้ป่วย

## ทำไมถึงทำแบบนี้

แยกฟังก์ชันตรวจข้อมูลที่ไม่อ่านหรือเขียน DB เพื่อทดสอบก่อนเชื่อมระบบจริง และไม่ชนกับ
งานเดิมที่ยังไม่ได้ commit อีกทางคือแทน JSON เดิมด้วย schema ใหม่ทันที แต่เสี่ยงกับ
ข้อมูลเก่าและต้องมีแผน migration ก่อน จึงยังไม่ทำการย้ายข้อมูล

## โครงสร้างไฟล์

- `backend/patients/canonical_state.py`: snapshot builder และ deterministic hash
- `backend/patients/tests_canonical_state.py`: synthetic unit tests
- `backend/patients/models.py`: ClinicalEvidenceRevision และ append-only queryset
- `backend/patients/migrations/0021_clinical_evidence_revision.py`: ตารางใหม่ ไม่ย้าย/ลบ JSON เดิม
- `backend/patients/evidence_service.py`: บันทึกหลักฐานและ correction ภายใน transaction
- `backend/patients/tests_evidence_service.py`: persistence, permission และ API tests
- `backend/patients/views.py`: GET `/api/patients/{id}/canonical-evidence/`

## สิทธิ์และขอบเขตการเชื่อถือ

- เพิ่มหลักฐานต้องมี `patients.add_clinicalevidencerevision`
- ยืนยัน/แก้ไขหลักฐานต้องมี `patients.verify_clinicalevidence` เพิ่มเติม
- อ่านผ่าน API ต้องมี `patients.view_clinicalevidencerevision` และผ่าน patient scope เดิม
- `is_staff` อย่างเดียวไม่ให้สิทธิ์เหล่านี้; superuser ยังเป็น trusted administrator ของ Django
- Backend สร้าง evidence ID, actor ID, เวลา, version และ verification เอง ไม่รับจาก source
- การยืนยันนี้คือ source verification เท่านั้น ไม่ใช่การอนุมัติรายงานหรือตรวจใบประกอบวิชาชีพ
- Source ต้องระบุ patient_id เป็น string และ HN ตรงกับผู้ป่วย ไม่แก้ป้ายเจ้าของให้เอง
- ยังไม่มี write API/UI; service เป็นช่องทางภายในสำหรับ source adapter ที่จะต่อในขั้นถัดไป
- ไม่มีการให้ permission อัตโนมัติแก่กลุ่ม doctor/nurse/admin เดิม
- ป้องกัน overwrite/delete ผ่าน model/queryset ปกติ แต่ไม่ใช่ DB-level tamper-proof storage
  SQL โดยตรงหรือ privileged DB admin ยังแก้ข้อมูลได้ ต้องพัฒนา DB retention/audit policy แยก
- Lock patient row ก่อนตรวจ correction และใช้ unique parent ป้องกัน revision แตกแขนง
  ต้องทดสอบ concurrent transactions บน PostgreSQL เพิ่ม; SQLite ไม่พิสูจน์ row locking
- ข้อมูล verified ที่ขัดแย้งกันคงเก็บไว้พร้อม BLOCKED ไม่ทิ้งหลักฐานที่จำเป็นต่อการตรวจสอบ

## คำสั่งให้ผู้ใช้รันเอง

จากโฟลเดอร์ backend ภายใต้ Python environment ของโปรเจกต์:

```sh
python -m unittest patients.tests_canonical_state -v
```

ไม่ต้องใช้ Django test DB และไม่ทำ migration

สำหรับ persistence/API tests ด้านล่าง Django จะสร้าง **test database**; ต้องใช้
environment พัฒนา/ทดสอบที่แยกจาก production และให้ผู้ใช้เป็นผู้รัน:

```sh
python manage.py makemigrations --check --dry-run
python manage.py test patients.tests_canonical_state patients.tests_evidence_service
```

ห้ามสรุปว่าผ่านจากการมีไฟล์ทดสอบ ต้องตรวจผลจริง หาก migration check พบความต่าง
ให้ตรวจ diff ก่อน ไม่สร้าง migration ซ้ำทับงานเก่าโดยอัตโนมัติ
0021 ต้อง review และทดสอบก่อนนำไป migrate production; ตารางเดิมไม่ถูก backfill
endpoint ใหม่จะใช้ไม่ได้จนกว่าจะ apply migration นี้

## จุดที่ต้องระวัง / งานถัดไป

1. Backend adapter ต้องดึง identity, verification และ permission จากข้อมูลที่เชื่อถือได้
   ไม่ให้ request body อ้างเองว่า VERIFIED หรือ verified_by เป็นแพทย์
2. เพิ่ม persistence/lock/authorization แล้ว แต่ยังรอผลทดสอบจริงและ concurrent PostgreSQL tests
3. ต้องเชื่อม source import, analysis hash, invalidation และทุก report composer
4. EP2 เปลี่ยน public evidence service ให้รับ registry_id แทน expected_units แล้ว
   โหลดหน่วยจาก approved registry ฝั่ง backend; pure validator ยังรับ mapping สำหรับ unit tests
5. ยังไม่รองรับการแปลงหน่วย; block ปลอดภัยไว้ก่อนรอ approved conversion rules
6. ตรรกะเวลาเดียวกันต้องต่อยอดเป็น specimen/observation identity ตาม source adapter
7. ไม่ใช้ state_hash เป็นลายเซ็นแพทย์; hash ที่ client ส่งมายังไม่ใช่ trusted state
8. ต้องทดสอบ integration และ concurrency ก่อนเปลี่ยน production path

## อ้างอิง

แผน Agentic EP0–EP10 ตาม specification ที่ผู้ใช้ส่งมา:
ครอบคลุมส่วนย่อยของ AT01, AT02, AT22–AT25 เท่านั้น ไม่ใช่หลักฐานผ่าน acceptance
