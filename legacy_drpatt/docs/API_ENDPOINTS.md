# รายการ API Endpoints (API Endpoint Registry)

นี่คือรายการ API Endpoints ทั้งหมดของฝั่งหลังบ้าน (Django Backend) ซึ่งเปิดให้บริการผ่านคำนำหน้า URL `/api/` (ดูรายละเอียดตัวคุมเส้นทางที่ [urls.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/urls.py) และ [accounts/urls.py](file:///Users/tanchonl/Downloads/drpatt/backend/accounts/urls.py)):

---

## 1. ระบบจัดการสิทธิ์และบัญชีผู้ใช้งาน (Authentication & User Accounts)

| HTTP Method | API Path | หน้าที่การทำงาน | ไฟล์ประมวลผล (Django Logic) |
| :--- | :--- | :--- | :--- |
| **POST** | `/api/auth/activate/` | ตรวจสอบเบอร์โทรและชื่อผู้ป่วยใน EMR 3,028 เคสเดิมเพื่ออนุญาตให้เปิดสิทธิ์ผู้ใช้งาน | [accounts/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/accounts/views.py) |
| **POST** | `/api/auth/register/` | ลงทะเบียนเปิดบัญชีผู้ใช้ระบบคนไข้ สร้างข้อมูลล็อกอินใน PostgreSQL และผูกกับ EMR | [accounts/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/accounts/views.py) |
| **POST** | `/api/auth/login/` | ยืนยันรหัสผ่านบัญชีคนไข้ คืนค่าสิทธิ์ความปลอดภัยในรูปแบบ JWT Token | [accounts/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/accounts/views.py) |
| **GET** | `/api/auth/me/` | ดึงรายละเอียดโปรไฟล์คนไข้และเวชระเบียนของผู้ใช้ปัจจุบันที่ทำการส่ง Token มา | [accounts/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/accounts/views.py) |
| **POST** | `/api/auth/doctor/login/` | ยืนยันตัวตนสำหรับสิทธิ์การทำงานของฝั่งแพทย์ผู้ดูแลและเจ้าหน้าที่คลินิก | [accounts/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/accounts/views.py) |
| **GET** | `/api/auth/doctor/me/` | เรียกคืนข้อมูลโปรไฟล์และสิทธิ์ของแพทย์ผู้ลงชื่อใช้งาน | [accounts/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/accounts/views.py) |
| **POST** | `/api/auth/register-fcm-token/` | ลงทะเบียนและผูกบันทึก VAPID Push Notification Token ของคนไข้ลงฐานข้อมูล | [accounts/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/accounts/views.py) |
| **POST** | `/api/auth/change-password/` | เปลี่ยนรหัสผ่านของผู้เข้าใช้งานที่มีสถานะเข้าสู่ระบบอยู่ | [accounts/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/accounts/views.py) |

---

## 2. ระบบเวชระเบียนและการประมวลผลทางชีวภาพ (EMR & Systems Biology Engine)

| HTTP Method | API Path | หน้าที่การทำงาน | ไฟล์ประมวลผล (Django Logic) |
| :--- | :--- | :--- | :--- |
| **GET** | `/api/patients/` | ค้นหา ดึงประวัติข้อมูล EMR และข้อมูลระดับโมเลกุล (Labs, Proteomics) ของคนไข้ทั้งหมด | [patients/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py) |
| **POST** | `/api/patients/` | เพิ่มข้อมูลประวัติเวชระเบียนคนไข้ใหม่เข้าระบบ PostgreSQL | [patients/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py) |
| **GET** | `/api/patients/list-lightweight/` | ดึงข้อมูลย่อ (HN, ชื่อ, อายุ) สำหรับใช้จัดทำตัวเลือกแสดงเคสคนไข้แบบประหยัดแรม | [patients/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py) |
| **GET** | `/api/patients/all-lab-results/` | ค้นหาข้อมูลและคอมไพล์ผลแล็บตรวจเลือดทั้งหมดในระบบประวัติตรงเข้าหน้าแพทย์ | [patients/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py) |
| **GET** | `/api/patients/<pk>/tspi-analysis/` | เรียกประเมินผลคะแนนวิจัย 39 แกน (NSS, SPS และการจัดกลุ่มยา) ตามคะแนนปัจจุบัน | [patients/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py) |
| **POST** | `/api/patients/<pk>/calculate-precision-medicine/` | อัปเดตแล็บ/อาการ สั่งคำนวณหรือใช้สมองกลพยากรณ์ และบันทึกประวัติตัวชี้วัดลงฐานข้อมูล | [patients/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py) |
| **GET** | `/api/patients/<patient_id>/reports/<report_id>/pdf/` | สร้างและส่งออกสรุปรายงานฉบับพรีเมียม WeasyPrint PDF แบบสตรีมดาวน์โหลด | [patients/views_ai.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_ai.py) |
| **GET** | `/api/records/` | ค้นหารายการบันทึกคะแนนแกนชีวภาพย้อนหลังทั้งหมดของประวัติคนไข้ | [patients/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py) |
| **GET** | `/api/history/` | เรียกดูประวัติการรักษาย้อนหลังในไทม์ไลน์ (เช่น ผลแล็บ, เอกสารสรุปของแพทย์) | [patients/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py) |
| **GET** | `/api/appointments/` | เรียกดูข้อมูลรายการการนัดตรวจโรคของคนไข้ | [patients/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py) |
| **GET** | `/api/pdpa-consent/` | เรียกดูสถานะความยินยอมการเปิดเผยประวัติการักษาตามข้อตกลงกฎหมาย PDPA | [patients/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py) |
| **GET** | `/api/settings/` | ตรวจสอบตั้งค่าระบบ (เช่น ค่าน้ำหนักถ่วงเกณฑ์คะแนนแกน, ค่าคีย์ AI Provider) | [patients/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py) |

---

## 3. ระบบเชื่อมต่อปัญญาประดิษฐ์และ RAG (AI & Knowledge RAG Services)

| HTTP Method | API Path | หน้าที่การทำงาน | ไฟล์ประมวลผล (Django Logic) |
| :--- | :--- | :--- | :--- |
| **POST** | `/api/ai/voice-to-soap/` | อัปโหลดไฟล์บันทึกเสียงหมอ ถอดความเสียง และจัดโครงสร้างฟอร์ม EMR SOAP | [patients/views_ai.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_ai.py) |
| **POST** | `/api/ai/analyze-lab-ocr/` | รับรูปภาพผลแล็บและแปลงเป็น JSON รายการแล็บและพิกัดความผิดปกติของช่วงอ้างอิง | [patients/views_ai.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_ai.py) |
| **POST** | `/api/ai/simulate-biology/` | จำลองการเติบโตหรือทดสอบผลตอบรับการรับสมุนไพร | [patients/views_ai.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_ai.py) |
| **POST** | `/api/ai/train-brain-model/` | สั่งฝั่งหลังบ้านดึงข้อมูลประวัติและฝึกฝนค่าน้ำหนักสมองกลแบบ OLS Ridge | [patients/views_ai.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_ai.py) |
| **GET** | `/api/ai/brain-training-stats/` | ดึงจำนวนสถิติข้อมูลที่มีอยู่สำหรับการประเมินฝึกฝนระบบโมเดลพยากรณ์ | [patients/views_ai.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_ai.py) |
| **GET** | `/api/knowledge-segments/` | เรียกดูข้อมูลอ้างอิงคลังเวชศาสตร์ RAG และเรียกอัปเดตเวกเตอร์ RAG | [patients/views_ai.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_ai.py) |

---

## 4. ระบบประตูทางผ่าน LINE OA (LINE Official Account Webhook Gateways)

| HTTP Method | API Path | หน้าที่การทำงาน | ไฟล์ประมวลผล (Django Logic) |
| :--- | :--- | :--- | :--- |
| **POST** | `/api/line/webhook/` | ช่องทางรับค่า Webhook จากข้อความสนทนาคนไข้ และทำ AI Intake | [patients/views_line.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_line.py) |
| **POST** | `/api/line/link/` | ลิงก์ LINE User ID เข้ากับข้อมูล EMR ของผู้ใช้โดยระบุหมายเลขโทรศัพท์และโทเค็นความปลอดภัย | [patients/views_line.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_line.py) |
| **POST** | `/api/liff/identity/` | ตรวจสอบระบุสิทธิ์ความถูกต้องของคนไข้เมื่อกดเปิด LIFF Application | [patients/views_line.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_line.py) |
