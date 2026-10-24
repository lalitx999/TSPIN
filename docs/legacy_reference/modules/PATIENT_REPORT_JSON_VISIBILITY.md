# Module: Patient report JSON visibility

## ทำอะไร

PatientSerializer ไม่คืน extra_data.generated_reports และ latest_precision_insight
ให้ผู้ป่วยหรือ serializer ที่ไม่มี request context เจ้าหน้าที่ยังใช้ข้อมูลเพื่อตรวจทานได้
ใช้สำเนาข้อมูลก่อนกรอง ไม่ลบ/แก้ข้อมูลในฐานข้อมูล

ผู้ป่วยไม่สามารถเขียน extra_data ผ่าน serializer นี้ หรือส่ง generated_reports /
latest_precision_insight เป็นฟิลด์ระดับบนเพื่อให้ perform_update เก็บอ้อมลง extra_data

## ทำไมถึงทำแบบนี้

การซ่อนปุ่มหน้าเว็บอย่างเดียวไม่ป้องกันการอ่าน JSON โดยตรง
จึงกรองฝั่ง backend ที่ serializer ซึ่งใช้ร่วมกันใน list/detail/account responses
ข้อแลกเปลี่ยน: ผู้ป่วยไม่สามารถแก้ metadata ผ่าน extra_data แบบอิสระได้อีก
ฟอร์มที่ใช้ช่องนี้ต้องเปลี่ยนเป็น patient-input endpoint ที่มี schema/สิทธิ์เฉพาะ
context ที่หายไปจะไม่เปิดเผยร่างรายงานโดยปริยาย

## โครงสร้างไฟล์

- backend/patients/serializers.py: response filtering และ write validation
- backend/patients/tests_patient_report_visibility.py: 7 regression tests

## ขอบเขตที่ยังต้องตรวจ

นี่คือการปิดสอง report fields ที่พบ ไม่ใช่ allowlist ทั้ง extra_data
ยังต้องตรวจ tspi-analysis/biological records, raw dictionaries, LINE messages,
frontend caches และ endpoint อื่นที่ไม่ผ่าน PatientSerializer
ไม่ได้รับรองว่า clinical data ทุกชนิดถูกกรองแล้ว
ยังไม่เปิด patient report release จนมี trusted sign-off

## ผลทดสอบ

ทดสอบ owner list/detail, staff review, missing context, cross-patient access,
metadata injection/erasure และ top-level alias bypass บน SQLite :memory:
ไม่มี production migration/deploy/push
18 October 2026: ชุดรวม 184 tests ผ่าน (exit 0), Django system check ไม่พบปัญหา
