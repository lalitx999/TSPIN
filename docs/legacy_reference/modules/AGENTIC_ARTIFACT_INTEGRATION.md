# Module: Unreleased agentic artifacts — backend integration

## ทำอะไร

บันทึกร่าง evidence-only สามฉบับและ workflow review เป็น AgenticArtifact
ใช้ manifest ของข้อมูลและ registry รุ่นที่ตรวจแล้ว พร้อม hash และสิทธิ์ผู้ใช้งาน
ไม่มีการเผยแพร่ผู้ป่วยหรืออนุมัติทางคลินิกจาก endpoint นี้

## ทำไมถึงทำแบบนี้

ทางเลือกสร้างรายงานทันทีจากผล scoring ทำให้ข้าม clinical review ได้
จึงเลือกเก็บเป็นร่างและ trace แยก: ตรวจสอบย้อนหลังได้ แต่ยังต้องพัฒนา workflow ที่เหลือ
เมื่อยังไม่มี adapter ของ clinical logic จะหยุด A07 ไม่สร้าง PASS จำลอง

## โครงสร้างไฟล์

- backend/patients/agentic_service.py: เชื่อม preflight/scoring/safety กับการสร้าง artifact
- backend/patients/evidence_reports.py: คัดหลักฐานชุดเดียวกันเป็นสามฉบับ ไม่เติมคำแนะนำ
- backend/patients/models.py: AgenticArtifact แบบ append-only ผ่าน ORM
- backend/patients/migrations/0028_agentic_artifact.py: schema สำหรับ artifact
- backend/patients/views.py: POST agentic-artifacts และ GET ประวัติภายใต้ patient
- backend/patients/tests_agentic_service.py: 11 service/API integration tests

## ผลทดสอบ 18 October 2026

ใช้ backend/.venv/bin/python และ Django test runner บน SQLite :memory:
runner สร้าง schema เฉพาะฐานข้อมูลทดสอบและทำลายหลังจบ ไม่ migrate ฐานข้อมูลใช้งานจริง

- ชุดรวมก่อนเพิ่ม workflow cases: 152 tests ผ่าน
- ชุด artifact หลังเพิ่ม workflow cases: 11 tests ผ่าน
- รันชุดรวมซ้ำหลังเพิ่ม workflow cases: 155 tests ผ่าน (exit 0)
- รอบถัดมาเพิ่ม cross-patient lookup/API, payload integrity และ emergency precheck:
  รวม 158 tests ผ่าน (exit 0), artifact suite มี 14 ข้อ
- ไม่มี system check issues ในการรันทั้งสองชุด

ตรวจการบันทึกสามฉบับ, ข้อมูลเก่าหลัง correction, explicit permissions,
ป้องกัน nonclinical access แม้มี model permission, write failure,
append-only, API ปฏิเสธ packet จาก client, history retrieval,
workflow หยุด A07, scoring run เก่าถูกปฏิเสธ และ stale hash หยุด A01
รวมถึง artifact ของผู้ป่วยอื่นต้องได้ 404 โดยไม่คืน payload,
snapshot ที่แก้ข้อมูลแล้ว hash ไม่ตรงต้องถูกปฏิเสธ และ EMERGENCY
ต้องบันทึก ESCALATED โดยไม่เรียก controller (ไม่ถือว่าได้แจ้งแพทย์จริง)

ระหว่างเพิ่ม cross-patient fixture พบ legacy_id ว่างซ้ำติด unique constraint
แก้เฉพาะข้อมูลจำลองให้มี legacy_id แยก ไม่เปลี่ยน patient schema/production data

## จุดที่ต้องระวัง

ยังไม่ได้ตรวจ PostgreSQL concurrency, production config, UI, external connectors,
independent audits, physician sign-off หรือการส่งให้ผู้ป่วย
การผ่าน tests นี้ไม่ใช่ AT01–30 ครบชุด และไม่ใช่การรับรองว่า EP0–10 เสร็จ
ไม่มี deploy หรือ push ในรอบนี้
