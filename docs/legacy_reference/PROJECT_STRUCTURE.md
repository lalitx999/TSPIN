# โครงสร้างโฟลเดอร์ของโปรเจกต์ (Project Folder Structure)

โครงสร้างไดเรกทอรีหลักของระบบ Dr. Pat ประกอบด้วยสองส่วนหลักคือ **Backend (Django)** และ **Frontend (Next.js)** โดยสรุปหน้าที่ของโฟลเดอร์และไฟล์สำคัญได้ดังนี้:

---

## 1. แผนผังโครงสร้างโฟลเดอร์ (Directory Tree)

```
drpatt/
├── backend/                              # 🐍 Backend (Django Web Framework)
│   ├── config/                           # โฟลเดอร์ตั้งค่าหลักของเซิร์ฟเวอร์
│   │   ├── settings.py                   # 🔑 การตั้งค่าฐานข้อมูล, CORS, Middleware และ SimpleJWT
│   │   └── urls.py                       # 🔀 รูทเตอร์หลักกระจายคำขอไปยังแอปพลิเคชันย่อย
│   ├── accounts/                         # แอปพลิเคชันระบบยืนยันตัวตน (Authentication & Auth App)
│   │   ├── models.py                     # ขยายความสัมพันธ์ผู้ใช้แพทย์/คนไข้
│   │   ├── views.py                      # 🔑 จัดการสมัครสมาชิก ล็อกอินแพทย์/คนไข้ และลงทะเบียน FCM Token
│   │   └── urls.py                       # เส้นทางการยืนยันตัวตนของแอป
│   ├── patients/                         # แอปพลิเคชันคุมเวชระเบียน EMR และคะแนนพหุมิติ (Core App)
│   │   ├── models.py                     # 🌟 [CORE] ตาราง Patient, PatientBiologicalRecord (39 axes), RAG
│   │   ├── serializers.py                # ตัวกรองและแปลงรูปแบบ EMR เป็น JSON เพื่อตอบกลับ REST
│   │   ├── tspi_engine.py                # 🌟 [CORE] ตัวประเมิน NSS, SPS และ Dosing Matrix ระดับหลังบ้าน
│   │   ├── views.py                      # REST API ViewSet คุมระบบเวชระเบียนและการวิเคราะห์แบบคงที่
│   │   ├── views_ai.py                   # 🔗 [CONNECTION] Logic ถอดความเสียง SOAP, ทำ OCR แล็บ, ประมวล RAG, WeasyPrint PDF
│   │   ├── views_line.py                 # 🔗 [CONNECTION] บอทซักประวัติติดตามอาการบน LINE OA และการซิงค์ EMR
│   │   ├── templates/
│   │   │   └── patients/
│   │   │       └── precision_medicine_report_v4.html  # 🌟 [CORE] โครงร่างเอกสารรายงานพรีเมียม WeasyPrint PDF
│   │   └── urls.py                       # เส้นทางรูท API คลินิกทั้งหมด
│   ├── manage.py                         # สคริปต์รันและจัดการ Django
│   └── requirements.txt                  # ไลบรารี Python หลักของ Backend
│
├── frontend/                             # ⚛️ Frontend (Next.js 16.2.6 & React 19)
│   ├── src/
│   │   ├── app/                          # Next.js App Router (Pages & API Routes)
│   │   │   ├── patient/                  # 🏥 หน้าจอและเมนูสำหรับคนไข้ (Mobile Friendly)
│   │   │   │   ├── dashboard/page.tsx    # 🌟 [CORE] แดชบอร์ดคนไข้ แสดงตาราง Biomarkers 2x2 และเตือนภัย
│   │   │   │   └── ai-intake/page.tsx    # แชทอัตโนมัติซักประวัติตามกฎความปลอดภัย
│   │   │   ├── doctor/                   # หน้าจอและแดชบอร์ดการจัดการของแพทย์
│   │   │   │   ├── ai-physician/page.tsx # 🌟 [CORE] หน้าจอประเมินชีววิทยาและสั่งสร้างรายงาน AI
│   │   │   │   └── knowledge-rag/page.tsx# หน้าอัพโหลดคลังเอกสาร RAG และสร้างเวกเตอร์
│   │   │   ├── api/                      # Next.js API Routes (Server-side AI Proxy)
│   │   │   │   └── ai/
│   │   │   │       ├── report/route.ts   # 🔗 [CONNECTION] สตรีมมิ่งประเมินผลรายงานผ่าน Deepseek / Groq
│   │   │   │       └── brain/route.ts    # 🔗 [CONNECTION] วิเคราะห์ผลแล็บและประสาน RAG คลินิก
│   │   │   └── globals.css               # สไตล์สีหลักของระบบตามชุดสีพรีเมียม (HSL CSS)
│   │   ├── components/                   # React Components (UI, Charts, Sidebar)
│   │   ├── data/                         # นิยามและคลังข้อมูลระบบพหุมิติของ TSPI (JSON)
│   │   │   ├── 39_last_x.json            # 🌟 [CORE] นิยามอย่างเป็นทางการของ 12 โดเมน และ 39 แกนชีวภาพ
│   │   │   ├── tspi_36_axes_v2.json      # นิยามแกนชีวภาพฉบับอัปเดตภาษาไทย/อังกฤษและกลไกย่อย ABC
│   │   │   └── 200_module_tspi.json      # คลังยาสมุนไพรและระบบจัดเกรดยาสมุนไพร TSPI
│   │   ├── lib/                          # AI Flows และตรรกะระบบ RAG
│   │   │   ├── tspi-engine.ts            # ตัวประเมินคะแนนแกนและจัดสรรยาคู่ขนานฝั่ง Next.js (Client Engine)
│   │   │   └── precision-medicine-flow.ts# ตัวควบคุมขั้นตอนวิเคราะห์ RAG ของคนไข้
│   │   └── utils/                        # ตัวช่วยทางเทคนิคและ Firebase Adapters
│   ├── package.json                      # การตั้งค่าแอปพลิเคชันหน้าบ้านและไลบรารี JavaScript/TypeScript
│   └── tsconfig.json                     # การตั้งค่า TypeScript
│
└── data/                                 # 📂 คลังข้อมูลและไฟล์น้ำหนักสมองกลจำลอง (Brain Weight JSON)
```

