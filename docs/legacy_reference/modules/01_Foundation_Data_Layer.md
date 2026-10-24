# Module: 01 - Foundation & Data Layer

## ทำอะไร
- วางโครงสร้างข้อมูลพื้นฐาน (Data Models / TypeScript Interfaces) เพื่อเป็นกระดูกสันหลังของระบบ TSPI Clinical System
- ออกแบบ Data Schema เพื่อรองรับ 39 Axes และการทำแบบสอบถามแบบ Hybrid (Static Core + AI Generated)

## ทำไมถึงทำแบบนี้
- **ใช้ Hybrid Approach:** เพื่อให้ระบบสามารถเก็บ Data ได้สม่ำเสมอสำหรับการพล็อตกราฟแนวโน้มระยะยาว (Trend) จาก Core Questions และสามารถใช้ AI เจาะลึกรายบุคคล (Personalized) เพื่อเพิ่ม Engagement ของคนไข้
- **มี `isAiGenerated`:** เพื่อใช้แยกแยะระหว่าง "ข้อมูลมาตรฐาน (Baseline)" กับ "ข้อมูลเฉพาะกิจ" ทำให้ง่ายต่อการกรองข้อมูลเวลาดู Dashboard
- **บังคับมี `linkedAxes`:** เพื่อให้คำตอบทุกข้อ (แม้แต่ของที่ AI แต่ง) วิ่งกลับไปสู่แกนทางชีววิทยา (Systems Biology Axes) เพื่อการวิเคราะห์แนวโน้มเสมอ

## โครงสร้างไฟล์
- `/frontend/src/types/clinical.ts`: เก็บ Interface ทั้งหมด 
  - `SystemAxis`
  - `QuestionItem`
  - `QuestionnaireSession`
  - `QuestionnaireResponse`

## จุดที่ต้องระวัง
- `SystemAxis` ปัจจุบันยังเป็นแค่ข้อมูลจำลอง (Mock) ต้องนำชื่อ 39 Axes ของจริงทางการแพทย์มาเติมให้ครบในอนาคต
- การ Map Data ก่อนส่งขึ้น Firestore ต้องระวังชนิดของตัวแปรวันที่ (JavaScript `Date` vs Firestore `Timestamp`)

## อ้างอิง
- [TSPI_CLINICAL_SYSTEM.md](../TSPI_CLINICAL_SYSTEM.md) (Master Architecture)
