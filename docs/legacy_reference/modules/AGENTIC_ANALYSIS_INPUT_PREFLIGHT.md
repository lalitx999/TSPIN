# Module: EP1/EP2 integration — Analysis input preflight

## สถานะจริง

เชื่อม canonical evidence กับ unit registry และ governed registry bundle ใน transaction
เดียว พร้อม API และชุดทดสอบแล้ว ยังไม่รัน tests และยังไม่แทน legacy calculation path
ไม่มี migration ใหม่ในรอบนี้ แต่ต้องมี schema 0021–0023 ก่อนใช้บริการใหม่

## ทำอะไร

- โหลด identity และหลักฐานจาก backend ไม่รับ client evidence/verification claims
- ตรวจ view permissions ทั้ง evidence และ registry รวมถึง patient scope ใน service/API
- บังคับเลือก ontology; ตรวจ concept ของ active evidence กับ ontology ที่อนุมัติจริง
- หลักฐานไม่ครบ/ขัดแย้ง/ยังไม่ verified หรือ identity ขาด HN/DOB/gender ให้ BLOCKED
- ผูก identity + canonical state + registry bundle + unit approval decision เป็น manifest hash
- ส่ง expected_manifest_hash เพื่อเทียบกับข้อมูลปัจจุบัน ถ้าเปลี่ยนคืน STALE_ANALYSIS_INPUT
- ไม่สร้าง AnalysisRecord, biological scores หรือรายงาน และไม่เขียนข้อมูลผู้ป่วย
- ไม่มีการอนุมัติ clinical use จาก preview; ยังมี scoring/safety/consent/physician gates แยก

## API

`POST /api/patients/{id}/analysis-input-preview/`

```json
{
  "unit_registry_id": "UUID ของ approved unit registry",
  "selection": {"ONTOLOGY": "UUID ของ approved ontology"},
  "expected_manifest_hash": "hash จาก preview ก่อนหน้า (ละได้ในการเปิดครั้งแรก)"
}
```

ตัวอย่างค่า UUID/hash ข้างบนเป็นคำอธิบาย ไม่ใช่ค่าที่ใช้ส่งจริง
200 = INPUT_PREVIEW_VALIDATED เท่านั้น, 409 = blocked/stale, 403 = permission ไม่พอ
body ที่มี fields นอก contract คืน 400; client ไม่สามารถส่ง expected_units/evidence มาแทน DB

## ทำไมถึงทำแบบนี้ / ทางเลือก

เพิ่ม preflight คู่ขนานก่อนเปลี่ยน engine เดิม เพื่อให้ทดสอบ integration ของฐานข้อมูลกลาง
อีกทางคือสลับ calculation endpoint เดิมทันที แต่ข้อมูลเก่ายังไม่มี canonical provenance
และ formula registry ที่พร้อมใช้งาน จึงเสี่ยงหยุดระบบเดิมทั้งหมด

## ไฟล์

- `analysis_inputs.py`: manifest builder และ freshness check
- `views.py`: patient-scoped preview action
- `tests_analysis_inputs.py`: synthetic integration tests

## ให้ผู้ใช้รันใน development/test environment

จาก backend:

```sh
python manage.py test patients.tests_canonical_state patients.tests_evidence_service patients.tests_unit_registry patients.tests_registry_governance patients.tests_analysis_inputs
```

คำสั่งนี้สร้าง test database ห้ามใช้ environment ที่ชี้ production
agent ยังไม่รัน tests ตามกฎโปรเจกต์ จึงยังไม่มีผลผ่าน/ไม่ผ่าน

## ข้อจำกัด / งานถัดไป

- Preview ไม่ใช่การ invalidate รายงานเก่าที่ persist แล้ว; ยังต้องต่อ execution/release gate
- expected hash ไม่ใช่ security token และไม่แทนการตรวจ permission/consent/registry retirement
- ต้องเรียกตรวจใหม่ใน transaction ตอน execute/approve/release ไม่ reuse preview หลังคืน response
- เลือก registries เพิ่มได้ แต่ required kinds ของ clinical operation ต้องกำหนดใน executor ภายหลัง
- Lock order: unit registry → patient → governed registries ตาม UUID เพื่อสอดคล้องกับ evidence writes
  ยังไม่รันทดสอบ concurrent PostgreSQL transactions
- ไม่มีการ infer ว่า VERIFIED source คือผลแล็บที่ใช้คิดคะแนนได้ ต้องตรวจ source type/unit/rule ใน EP3
- consent_scope ของหลักฐานยังไม่ใช่หลักฐาน consent จริง; consent gate ยังไม่เชื่อม
- Manifest ยังไม่ persist เป็น immutable analysis run; งานนี้เป็น read-only integration ก่อน
- ยังไม่ตรวจ live CASE connectivity หรือ clinical validity ของ registry mappings
- ระบบ legacy ยังไม่ใช้ gate ใหม่นี้ ห้ามอ้างว่ากัน stale analysis ได้ครบทั้งระบบแล้ว

## อ้างอิง

ส่วนย่อย AT01, AT02, AT21, AT22, AT25 ตาม Agentic specification ไม่ใช่ผล end-to-end acceptance