---

## 2. บทบาทหน้าที่ของไฟล์สำคัญระดับระบบ (Core & Connection Files)

### 🌟 ไฟล์หลักของระบบ (Core Files)
1. **[backend/patients/models.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/models.py)**: โครงสร้าง EMR ทั้งหมดของระบบ ประวัติผู้ป่วยย้อนหลัง สิทธิ์ความยินยอม PDPA และข้อมูล RAG
2. **[backend/patients/tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py)**: ระบบที่ทำหน้าที่คำนวณคะแนน NSS, SPS แนะนำยาสมุนไพร และคัดกรองความปลอดภัย (Safety Gate) ฝั่งเซิร์ฟเวอร์
3. **[frontend/src/data/39_last_x.json](file:///Users/tanchonl/Downloads/drpatt/frontend/src/data/39_last_x.json)**: นิยามมาตรฐานของโดเมนและแกนชีวภาพที่เป็นหนึ่งเดียวของระบบ (Ontology Source)
4. **[frontend/src/app/doctor/ai-physician/page.tsx](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/doctor/ai-physician/page.tsx)**: แดชบอร์ดแพทย์สำหรับวิเคราะห์ผลแล็บ ประเมินคนไข้ และแสดงรายงานสรุปผล
5. **[backend/patients/templates/patients/precision_medicine_report_v4.html](file:///Users/tanchonl/Downloads/drpatt/backend/patients/templates/patients/precision_medicine_report_v4.html)**: เทมเพลตสำหรับหน้ากระดาษรายงานแพทย์พรีเมียมขนาด A4

### 🔗 ไฟล์เชื่อมต่อระบบ (Connection Files)
1. **[backend/patients/views_ai.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_ai.py)**: ประสานกระบวนการถอดความเสียงแพทย์, แปลง OCR ค่าแล็บ, จัดทำเวกเตอร์ RAG และคอมไพล์ PDF ด้วย WeasyPrint
2. **[backend/patients/views_line.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_line.py)**: ตัวเชื่อมบอทซักประวัติอัตโนมัติบน LINE OA ส่งข้อความและซิงค์ข้อมูลคนไข้ลงฐานข้อมูล PostgreSQL EMR
3. **[frontend/src/app/api/ai/report/route.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/api/ai/report/route.ts)**: ประสานการสตรีมมิ่งข้อมูลคำวินิจฉัยจาก Next.js ไปยัง Deepseek/Groq API เพื่อเรนเดอร์ในแดชบอร์ดแพทย์
