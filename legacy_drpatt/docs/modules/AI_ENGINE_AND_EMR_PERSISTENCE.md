# Module: TSPI Clinical AI Engine & EMR Alignment

## ทำอะไร
- ปรับโครงสร้างระบบ AI Engine และการบันทึกประวัติการตรวจลง EMR ไทม์ไลน์จริง (PostgreSQL) ทั้งฝั่ง Django Backend และ Next.js Frontend
- แก้ไข Data Paths จาก Hardcoded Mac (`/Users/tanchonl/...`) เป็น `TSPI_DATA_DIR` (`/mnt/tspidata`) พร้อม Volume Mount ใน Docker
- รวบมาตรฐานการใช้งาน AI API Keys เป็น `GEMINI_API_KEY` และสร้างระบบ 3-Tier Fallback (DeepSeek → Groq → Gemini 2.5 Flash) พร้อมการดึง API Key อัตโนมัติจาก Django Backend เมื่อ Vercel ไม่มี ENV

## ทำไมถึงทำแบบนี้
- **Data Path & Permissions**: เพื่อให้ Django Container บน Linux Home Server สามารถอ่านไฟล์ `tspi_brain_weights.json` และ RAG Datasets ที่เก็บไว้บน Host Disk (`/mnt/tspidata`) ได้อย่างปลอดภัยด้วยสิทธิ์ `755` และ Mount แบบ `ro`
- **Dynamic Key Fetching**: เพื่อแก้ปัญหา Vercel Serverless Function ขาดแคลน ENV API Keys จนเกิด HTTP 401/500 — ให้ Frontend ดึง API Keys ล่าสุดจากหลังบ้าน `/api/settings/ai_settings/` โดยอัตโนมัติ
- **EMR Timeline Persistence**: เพื่อให้ประวัติการวิเคราะห์ 39 แกนของคนไข้ถูกบันทึกลงตาราง `patient_history` จริงทุกครั้งที่เรียก `calculate-precision-medicine`

## โครงสร้างไฟล์
- [`backend/config/settings.py`](file:///Users/tanchonl/Downloads/drpatt/backend/config/settings.py): กำหนด `TSPI_DATA_DIR` พร้อมระบบ Fallback รองรับทั้ง Linux Server และ Mac Local Dev
- [`backend/docker-compose.yml`](file:///Users/tanchonl/Downloads/drpatt/backend/docker-compose.yml): เพิ่ม Volume Mount `- /mnt/tspidata:/mnt/tspidata:ro`
- [`backend/patients/views.py`](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py): ปรับ `weights_path` ใช้ `TSPI_DATA_DIR` และเพิ่มการบันทึก `PatientHistory`
- [`backend/patients/views_ai.py`](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_ai.py): ปรับมาตรฐาน `GEMINI_API_KEY` และบังคับใช้งาน `gemini-2.5-flash`
- [`frontend/src/app/api/ai/brain/route.ts`](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/api/ai/brain/route.ts): ประกาศตัวแปร `activeModel`, `provider`, `dbSystemPrompt` ป้องกัน ReferenceError และใช้ `gemini-2.5-flash`
- [`frontend/src/app/api/ai/report/route.ts`](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/api/ai/report/route.ts): เพิ่มฟังก์ชัน `getReportAiKeys()` ดึงคีย์จากหลังบ้าน และระบบ 3-Tier AI Streaming Cascade

## จุดที่ต้องระวัง
- บน Linux Home Server ต้องไม่ลืมรัน `sudo chmod -R 755 /mnt/tspidata` เมื่อมีการเพิ่มไฟล์ชุดข้อมูลใหม่
- การเรียกใช้ Gemini API โมเดล `gemini-2.5-flash` เป็นโมเดลหลักที่ผ่านการทดสอบว่าใช้งานได้จริง 100% (โมเดลเก่าอย่าง `gemini-1.5-pro` ส่งคืน 404 บน API Endpoint ปัจจุบัน)

## อ้างอิง
- Google Gemini API Documentation (`gemini-2.5-flash`)
- TSPI 39-Axis Precision Medicine Framework Mechanics
