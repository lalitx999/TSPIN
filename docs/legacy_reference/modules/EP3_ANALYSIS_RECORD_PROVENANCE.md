# EP3 — Immutable AnalysisRecord & Provenance

## ทำอะไร

ขยาย `AnalysisRecord` ให้เป็น snapshot append-only ของการวิเคราะห์หนึ่งรอบ พร้อมหลักฐานที่ renderer ต้องใช้อ้างอิงย้อนหลัง:

- `analysis_run_id`: UUID ของ run ที่อ้างอิงข้าม report ได้
- `identity_snapshot`: สถานะและรายละเอียด identity validation ขณะสร้าง run
- `evidence_provenance`: source ownership, source IDs และ marker-to-axis provenance
- `registry_versions`: เวอร์ชัน canonical/module/network registry ที่ใช้จริง
- `created_by`: ผู้ใช้ที่เริ่ม run

`save()` ปฏิเสธการแก้ record เดิม เพื่อให้ต้องสร้าง analysis run ใหม่ทุกครั้งที่ข้อมูลเปลี่ยน

## ทำไมใช้ JSON snapshot

ทางเลือก A: แยกตาราง evidence/provenance ตั้งแต่รอบนี้ — query ได้ละเอียด แต่เป็น schema ใหญ่และต้องมี workflow อัปโหลด/อนุมัติครบก่อน

ทางเลือก B: เก็บ JSON snapshot ใน AnalysisRecord ก่อน — ปิดความเสี่ยง report เปลี่ยนย้อนหลังทันที และยัง migrate ไป evidence table แบบ append-only ในภายหลังได้

EP นี้เลือก B เพราะรักษา core invariant ก่อน โดยไม่สร้าง feature/workflow ใหม่เกินขอบเขต

## R0 ที่ต้อง review ก่อน push/deploy

มี migration ใหม่ `0017_analysisrecord_provenance_and_immutability.py` เพิ่ม 5 columns ใน `patient_analysis_records` เท่านั้น; ไม่มีการลบหรือแก้ข้อมูลเดิม

```bash
cd backend
python manage.py migrate patients 0017
python manage.py test patients.tests.AnalysisRecordProvenanceTests
```

## จุดต้องระวัง

model-level immutability ป้องกัน `.save()` แต่ไม่ได้กัน bulk `QuerySet.update()` ดังนั้น EP5 ต้องไม่ใช้ bulk update กับ `AnalysisRecord`; หากต้องการ audit ระดับ database จะเพิ่ม DB trigger ในรอบ hardening ภายหลัง
