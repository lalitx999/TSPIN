# Module: EP4 — Safety completeness and SOC prerequisites

## สถานะจริง

เพิ่ม SAFETY registry contract, pure evaluator, backend preview/API, migration 0026
และชุดทดสอบแล้ว ยังไม่ได้รัน tests/migration/deploy และยังไม่ได้เชื่อมเป็น gate
บังคับของ scoring/report/release เดิม จึงยังไม่ครบ EP4 หรือ clinical acceptance

## ทำอะไร

- Approved policy ต้องครอบคลุม emergency, allergy, pregnancy, renal, hepatic,
  bleeding, interactions, critical_labs, referral และ consent
- Policy pin ontology/version/hash และระบุ concept, อายุข้อมูลที่ยอมรับ, N/A policy ชัดเจน
- ใช้ผลประเมินที่บันทึกโดยผู้ตรวจทางคลินิกและ verified ไม่แปลค่าผลแล็บเป็น CLEAR เอง
- รับสถานะ CLEAR/ALERT/EMERGENCY/NOT_APPLICABLE; missing/unverified/เก่า/อนาคต/กำกวมไม่ถือว่าประเมินครบ
- เลือก observation ล่าสุดตาม source timestamp ต่อ concept; ถ้าเวลาล่าสุดมีหลายค่าให้ incomplete
- สัญญาณ ALERT/EMERGENCY ใน observations ที่เลือกยังแสดงเพื่อให้ตรวจสอบ แม้ต้องทวน freshness/verification
- แยก coverage เป็นจำนวน domains ที่ประเมิน ไม่ใช่เปอร์เซ็นต์ความมั่นใจทางคลินิก
- SOC prerequisites ต้องมีหลักฐาน verified ตามรายการ/อายุที่ policy อนุมัติ ไม่เดาข้อบ่งชี้ขึ้นเอง
- Runtime interaction source ยังไม่ต่อ: service ส่ง UNAVAILABLE เสมอ จึงไม่มี all-clear
- แม้ pure test ให้ข้อมูลครบและ source available ก็ได้เพียง NO_RED_FLAG_IDENTIFIED_IN_AVAILABLE_DATA
  decision ยัง DEFER และ clinical_use_authorized=false เพื่อรอแพทย์

## API

POST `/api/patients/{id}/safety-preview/`

```json
{
  "unit_registry_id": "approved unit registry UUID",
  "selection": {"ONTOLOGY": "ontology UUID", "SAFETY": "safety registry UUID"},
  "policy_id": "approved policy entry ID"
}
```

เพิ่ม expected_manifest_hash จาก input preview ได้ เพื่อป้องกันข้อมูลค้าง
ต้องมี evidence/registry view permissions และ patient scope เช่นเดียวกับ input preview
ห้ามส่ง evidence หรือ interaction_source_status จาก client; schema ปฏิเสธ fields ส่วนเกิน
HTTP 200 หมายถึงอ่านผลประเมินสำเร็จ **ไม่ใช่ผ่านความปลอดภัย** ต้องอ่าน safety_state/decision
409 เมื่อ registry/contract ถูก block; read-only ไม่มีการอนุมัติหรือส่งข้อความออกนอกระบบ

## ทำไมถึงทำแบบนี้ / ทางเลือก

ใช้ structured clinician assessments เพื่อควบคุม completeness ก่อน โดยไม่ประดิษฐ์
clinical thresholds อีกทางคือให้ LLM ตัดสินจากข้อความ/ค่าผลแล็บ แต่ตรวจย้อนกลับยาก
และขัดกับ no verified source/no medical conclusion จึงไม่เลือกแนวทางนั้น

## ไฟล์

- safety_contracts.py: policy validation, freshness, recorded alerts และ SOC completeness
- safety_service.py: approved registry + canonical preflight + unavailable interaction source
- registry_governance.py / models.py: SAFETY kind และ ontology mapping validation
- migrations/0026_safety_registry.py: เพิ่ม registry choice ไม่ seed clinical policy
- views.py: patient-scoped safety-preview
- tests_safety_contracts.py / tests_safety_service.py: synthetic unit/integration tests

## ผู้ใช้รันทดสอบใน development/test environment

จาก backend:

```sh
python -m unittest patients.tests_safety_contracts -v
python manage.py makemigrations --check --dry-run
python manage.py test patients.tests_registry_governance patients.tests_safety_service
```

Django tests ใช้ test database ห้ามชี้ environment ไป production
review migration 0026 ก่อนใช้งานจริง; agent ไม่ได้รันทดสอบหรือ apply migration

## จุดที่ต้องระวัง / สิ่งที่ต้องขอจากแพทย์

- ต้องขอ approved safety concepts, applicability, freshness windows และ SOC prerequisite lists
  สำหรับแต่ละบริบทจริง ค่าใน tests เป็นข้อมูลสมมติ ไม่ใช่เกณฑ์รักษา
- ยังไม่มี drug-interaction connector และ no-interaction evidence จริง; ห้ามเปลี่ยนเป็น AVAILABLE ลอย ๆ
- Consent domain เป็นข้อมูลการประเมินเท่านั้น ยังไม่แทน legal consent/access/export authorization
- ไม่ใช่ระบบวินิจฉัย/คัดกรองอัตโนมัติ และยังไม่ได้ตรวจ medical licence ของผู้ประเมิน (EP7)
- เพิ่ม persistent safety snapshot/history/replay ภายหลังใน AGENTIC_EP4_SAFETY_HISTORY แล้ว
  แต่ยังไม่รันทดสอบและยังไม่มี output-release integration
- ถ้า registry ไม่พร้อม API จะ block; ไม่รับรองว่าตรวจพบ emergency ทุกกรณี
- รายการ SOC ว่างเป็นการประกาศขอบเขตของ policy ไม่ได้แปลว่าไม่ต้องประเมินมาตรฐานใดเลย
- Preflight blocked/stale จะไม่กลายเป็น clearance; alert ที่มีอยู่คงไว้เพื่อให้แพทย์ทบทวน
- ชุด safety ทั้งหมดเป็นเส้นทางใหม่ ระบบ legacy ยังไม่ถูกแทน ห้ามอ้างว่าปิดช่องทางเดิมแล้ว

## อ้างอิง

ส่วนย่อย AT12, AT28, AT29 ตาม Agentic specification ไม่ใช่ผล acceptance ที่รันผ่านแล้ว
