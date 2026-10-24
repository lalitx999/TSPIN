# Module: EP1 — แก้ลงทะเบียนไม่สมบูรณ์ & ป้องกันการผูก LINE ผิดคน

## ทำอะไร
ปรับปรุงกระบวนการลงทะเบียนผู้ป่วยและเปิดใช้งานบัญชี (Wizard Registration Flow) ให้รองรับการกู้คืนและซ่อมแซมบัญชี (Incomplete Account Auto-Repair) กรณีที่มีบัญชีผู้ใช้ในระบบ `auth_user` แต่ไม่มีโปรไฟล์เวชระเบียน `patients` รวมถึงเพิ่มระบบป้องกันการผูกบัญชี LINE OA ข้ามคน (Cross-Patient LINE User Binding Protection)

---

## ทำไมถึงทำแบบนี้
1. **แก้ปัญหากรณีการลงทะเบียนหลุดค้าง (Incomplete Registration):** หากเกิดข้อผิดพลาดในการลงทะเบียนครั้งก่อน (เช่น Database Timeout หรือ Audit Log มีปัญหา) ผู้ใช้อาจมีบัญชี `User` แล้วแต่ยังไม่มีโปรไฟล์ `Patient` เมื่อผู้ใช้กลับมาสมัครใหม่ ระบบจะทำการซ่อมแซมและผูกโปรไฟล์ `Patient` ให้กับ `User` เดิมทันทีโดยไม่สร้างบัญชีซ้ำ
2. **ป้องกันการผูกบัญชี LINE OA ผิดคน:** หาก `line_user_id` ถูกผูกไว้กับผู้ป่วยท่านอื่นที่มีเลขบัตรประชาชนต่างกัน ระบบจะปฏิเสธการลงทะเบียนทันที พร้อมแจ้งเตือน error 400 เพื่อป้องกันข้อมูลสุขภาพรั่วไหลข้ามคน

---

## โครงสร้างไฟล์
- `backend/accounts/views.py`: ปรับปรุงฟังก์ชัน `_patient_register` เพื่อเพิ่มการตรวจสอบ `other_line_patient` และเพิ่ม logic ซ่อมแซมบัญชีหลุดค้าง
- `backend/patients/tests.py`: เพิ่ม Unit Test `test_incomplete_account_recovers_successfully` และ `test_cross_patient_line_binding_rejected`

---

## จุดที่ต้องระวัง
- การจัดการสิทธิ์และการซ่อมแซมบัญชีต้องอยู่ภายใต้ `transaction.atomic` เสมอ เพื่อให้มั่นใจว่าเมื่อมีข้อผิดพลาด ระบบจะทำการ Rollback ทั้งหมด 100%
- ผู้ใช้ที่ต้องการรันการทดสอบ Unit Test สามารถรันคำสั่งได้ด้วยตัวเอง (ตามกฎเหล็กข้อ 5.3):
  `python backend/manage.py test patients.tests.PatientRegistrationTests`

---

## อ้างอิง
- เอกสารเกณฑ์ตรวจรับ EP1 (รอบแก้ 22.09.2026)
- [views.py](file:///Users/tanchonl/Downloads/drpatt/backend/accounts/views.py)
- [tests.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tests.py)
