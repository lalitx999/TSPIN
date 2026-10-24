# Module: Agentic release readiness diagnostics

## ทำอะไร

เพิ่ม GET `/api/patients/{patient_id}/agentic-artifacts/{artifact_id}/release-readiness/`
สำหรับผู้ตรวจสอบที่มีสิทธิ์ดู artifact และ canonical/registry inputs
ตรวจ integrity, patient scope และสร้าง manifest ปัจจุบันเทียบกับฉบับที่บันทึกไว้
ตรวจ registry ที่ยังอนุมัติอยู่และรายงานเหตุผลที่ยังส่งไม่ได้

## ทำไมถึงทำแบบนี้

ทางเลือกใช้สถานะ AnalysisReportRelease เดิมทันทีไม่มี binding กับ AgenticArtifact ใหม่
จึงไม่สามารถถือเป็นการอนุมัติร่างนี้ได้ อีกทางเลือกคือเพิ่ม diagnostics แบบอ่านอย่างเดียวก่อน
ซึ่งทำในรอบนี้ เพื่อไม่เปิดสิทธิ์เผยแพร่จากข้อมูลอนุมัติที่ยังไม่ตรวจสอบ

## โครงสร้างไฟล์

- backend/patients/release_readiness.py: read-only revalidation service
- backend/patients/views.py: GET action พร้อม permission/error handling
- backend/patients/tests_agentic_service.py: เพิ่ม 4 regression cases

## ขอบเขตและข้อควรระวัง

- `state=BLOCKED`, `send_allowed=false`, `clinical_use_authorized=false` เสมอในเวอร์ชันนี้
- แสดงว่ายังขาด artifact-bound physician approval, current release consent,
  verified recipient/channel และ pre-send safety recheck
- ไม่ใช้ staff/doctor group เป็นหลักฐานใบอนุญาต ไม่ใช้ legacy release เป็นลายเซ็นอนุมัติร่างใหม่
- ข้อมูลตรงกับปัจจุบันไม่ได้แปลว่าอนุมัติให้ส่งได้
- ไม่ใช่ send token ไม่บันทึก approval ไม่เรียก provider ไม่เปลี่ยนประวัติ
- ยังไม่เชื่อมบังคับเส้นทาง PDF/LINE/การส่งเดิม จึงไม่อ้างว่าปิด release gates ทั้งระบบแล้ว
- ยังต้องทำ trusted physician verification, signed output binding และ consent/delivery integration

## ผลทดสอบ

18 October 2026: artifact service/API suite 18 ข้อผ่านบน SQLite :memory:
เพิ่มกรณี read-only/no approval, identity เปลี่ยน, registry retired,
GET permission และ POST ต้องได้ 405 ไม่มี production migration/deploy/push
รันชุดรวมซ้ำ 162 tests ผ่าน (exit 0), Django system check ไม่พบปัญหา
