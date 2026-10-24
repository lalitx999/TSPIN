# Module: Canonical correction and safety alert regression hardening

## ทำอะไร

- แก้การนำเข้าข้อมูลซ้ำ: เมื่อ correction แทนหลักฐานต้นฉบับ สำเนาของ observation เดียวกันต้องไม่กลับมาเป็น active
- เก็บทุกแถวใน evidence_history ไม่ลบข้อมูลต้นฉบับ
- ไม่เลิกใช้ข้อมูลที่มาจากคนละ source หรือมีเนื้อหาต่างกัน ความขัดแย้งยังต้อง BLOCKED
- เมื่อ assessment ใหม่ใช้ยืนยันไม่ได้ ให้คง alert เดิมสำหรับ clinician review แทนการบดบังด้วย CLEAR ที่ยังไม่ยืนยัน
- ไม่เพิ่มเกณฑ์วินิจฉัยหรืออนุญาตให้รักษาอัตโนมัติ

## ทำไมถึงทำแบบนี้

ทางเลือกแรกคือแก้เฉพาะ ID ต้นฉบับ แต่สำเนาที่มี ID อื่นจะยังถูกใช้ซ้ำได้
ทางเลือกที่ใช้คือเทียบ source/concept/เวลาแบบ UTC/version/เนื้อหา เพื่อเลิกใช้เฉพาะสำเนาที่เทียบเท่ากัน
ส่วน safety เลือกคงคำเตือนให้ผู้ตรวจสอบเห็นเมื่อข้อมูลใหม่ไม่น่าเชื่อถือ
ข้อแลกเปลี่ยนคืออาจมีคำเตือนเก่าที่ต้องให้แพทย์ทบทวน ไม่ได้แปลว่ามีเหตุฉุกเฉินที่ยืนยันแล้ว

## โครงสร้างไฟล์

- backend/patients/canonical_state.py: observation signature และ snapshot v2
- backend/patients/safety_contracts.py: รักษา alert เมื่อข้อมูลใหม่ไม่ผ่าน validation
- backend/patients/safety_service.py: snapshot ใหม่ระบุ safety-completeness-v2
- backend/patients/safety_history.py: replay แยก v1/v2 โดยไม่ตีความประวัติใหม่
- backend/patients/tests_canonical_state.py และ tests_safety_contracts.py: regression tests

## ผลตรวจ

จำลอง canonical regression ก่อนแก้พบ failure จริง และ safety regression พบว่า
unverified, malformed timestamp, patient-reported และ future CLEAR บดบัง EMERGENCY เดิม
หลังแก้ pure suite รวม 64 tests ผ่าน เมื่อ 18 October 2026
รวมทดสอบข้อมูลคนละ source ต้องยังขัดแย้ง, input ordering,
current verified clinician assessment และ legacy selection semantics

## จุดที่ต้องระวัง

- v2 ทำให้ canonical manifest hash เปลี่ยน ต้อง preview/review และคำนวณใหม่ ไม่แก้ stored snapshot เก่า
- legacy v1 replay เป็นการจำลองประวัติ ไม่ใช่การรับรองความปลอดภัยปัจจุบัน
- ยังไม่ได้ทดสอบ Django/database/API integration หรือ migration
- ไม่ deploy, push หรือแก้ production ในรอบนี้
- หลักเกณฑ์ clinical clearance และ freshness ยังต้องผ่านการอนุมัติจากแพทย์
