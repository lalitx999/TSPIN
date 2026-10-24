# Module: EP3 — Persistent scoring snapshots and historical replay

## สถานะจริง

เพิ่ม ScoringRun, migration 0025, persistence ใน scoring service, historical replay,
patient-scoped history API และ tests แล้ว ยังไม่ได้รัน tests/migration/deploy
ยังไม่มี public execution API และยังไม่แทน legacy analysis/report engine

## ทำอะไร

- เก็บ manifest และผลลัพธ์ที่ใช้จริงในแต่ละ run พร้อม UUID, actor, เวลา และ integrity hash
- ผลลัพธ์มี rule content/hash/source references, registry/version, selected evidence IDs และ contributions
- คำนวณแล้วต้อง persist สำเร็จใน transaction จึงคืนผล ไม่มี fallback ข้าม audit write
- ถ้า preflight คืน BLOCKED เช่น stale hash เก็บเหตุผล/ค่าที่ร้องขอไว้ แต่ไม่รัน arithmetic
- History append-only ผ่าน model/queryset ปกติ ป้องกัน update/delete และใช้ FK PROTECT
- Replay ใช้ snapshot ของหลักฐานและสูตรเดิม ไม่ใช้ข้อมูลผู้ป่วย/สูตรปัจจุบัน
- อ่านประวัติได้แม้ registry ถูก retire แต่ response ระบุ historical_only และ clinical_use_authorized=false
- ตรวจทั้ง integrity hash, manifest hash และ deterministic result hash ก่อน replay

## API

GET `/api/patients/{patient_id}/scoring-runs/{run_uuid}/`

ต้องมี `patients.view_scoringrun` และผ่าน patient access ทั้ง view/service
คืน manifest/result ที่เก็บไว้ พร้อม replay MATCH/MISMATCH/NOT_EXECUTED/UNSUPPORTED_EXECUTOR_VERSION
ไม่เปลี่ยนสถานะอนุมัติและไม่อัปเดตข้อมูลผู้ป่วย
409 เมื่อ integrity/replay ผิด, 404 เมื่อไม่พบ run ในผู้ป่วยนั้น, 403 เมื่อ permission ไม่พอ

## ทำไมถึงทำแบบนี้ / ทางเลือก

แยก ScoringRun จาก AnalysisRecord เดิมเพื่อไม่ทำให้ arithmetic result ถูกตีความว่า
เป็น clinical report ที่ผ่าน safety/physician approval แล้ว อีกทางคือบันทึกลง
AnalysisRecord เดิมทันที แต่ต้องแก้ downstream gates ทั้งหมดพร้อมกัน จึงยังไม่ทำ

## โครงสร้างไฟล์

- models.py / migrations/0025_scoring_run.py: append-only run snapshots
- scoring_service.py: persist successful/not-assessed/arithmetic-blocked และ preflight-blocked outcomes
- scoring_history.py: integrity verification และ historical replay
- views.py: history/replay read endpoint
- tests_scoring_service.py: เพิ่ม persistence, correction, retirement, permission และ write-failure tests

## คำสั่งสำหรับผู้ใช้รันใน environment พัฒนา

จาก backend:

```sh
python manage.py makemigrations --check --dry-run
python manage.py test patients.tests_deterministic_scoring patients.tests_analysis_inputs patients.tests_scoring_service
```

Django test สร้าง test database; ไม่ใช้ production environment
ต้อง review migration 0025 ก่อนใช้งานจริง ยังไม่มีการ apply โดย agent

## จุดที่ต้องระวัง / งานถัดไป

- ยังไม่ได้รัน tests และ PostgreSQL concurrency tests
- permission denial, malformed requests และ exceptions ก่อน preflight สำเร็จยังไม่ได้เก็บใน ScoringRun
  ต้องใช้ security/request audit layer ใน EP9 ไม่กล่าวอ้างว่า log ทุกเหตุการณ์แล้ว
- Hash ตรวจ accidental tampering ไม่ใช่ digital signature; ผู้มีสิทธิ์ SQL แก้ทั้งข้อมูลและ hash ได้
- run UUID เป็น reference ใน scoring history ไม่ใช่ลายเซ็นอนุมัติจากแพทย์
- result_hash ไม่รวมเวลา/actor; integrity_hash รวม full result, actor และ run ID
- replay MATCH หมายถึงคำนวณซ้ำได้เหมือนเดิม ไม่รับรอง clinical validity หรือ consent
- ยังไม่ผูก PDF/release workflow; history เก่าต้องไม่ถูกนำส่งผู้ป่วยโดยข้าม current gates
- บันทึกซ้ำได้คนละ run ID แม้ inputs เหมือนกัน ยังไม่มี idempotency key contract
- การเก็บประวัติใช้ข้อมูลสุขภาพ ต้องกำหนด retention/encryption/backup/access policy ก่อน production
- executor เวอร์ชันใหม่ต้องคง replay implementation ของเวอร์ชันเก่า หรือคืน UNSUPPORTED ห้ามใช้สูตรใหม่แทนเงียบ ๆ

## อ้างอิง

ส่วนย่อย EP3/EP9, AT09 และ deterministic replay ของ AT20 ยังไม่ครบ clinical acceptance
