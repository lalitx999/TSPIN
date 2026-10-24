# Module: EP4 — Persistent safety assessment and historical replay

## สถานะจริง

เพิ่ม model, migration 0027, snapshot service, record/history API และ tests แล้ว
ยังไม่ได้รัน tests/migration/deploy ยังไม่เชื่อม safety snapshot เป็น release gate ของรายงานเดิม

## ทำอะไร

- บันทึก manifest, policy content, registry references, result, preflight status และ expected hash
- เก็บ UUID, ผู้บันทึก, created_at และ integrity hash; บันทึกใหม่แทนแก้ทับ
- เก็บผล incomplete/stale/alert ด้วย เพื่อให้เห็นเหตุผลที่ไม่พร้อม ไม่ถือเป็นการอนุมัติ
- หากบันทึกไม่ได้ให้ transaction ล้มเหลว ไม่ตอบว่าเก็บสำเร็จ
- Replay ใช้ evidence, policy, interaction source status และ assessed_at เดิม
- Retirement ของ policy ไม่ลบประวัติ แต่การประเมินใหม่ต้องผ่าน registry ปัจจุบัน
- Preview เดิมยัง read-only ไม่มีการบันทึกโดยอัตโนมัติ

## API

POST `/api/patients/{patient_id}/safety-assessments/`

ต้องมี add_safetyassessment พร้อม view permissions ของ evidence/registry และ patient scope
body ต้องมี unit_registry_id, selection, policy_id, expected_manifest_hash เท่านั้น
คืน 201 เมื่อสร้าง snapshot สำเร็จ แม้ safety_state เป็น PARTIAL/INCOMPLETE/ALERT
**201 ไม่ใช่ safety pass**; clinical_use_authorized=false เสมอ

GET `/api/patients/{patient_id}/safety-assessments/{uuid}/`

ต้องมี view_safetyassessment และผ่าน patient scope คืน historical snapshot และ replay result
historical_only=true และ clinical_use_authorized=false
404 เมื่อไม่มี record ในผู้ป่วยนั้น, 403 เมื่อสิทธิ์ไม่พอ, 409 เมื่อ integrity/replay ไม่ตรง

## ทำไมถึงทำแบบนี้ / ทางเลือก

แยก historical assessment จาก clinical approval เพราะข้อมูลครบในอดีตไม่ได้แปลว่า
ยังใช้อนุมัติวันนี้ได้ อีกทางคืออ่านข้อมูลล่าสุดมาสร้างประวัติทุกครั้ง แต่ทำให้การตรวจ
ย้อนหลังเปลี่ยนไปตามข้อมูลใหม่ จึงเก็บ snapshot พร้อมเวลาและ policy เดิม

## ไฟล์

- models.py / migrations/0027_safety_assessment.py: append-only safety snapshots
- safety_service.py: แยก snapshot builder, read-only preview และ explicit record service
- safety_history.py: integrity verification และ replay ที่เวลาเดิม
- views.py: record/history endpoints
- tests_safety_history.py: permission, persistence, stale inputs, aging, retirement และ write-failure tests

## คำสั่งทดสอบสำหรับผู้ใช้

จาก backend ใน development/test environment ที่ไม่ชี้ production:

```sh
python manage.py makemigrations --check --dry-run
python manage.py test patients.tests_safety_contracts patients.tests_safety_service patients.tests_safety_history
```

Django tests ใช้ test database; review migration 0027 ก่อนใช้งานจริง
agent ไม่ได้รันทดสอบหรือ apply migration ตามกฎโปรเจกต์

## ข้อจำกัด / งานต่อ

- ยังไม่มี release gate บังคับทั้งระบบ, physician signature หรือ licence verification
- Interaction source ยัง UNAVAILABLE ไม่มีการเชื่อมระบบตรวจยาจริง
- Integrity hash ไม่ใช่ digital signature และไม่ป้องกัน privileged SQL ที่แก้ทั้ง payload/hash
- Permission-denied/malformed requests ก่อน snapshot ไม่เก็บในตารางนี้ ต้องเชื่อม request/security audit EP9
- Replay MATCH ยืนยัน reproducibility เท่านั้น ไม่ยืนยันความถูกต้องทางคลินิกหรือความพร้อมปัจจุบัน
- ข้อมูลสุขภาพใน snapshots ต้องมี retention/encryption/backup policy ก่อน production
- การ POST ซ้ำสร้างคนละ assessment ID; idempotency contract ยังไม่เพิ่ม
- ต้องตรวจใหม่ตอน release เสมอ ห้ามใช้ UUID/hash ของ history เป็น approval token
- Tests เขียนแล้วแต่ยังไม่รัน จึงยังไม่ถือว่าผ่าน AT12/AT20/AT28/AT29
