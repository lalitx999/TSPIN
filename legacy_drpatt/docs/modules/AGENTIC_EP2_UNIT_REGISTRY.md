# Module: EP2 — Versioned unit registry

## สถานะ

เขียน registry lifecycle, evidence integration, GET canonical-state และ tests แล้ว
ยังไม่รัน tests/migrations/deploy และยังไม่ครบ EP2 (ontology/network/module/research/case
registry ยังไม่ย้ายมาใช้กลไกใหม่นี้)

## ทำอะไร

- Registry content immutable: version, concept-to-unit dictionary, hash และผู้สร้าง
- Lifecycle แยกเป็นประวัติ append-only: DRAFT → PROVISIONAL/APPROVED/RETIRED;
  PROVISIONAL → APPROVED/RETIRED; APPROVED → RETIRED; RETIRED ห้ามกลับมาใช้
- ผู้อนุมัติต้องมี permission และไม่ใช่ผู้สร้าง version เดียวกัน ต้องมีเหตุผลทุกครั้ง
- append_evidence/read_evidence_state เปลี่ยนจากรับ expected_units เป็น registry_id
  จึงไม่ให้ callers ส่ง dictionary เพื่ออ้างว่าหน่วยใดก็ถูกต้อง
- ฝัง registry ID/version/content hash ในหลักฐานและ canonical state hash
- Registry retirement กับ evidence write ใช้ row lock เดียวกันใน transaction
- Legacy evidence ที่ไม่มี registry และ version skew ถูก block ไม่ relabel โดยอัตโนมัติ
- GET `/api/patients/{id}/canonical-state/?registry_id={uuid}` ตรวจสิทธิ์ evidence view
  และ patient scope; 409 เมื่อ blocked, 404 เมื่อหา registry ไม่พบ, 400 เมื่อไม่ได้ระบุ version
- API แสดง VALIDATED_STRUCTURE เท่านั้น ไม่ใช่อนุมัติการรักษาหรือส่งรายงานผู้ป่วย

## ทำไมถึงทำแบบนี้ / ทางเลือก

ใช้ immutable release + lifecycle events เพื่อเก็บทั้งเนื้อหาและเหตุผลย้อนหลัง
อีกทางคือแก้ registry แถวเดิมง่ายกว่าแต่ทำให้หลักฐานเก่าตีความตามหน่วยใหม่โดยไม่รู้ตัว
ไม่ได้เปลี่ยนฐานข้อมูล production; migration เพิ่มตารางใหม่และ nullable FK เท่านั้น

## ไฟล์

- `models.py`: CanonicalUnitRegistry, UnitRegistryDecision และ evidence FK
- `migrations/0022_canonical_unit_registry.py`: schema เพิ่มเติม ไม่ backfill
- `unit_registry.py`: create/transition/approved lookup
- `evidence_service.py`: trusted registry lookup และ version binding
- `views.py`: read-only canonical-state action
- `tests_unit_registry.py`, `tests_evidence_service.py`: synthetic cases

## ทดสอบโดยผู้ใช้ใน environment พัฒนา

จาก backend:

```sh
python manage.py makemigrations --check --dry-run
python manage.py test patients.tests_canonical_state patients.tests_evidence_service patients.tests_unit_registry
```

คำสั่ง test ใช้ test database อย่าชี้ environment ไป production
ก่อนใช้งานจริงต้อง review migration 0021/0022 และรันโดยผู้ใช้เอง
ไม่มี seed approved registry หรือ grant permissions โดยอัตโนมัติ

## ข้อจำกัดสำคัญ

- ตอนนี้ผู้ป่วยที่มีหลักฐาน registry เวอร์ชันเก่าจะถูก block เมื่อใช้ version ใหม่
  ต้องสร้าง workflow revalidation/migration ที่อนุมัติและเก็บประวัติก่อนเปลี่ยนเวอร์ชัน
  ห้ามลบหลักฐานหรือแก้ FK เพื่อหลบ gate
- Retirement ไม่ลบ history; API canonical-evidence ยังอ่านประวัติได้ตามสิทธิ์เดิม
- Registry approval คือสิทธิ์กำกับข้อมูล ไม่ใช่ physician report approval/licence verification
- ORM append-only ไม่ป้องกัน privileged direct SQL; ต้องมี DB-level governance ภายหลัง
- ยังไม่มี write UI/API สำหรับ registry และ evidence; internal service เท่านั้น
- ยังไม่มี scoring/report invalidation integration, conversion rules หรือ concurrency test จริง
- ต้องขอแพทย์/ผู้กำกับข้อมูลอนุมัติ concept/unit mapping ก่อนสร้าง approved release จริง

## อ้างอิง

Agentic specification EP1/EP2, AT21 (version skew), AT23 (units) บางส่วนเท่านั้น
การเพิ่ม test ไม่ใช่หลักฐานว่าผ่าน acceptance
