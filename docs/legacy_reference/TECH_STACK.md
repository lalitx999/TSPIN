# สรุปกลุ่มเทคโนโลยีที่ใช้งาน (Technology Stack & Libraries)

สถาปัตยกรรมของโปรเจกต์ **Dr. Pat (TSPI)** ประกอบด้วยโมดูลสำคัญในการดูแลจัดการข้อมูลเวชระเบียนพหุมิติและโมเดลปัญญาประดิษฐ์ โดยสรุปรายการเทคโนโลยีและไลบรารีที่ใช้ได้ดังนี้:

---

## 1. ฝั่งหลังบ้าน (Backend Server Stack)

หลังบ้านพัฒนาขึ้นด้วยภาษา Python 3 และเฟรมเวิร์กควบคุมสิทธิ์ที่เน้นเรื่องสถาปัตยกรรมคลาวด์และฐานข้อมูลเชิงสัมพันธ์:

| ชื่อเทคโนโลยี / Library | เวอร์ชัน | บทบาทหน้าที่ทางวิศวกรรม | ไฟล์อ้างอิง |
| :--- | :--- | :--- | :--- |
| **Python** | `>= 3.10` | ภาษาพัฒนาเซิร์ฟเวอร์หลัก | `backend/.venv/` |
| **Django** | `>= 4.2` | โครงสร้างหลัก จัดระบบฐานข้อมูล EMR และ ORM | [requirements.txt](file:///Users/tanchonl/Downloads/drpatt/backend/requirements.txt) |
| **Django REST Framework** | `>= 3.14` | ทำ endpoints ส่งคืนค่าเป็น JSON แบบ REST API | [requirements.txt](file:///Users/tanchonl/Downloads/drpatt/backend/requirements.txt) |
| **SimpleJWT** | `>= 5.3` | ยืนยันความปลอดภัยล็อกอินด้วย JSON Web Tokens | [requirements.txt](file:///Users/tanchonl/Downloads/drpatt/backend/requirements.txt) |
| **psycopg2-binary** | `>= 2.9` | ตัวเชื่อมและจัดการระบบฐานข้อมูล PostgreSQL | [requirements.txt](file:///Users/tanchonl/Downloads/drpatt/backend/requirements.txt) |
| **django-cors-headers** | `>= 4.3` | คุมสิทธิ์เข้าใช้ต่างโดเมนให้ Next.js หน้าบ้าน | [requirements.txt](file:///Users/tanchonl/Downloads/drpatt/backend/requirements.txt) |
| **pandas** | `>= 2.0` | นำเข้าข้อมูลประวัติเก่า แปลงและทำข้อมูล CSV | [requirements.txt](file:///Users/tanchonl/Downloads/drpatt/backend/requirements.txt) |
| **numpy** | *Dynamic* | ประเมินระยะห่าง RAG และสมการโมเดล Ridge OLS | *Dynamic (venv)* |
| **WeasyPrint** | *Dynamic* | แปลงหน้าเว็บรายงาน HTML/CSS เป็นไฟล์ PDF A4 | [views_ai.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_ai.py) |

---

## 2. ฝั่งหน้าบ้าน (Frontend UI & Next.js Stack)

หน้าบ้านขับเคลื่อนด้วย React 19 และ Next.js 16 (App Router) พร้อมการเชื่อมโยงระบบคลังข้อมูลด้วย TypeScript:

| ชื่อเทคโนโลยี / Library | เวอร์ชัน | บทบาทหน้าที่ทางวิศวกรรม | ไฟล์อ้างอิง |
| :--- | :--- | :--- | :--- |
| **Next.js** | `16.2.6` | โครงสร้างควบคุมระบบ Router, Pages และ API | [package.json](file:///Users/tanchonl/Downloads/drpatt/frontend/package.json) |
| **React** | `19.2.4` | ส่วนประมวลผล Components หน้าเว็บหลัก | [package.json](file:///Users/tanchonl/Downloads/drpatt/frontend/package.json) |
| **Genkit (Firebase)** | `^1.33.0` | คุม AI Flows และจัดทำประวัติ Intake สำหรับแพทย์ | [package.json](file:///Users/tanchonl/Downloads/drpatt/frontend/package.json) |
| **@google/generative-ai** | `^0.24.1`| ตัวเชื่อมต่อ Gemini AI สำหรับ RAG และประมวลผลข้อความ | [package.json](file:///Users/tanchonl/Downloads/drpatt/frontend/package.json) |
| **openai** | `^6.37.0` | ตัวเรียก Deepseek Chat API และ Groq Llama 3.3 | [package.json](file:///Users/tanchonl/Downloads/drpatt/frontend/package.json) |
| **admin-lte** | `^4.0.0-rc4`| โครงร่างหน้าแดชบอร์ดแพทย์และธีมสวยงาม | [package.json](file:///Users/tanchonl/Downloads/drpatt/frontend/package.json) |
| **bootstrap** | `^5.3.8` | ระบบ Layout และ Responsive CSS ของหน้าจอผู้ใช้ | [package.json](file:///Users/tanchonl/Downloads/drpatt/frontend/package.json) |
| **recharts** | `^3.8.1` | วาดแผนภูมิประเมินระบบพหุมิติและเทรนด์ผลเลือด | [package.json](file:///Users/tanchonl/Downloads/drpatt/frontend/package.json) |
| **zod** | `^3.24.2` | ตรวจสอบโครงสร้างคำตอบของปัญญาประดิษฐ์และพิมพ์ข้อมูล | [package.json](file:///Users/tanchonl/Downloads/drpatt/frontend/package.json) |
| **firebase** | `^12.13.0`| ระบบเตือนเตือนภัย Web Push (FCM Notifications) | [package.json](file:///Users/tanchonl/Downloads/drpatt/frontend/package.json) |
