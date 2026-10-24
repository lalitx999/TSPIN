# Module: EP3 — Restricted deterministic scoring

## สถานะจริง

เขียน arithmetic executor, SCORING registry contract, authenticated backend service,
migration 0024 และชุดทดสอบแล้ว ยังไม่ได้รัน tests/migration และยังไม่เชื่อมระบบคำนวณเดิม
ไม่มี approved clinical formula จริง ไม่มีการสร้างคะแนนให้ผู้ป่วยจริงในรอบนี้

## ทำอะไร

- รองรับเฉพาะ WEIGHTED_SUM: offset + sum(value × weight)
- สูตรต้องระบุ inputs/units/weights/offset/range/bands และ missing_behavior=NOT_ASSESSED
- Decimal arithmetic ใช้ precision/range ที่กำหนด ไม่ใช้ eval หรือ LLM
- ตรวจ structural schema ก่อนอนุมัติทะเบียนและก่อนคำนวณ
- SCORING registry ใช้ immutable release/lifecycle เดิม และ pin ontology ID/hash
- service ต้องมี execute_governedscoring พร้อมสิทธิ์ evidence/registry/patient access
- บังคับ hash จาก preview; ตรวจ registry approval/retirement และ canonical evidence ใหม่ใน transaction
- ผู้เรียกต้องเลือก evidence IDs ที่ active และอยู่ในผู้ป่วยนั้นเองอย่างชัดเจน
- Missing/ambiguous/unverified/hypothesis/derived/wrong units ไม่ให้คะแนน
- ไม่ average หลาย observations และไม่ clamp คะแนนหลุดช่วงให้ดูเหมือนผ่าน
- ผลลัพธ์มีค่าที่ใช้ น้ำหนัก contribution source IDs rule/hash registry manifest hash และเวลา/ผู้รัน
- result_hash ไม่รวมเวลา/actor เพื่อเทียบ deterministic output; ไม่ใช่ลายเซ็นหรือ audit log
- clinical_use_authorized เป็น false เสมอ ต้องผ่าน safety/consent/physician approval อีก

## ทำไมถึงทำแบบนี้ / ทางเลือก

เลือกตัวแปลสูตรแบบจำกัด operation เพื่อให้ตรวจและทดสอบได้
อีกทางคือรับ Python expression หรือสูตรข้อความอิสระ จะรองรับสูตรมากกว่าแต่เสี่ยง
code execution และความคลุมเครือ จึงไม่เปิดช่องนั้น

## โครงสร้างไฟล์

- deterministic_scoring.py: pure validator/interpreter ไม่ตรวจ permission ด้วยตัวเอง
- scoring_service.py: entry point ที่ตรวจ approved DB state/permissions/manifest ก่อนคำนวณ
- registry_governance.py: เพิ่มชนิด SCORING และตรวจ ontology input mapping
- models.py, migrations/0024_governed_scoring.py: registry kind + execute permission
- tests_deterministic_scoring.py: synthetic arithmetic/unit tests
- tests_scoring_service.py: synthetic backend integration tests

## ผู้ใช้รันทดสอบเอง

จาก backend ใน environment พัฒนา/ทดสอบ ไม่ใช่ production:

```sh
python -m unittest patients.tests_deterministic_scoring -v
python manage.py makemigrations --check --dry-run
python manage.py test patients.tests_registry_governance patients.tests_analysis_inputs patients.tests_scoring_service
```

คำสั่ง Django test ใช้ test database ต้อง review migration 0024 ก่อนใช้งานจริง
ไม่มี auto-grant execute permission และไม่มี approved seed

## จุดที่ต้องระวัง / งานถัดไป

- ยังไม่มี public execution API/UI เพื่อไม่ให้คะแนนออกไปก่อน persistent audit/safety gates พร้อม
- เพิ่ม ScoringRun persistence/replay แล้วในโมดูล AGENTIC_EP3_SCORING_HISTORY แต่ยังไม่ทดสอบ
  และยังไม่ผูก AnalysisRecord เดิม จึงยังไม่ครบ AT09/AT20
- ยังไม่รองรับ non-linear formulas, transforms, unit conversion, models หรือ score aggregation
- สูตรจริง/thresholds/weights/bands/source policy/time windows ต้องให้แพทย์อนุมัติ ไม่ใช้สูตรทดสอบ
- ข้อมูลที่เลือกอาจเป็นคนละวัน; ยังต้องเพิ่ม clinical time-window rule ก่อนใช้งานทางคลินิก
- ค่า score เป็น decimal string เพื่อไม่เสีย precision; frontend เดิมยังไม่ใช้ contract นี้
- ไม่ใช้ heuristic axis scores เดิมเป็น input และยังไม่ได้ปิด legacy scoring path
- ตัว pure interpreter ไม่ใช่ security boundary: production callers ต้องผ่าน scoring_service เท่านั้น
- มี tests แต่ยังไม่รัน จึงยังไม่อ้างผลผ่านหรือ production readiness

## อ้างอิง

ส่วนย่อย EP3 / AT03, AT04, AT09, AT21 เท่านั้น ยังไม่ครบ end-to-end acceptance
