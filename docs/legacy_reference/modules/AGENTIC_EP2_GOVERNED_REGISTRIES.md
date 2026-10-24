# Module: EP2 — Governed registry metadata and bundle validation

## สถานะจริง

เขียน model, migration 0023, lifecycle service, bundle resolver, read-only validation API
และชุดทดสอบแล้ว ยังไม่ได้รัน tests/migration/deploy ยังไม่ได้แทน legacy module registry,
เชื่อม scoring/report engine หรือสร้าง write UI จึงยังไม่ถือว่า EP2 ผ่าน acceptance

## ทำอะไร

- ทะเบียน ONTOLOGY/NETWORK/MODULE ใช้ DRAFT/PROVISIONAL/APPROVED/RETIRED
- RESEARCH ใช้ UNVERIFIED → VERIFIED → APPROVED หรือ RETIRED
- CASE ใช้ UNAVAILABLE → CONNECTED → VALIDATED และกลับ UNAVAILABLE ได้
- ทุก version เป็น immutable content พร้อม hash; decisions เก็บ actor/time/reason แยก
- การอนุมัติขั้นสุดท้ายต้องเป็นคนละบัญชีกับผู้สร้างและมี permission ชัดเจน
- NETWORK ผูก ontology ID/hash; MODULE ผูกทั้ง ontology และ network ID/hash
- Bundle resolver ตรวจชื่อชนิด registry, lifecycle, hash, dependency และ mapping IDs
- ไม่เลือก latest อัตโนมัติและไม่ยอมจับ registry คนละเวอร์ชันเข้าด้วยกัน
- Research entries บังคับ Study ID; ทุก entry ต้องมี source references
- CASE เก็บ connector/dataset metadata เท่านั้น ไม่ใช่ทะเบียนประวัติผู้ป่วย
- Metadata schema ไม่รับคะแนน/ranking/synergy หรือผลลัพธ์การรักษา

## API

`POST /api/registries/validate-bundle/` ใช้ POST เพื่อรับ JSON selection แต่ไม่เขียนข้อมูล
ต้อง login และมี `patients.view_governedregistry`

```json
{
  "selection": {
    "ONTOLOGY": "UUID ของ ontology release",
    "NETWORK": "UUID ของ network release",
    "MODULE": "UUID ของ module release"
  }
}
```

200 หมายถึง **REGISTRY_METADATA_VALIDATED** และ `clinical_use_authorized: false`
เสมอ ไม่ใช่อนุมัติการรักษา; 409 เมื่อ gate ไม่ผ่าน, 403 เมื่อไม่มี permission
API นี้ตรวจ subset ที่ผู้เรียกเลือก ไม่ยืนยันว่าครบ registries สำหรับ clinical operation
ทุก downstream operation ต้องบังคับ required kinds ของตัวเองและตรวจใหม่ก่อนใช้งาน

## ทำไมถึงทำแบบนี้ / ทางเลือก

เพิ่ม immutable releases คู่ขนานกับ legacy models เพื่อไม่แปลงข้อมูลที่มีอยู่ให้ approved เอง
อีกทางคือแทน ModuleRegistryEntry เดิมทันที แต่เสี่ยงเปลี่ยนผลระบบเก่าและเสียประวัติ
ต้องมี reviewed import/migration adapter และ regression tests ก่อนสลับ engine

## ไฟล์

- `models.py`: GovernedRegistry และ GovernedRegistryDecision
- `migrations/0023_governed_registry.py`: สองตารางใหม่ ไม่มี backfill/grant permission
- `registry_governance.py`: schema validation, lifecycle, locked bundle resolution
- `views_registry.py`, `urls.py`: authenticated read-only validation endpoint
- `tests_registry_governance.py`: synthetic cases สำหรับ readiness, skew, permissions และ references

## การตรวจสอบโดยผู้ใช้

จาก backend ใน environment พัฒนา/ทดสอบที่ไม่ชี้ production:

```sh
python manage.py makemigrations --check --dry-run
python manage.py test patients.tests_canonical_state patients.tests_evidence_service patients.tests_unit_registry patients.tests_registry_governance
```

Django tests สร้าง test database; agent ไม่ได้รันคำสั่งเหล่านี้
review migration 0021–0023 ก่อนใช้งานจริง ไม่ต้องลบข้อมูลเดิม

## ข้อจำกัดและงานถัดไป

- Source IDs เป็น reference strings ไม่ได้ตรวจเนื้อหาเอกสารจริง/คุณภาพงานวิจัยโดยอัตโนมัติ
- CASE VALIDATED คือ metadata review ไม่ใช่หลักฐานว่า connector online ณ ขณะใช้งาน
  ต้องมี runtime connectivity/consent/data access checks ก่อน case matching และห้ามอ้าง match % จาก metadata
- ไม่มีค่าทางคลินิกจริงหรือ approved seed; ต้องขอ approved definitions/mappings จากแพทย์
- Bundle hash ไม่ใช่ token อนุมัติที่ใช้ได้ตลอด; retirement ภายหลังต้องตรวจใหม่ทุกครั้ง
- Transaction locks ให้ coherent registry read; ยังไม่พิสูจน์ concurrency บน PostgreSQL
- ORM guards ไม่ใช่ DB immutable security boundary; privileged SQL ยังเป็นข้อจำกัด
- กรณีไม่มี entry ไม่ได้แปลว่ามี candidate ใช้ได้; resolver ส่ง entry_count ให้ downstream
- Mapping compatibility ตรวจตอน resolve ไม่ใช่การรับรองว่าการเชื่อมโยงนั้นถูกต้องทางคลินิก
- Registry schema ตอนนี้เก็บ metadata เฉพาะที่กำหนด ยังไม่ครอบคลุม protocol/thresholds/contraindications
- Unit registry ของ EP2 ก่อนหน้ายังเป็นคนละชุดกับ bundle นี้ ต้องผูกทั้งสองใน analysis manifest ต่อไป

## อ้างอิง

ส่วนย่อยของ AT05–08 และ AT21 ตาม Agentic specification เท่านั้น
ยังไม่ใช่ผล clinical end-to-end acceptance
