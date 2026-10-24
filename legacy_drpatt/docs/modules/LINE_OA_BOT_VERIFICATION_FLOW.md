# Module: LINE OA Patient Verification & Flex Message Flow

## ทำอะไร
- พัฒนาระบบยืนยันตัวตนคนไข้ผ่านแชต LINE Official Account (LINE OA) ด้วยเลขบัตรประชาชน 13 หลักเพื่อค้นหาจาก PostgreSQL จริง
- ออกแบบ Flex Messages สวยงามแบบ 100% สำหรับข้อความทักทาย, ข้อความยืนยันชื่อคนไข้สำเร็จ, และการ์ดเด้งลิงก์ไปหน้าลงทะเบียน
- เชื่อมโยงระบบลงทะเบียนออนไลน์ (`https://tspi.vercel.app/patient/register?line_user_id=...`) เข้ากับ LINE OA Push Message อัตโนมัติ

## ทำไมถึงทำแบบนี้
- **Security & Privacy**: ป้องกันไม่ให้บอทเปิดแชตซักประวัติหลุดไปหาคนนอก โดยต้องผ่านการยืนยันเลขบัตรประชาชน 13 หลักในตาราง `patients` (`user`) ก่อน
- **Seamless Registration**: กรณีไม่พบข้อมูล คนไข้สามารถกดปุ่ม Flex เด้งไปลงทะเบียนในเว็บได้ทันที เมื่อกรอกเสร็จระบบจะส่ง Flex Message ต้อนรับกลับไปใน LINE Chat ทันทีโดยไม่ต้องพิมพ์ใหม่
- **No Mockup**: ข้อมูลทุกส่วนอิงตามเรคคอร์ดใน PostgreSQL (`id_card`, `first_name`, `last_name`, `hn`, `line_user_id`) 100%

## โครงสร้างไฟล์
- [`backend/patients/line_flex_builder.py`](file:///Users/tanchonl/Downloads/drpatt/backend/patients/line_flex_builder.py): เพิ่มฟังก์ชัน `build_greeting_flex()`, `build_verified_patient_flex()`, และ `build_registration_link_flex()`
- [`backend/patients/views_line.py`](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_line.py): เพิ่มการตรวจจับคำสั่ง `"เปิดใช้งานบอท"`, `"ปิดใช้งานบอท"`, การตรวจสอบเลข 13 หลัก, การผูก `line_user_id` และการสลับโหมดซักประวัติ AI
- [`backend/accounts/views.py`](file:///Users/tanchonl/Downloads/drpatt/backend/accounts/views.py): ในฟังก์ชัน `patient_register` เพิ่มการรับ `line_user_id` และยิง LINE Push Message ต้อนรับกลับทันทีหลังลงทะเบียนเสร็จ
- [`frontend/src/app/patient/register/page.tsx`](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/patient/register/page.tsx): ดึง Query Parameter `line_user_id` จาก URL แล้วส่งแนบไปใน POST Request ของการลงทะเบียน

## จุดที่ต้องระวัง
- เมื่ออัปเดตไฟล์ฝั่งหลังบ้านแล้ว ต้องรัน `docker compose up -d --build` บน Home Server เพื่อให้ Webhook ใช้โค้ดใหม่
- ต้องตรวจสอบว่า Channel Access Token ของ LINE Messaging API บนหลังบ้านมีความถูกต้องและมีสิทธิ์ส่ง Push Message

## อ้างอิง
- LINE Messaging API Documentation (Flex Message / Reply / Push)
- TSPI EMR PostgreSQL Database Schema (`patients` table)
