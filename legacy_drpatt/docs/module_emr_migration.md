# Module: EMR Migration & Firebase Removal

## ทำอะไร
- ทำการย้ายฐานข้อมูลและ API ของระบบทั้งฝั่งแพทย์ (Doctor Portal) และคนไข้ (Patient Portal) จากระบบลูกผสม (Firebase Firestore / Cloud Functions) มาทำงานบนระบบ EMR หลัก (Django REST Framework + PostgreSQL) แบบเต็มรูปแบบ 100%
- ทำความสะอาดโค้ด ลบไลบรารีและคำสั่งที่เชื่อมต่อตรงหา Firestore (SDK client-side) เพื่อแก้ไขปัญหาระบบดึงข้อมูลผู้ป่วยไม่ได้และทำให้ระบบสามารถ Build ผ่านได้อย่างถูกต้อง (TypeScript Clean Build)

## ทำไมถึงทำแบบนี้
- **เลือกวิธีนี้เพราะ**: ต้องการใช้ Django + PostgreSQL เป็น Single Source of Truth ตามกฎสถาปัตยกรรมระบบ การเชื่อมต่อตรงผ่าน Firestore ทำให้เกิดข้อมูลซ้ำซ้อน ดึงผลลัพธ์การจัดกลุ่มอาการ (Triage) ของคนไข้ได้ไม่แน่นอน และจัดการ PDPA ได้ยากกว่า
- **ทางเลือกอื่นที่คิดไว้**: การคงโครงสร้าง Firestore เป็น Read-replica — แต่ยกเลิกเพราะทำให้โค้ดฝั่ง Next.js ซับซ้อนโดยไม่จำเป็น และเสี่ยงต่อข้อมูลคลาดเคลื่อนระหว่าง PostgreSQL และ Firestore

## โครงสร้างไฟล์
- [frontend/src/utils/firebase/services.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/utils/firebase/services.ts) - เป็น Adapter แปลงคำสั่งดั้งเดิมของ Firebase ให้กลายเป็น REST requests ไปที่ Django API
- [frontend/src/app/doctor/ai-physician/page.tsx](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/doctor/ai-physician/page.tsx) - ปรับปรุงการโหลดข้อมูลผู้ป่วย บันทึก EMR และสร้างรายงานวิเคราะห์ผ่านระบบ REST API
- [frontend/src/app/doctor/chats/page.tsx](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/doctor/chats/page.tsx) - ย้ายประวัติข้อความเสียง/รูปภาพเข้าฐานข้อมูล PostgreSQL
- [frontend/src/app/patient/checkin/](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/patient/checkin/) - หน้าเช็คอินบันทึก Questionnaire Sessions ลงฟิลด์ `extra_data` ในฐานข้อมูลกลาง
- [frontend/src/app/patient/ai-intake/page.tsx](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/patient/ai-intake/page.tsx) - แชทซักประวัติอัจฉริยะฝั่งคนไข้ เชื่อมต่อประวัติ EMR ด้วยระบบ Polling ทุก 3 วินาทีไปยัง PostgreSQL
- [frontend/src/app/patient/consent/page.tsx](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/patient/consent/page.tsx) - บันทึกผลยอมรับ PDPA เข้าฐานข้อมูล EMR

## จุดที่ต้องระวัง
- **การใช้ Polling ในห้องแชท**: ในหน้า `patient/ai-intake` และ `doctor/chats` การเปลี่ยนจาก Firestore Realtime (`onSnapshot`) มาเป็น Polling (ทุก 3 วินาที) อาจทำให้เกิด HTTP request load เพิ่มขึ้นเล็กน้อยในฝั่ง Django Backend หากมีผู้ใช้งานปริมาณมาก ควรเตรียมปรับปรุงเป็น WebSockets หรือ Server-Sent Events (SSE) ในอนาคตหากต้องการ Realtime แท้จริง
- **การเก็บข้อมูลใน `extra_data`**: เนื่องจากเก็บ Questionnaire และแชทไว้ใน JSONField (`extra_data`) หากขนาดประวัติแชทคนไข้ยาวมาก ขนาดฟิลด์อาจจะใหญ่ขึ้น ในระยะยาวควรพิจารณาแยกไปเป็นตารางความสัมพันธ์เฉพาะ

## อ้างอิง
- [Walkthrough.md](file:///Users/tanchonl/.gemini/antigravity-ide/brain/d69bd92e-f5f6-4263-8b2d-c98bccfd5383/walkthrough.md) - สรุปการทดสอบและผลลัพธ์
- [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py) - ระบบคำนวณคะแนนแกนชีวภาพหลัก
