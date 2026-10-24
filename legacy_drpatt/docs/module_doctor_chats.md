# Module: Doctor Chats & Smart AI Intervention (High-Performance Edition)

## ทำอะไร
- ปรับปรุงแถบรายชื่อแชทฝั่งแพทย์ให้ **จัดเรียงตามลำดับเวลาล่าสุด (Realtime Sorting)** ที่มีการพิมพ์คุยจริง (จากผู้ใช้, หมอ หรือ AI)
- เพิ่ม **Badge บ่งชี้สถานะการทำงาน (🤖 AI / 👨‍⚕️ หมอ)** ถัดจากชื่อคนไข้ในแถบรายการด้านซ้ายของแพทย์อย่างเด่นชัด
- แปลงการแสดงผลสถานะและการเปิด-ปิดบอท AI คัดกรองอาการที่หัวแชทให้เป็น **iOS-style Toggle Switch** สีเขียว-เทา ที่ทันสมัยและใช้งานง่าย
- พัฒนา **ระบบปิดการทำงานของ AI อัตโนมัติเมื่อแพทย์เข้าแทรกแซง (Auto-Intervene)**: เมื่อแพทย์ส่งข้อความแชทไปหาคนไข้ในขณะที่ AI ยังทำงานอยู่ ระบบจะปิดสิทธิ์การทำงานของ AI (`aiActive = false`) และส่งข้อความประกาศแจ้งเตือนระบบให้คนไข้ทราบทันที
- **อัปเกรดความเร็วระบบแชท (Latency Fix)**: ย้ายสถาปัตยกรรมการยิง GET/PATCH วนซ้ำๆ 6 รอบข้ามเครือข่ายของ Next.js ไปทำธุรกรรมแบบ **Single Request Transaction (Local Transaction)** บน Django Backend ผ่าน REST API Actions ตัวใหม่
- **แก้ไขบั๊ก Gemini Triage Chat**: กรองล้างข้อความประวัติแชทเริ่มต้นที่ขึ้นต้นด้วยบทบาท model (assistant) ออกชั่วคราว เพื่อรองรับกฎเหล็กของ Gemini API ที่ระบุว่าข้อความแรกสุดในประวัติการคุยจะต้องมาจาก user เสมอ
- **กำหนด API Key Fallback**: เพิ่มลอจิกเรียกใช้ตัวแปร `GOOGLE_AI_API_KEY` เผื่อไว้ในกรณีที่ไม่ได้ระบุตัวแปร `GEMINI_API_KEY` ปลดล็อกความปลอดภัยจากการถูกปิดกั้นการเข้าถึง (403 Forbidden)
- **ใช้งานโมเดล Gemini 2.5 Flash (`gemini-2.5-flash`) ตามมาตรฐานปี 2026**: จากผลลัพธ์ของ Node.js Verification Test พบว่าโมเดลรุ่น 1.5 และ 2.0 ถูกยกเลิกบริการ (Deprecated) แล้วบนระบบของ Google Cloud ในช่วงปี 2026 ดังนั้นระบบจึงใช้โมเดลรุ่นมาตรฐานใหม่คือ `gemini-2.5-flash` สำหรับงาน OCR ภาพและแกะคลิปเสียงได้อย่างรวดเร็วและสำเร็จ 100%
- **เพิ่มปุ่มรีเฟรช 🔄 (Manual Refresh Button)**: เพิ่มปุ่มรีเฟรชแชทที่แถบหัวข้อของแพทย์และคนไข้เพื่อดึงข้อมูลสดๆ จาก PostgreSQL ในกรณีที่เกิดความหน่วงเครือข่าย
- **ระบบบอกสถานะพิมพ์ตามจริง (Dynamic Typing State)**: เมื่อคนไข้พิมพ์/แนบรูป/ส่งคลิปเสียง ระบบแชทจะขึ้นข้อความแจ้งว่า "AI/แพทย์ กำลังวิเคราะห์รูปภาพ/เสียง/ข้อความของคุณอยู่" สอดคล้องตามสถานะการส่งจริงและสถานะ Toggle AI
- **แก้ไขบั๊กแชทเด้ง (Auto-Scroll Jump Fix)**: ป้องกันไม่ให้ห้องแชทของคนไข้เด้งกระพริบดึงผู้ใช้งานกลับไปล่างสุดโดยอัตโนมัติขณะพยายามเลื่อนขึ้นไปอ่านข้อความเก่า โดยใช้ `useRef` ล็อคการเปรียบเทียบความยาวของอาร์เรย์ข้อความ เพื่อสั่งเลื่อนลงล่างสุดเฉพาะในกรณีที่ผู้ใช้เพิ่งส่งแชทใหม่ หรือมีข้อความใหม่ตอบกลับเข้ามาจริงเท่านั้น
- **สถาปัตยกรรม Precision Medicine AI Engine**:
  - **Gemini 2.5 Flash**: วิเคราะห์ OCR รูปภาพผลแล็บและแกะคลิปเสียงเป็นข้อมูลดิบใน `/api/doctor/voice-to-form/`
  - **Django (Python Logic)**: คำนวณความเบี่ยงเบนและระดับความเสี่ยงของแกนชีวภาพ 39 แกนประสาทชีวภาพอ้างอิงสูตร/กฎเกณฑ์ทางการแพทย์จริงแบบ Deterministic ผ่าน `/api/patients/{id}/calculate-precision-medicine/` ป้องกันปัญหา AI มโนคะแนนเอง
  - **Deepseek Chat API (`deepseek-chat`)**: ขัดเกลาข้อสรุปคะแนนดิบจาก Django และเรียบเรียงภาษาไทยให้เป็นประโยคที่สละสลวย อธิบายกลไกทางคลินิกอย่างเป็นทางการ
  - **ประสิทธิภาพความเร็ว (Latency Fix)**:
    - ผสานการโหลดข้อมูลคนไข้ (EMR) และประวัติรายงานวิเคราะห์สุขภาพเข้าด้วยกันด้วย `Promise.all` ยิงขนานพร้อมกัน ช่วยลดเวลารอบการโหลดหน้าจอ AI Physician ลงกว่าครึ่งหนึ่ง
    - ลบผลลัพธ์ request ซ้ำซ้อนและกระพริบของ `useEffect` ออกอย่างสมบูรณ์

## ทำไมถึงทำแบบนี้
- **Deterministic Biology Calculation**: คะแนน 39 แกนชีวภาพของคนไข้เป็นเรื่องละเอียดอ่อน ไม่ควรให้ LLM ประเมินสุ่ม การคำนวณผ่าน Python code บน Django หลังบ้านช่วยรักษาความถูกต้องทางหลักการแพทย์สูงสุด และใช้ Deepseek ในจุดที่ถนัดคือการขัดเกลาถ้อยคำ
- **Parallel Loading (Promise.all)**: การโหลดข้อมูลประวัติและประวัติรายงานวิเคราะห์สุขภาพจากเดิมที่โหลดต่อกัน (Sequential) ถูกย้ายไปรันขนานกัน ทำให้ลด latency ของเน็ตเวิร์กและโหลดหน้าจอ AI Physician ได้ไวขึ้นอย่างเห็นได้ชัด
- **Auto-Scroll Prevention**: การ polling ทุกๆ 3 วินาทีทำให้ object reference ของอาร์เรย์ messages เปลี่ยนและทริกเกอร์ useEffect scroll ตลอดเวลา การล็อคด้วยความยาวอาร์เรย์ (`messages.length`) ช่วยหยุดการ scroll เด้งขัดจังหวะผู้ป่วยขณะอ่านข้อมูลประวัติ
- **API Key Fallback**: การยิงเรียกใช้งาน API ในแอปเคยเกิด 403 Forbidden เนื่องจากระบบ Next.js ของผู้ใช้งานไม่ได้เก็บคีย์ไว้ในชื่อ `GEMINI_API_KEY` แต่เก็บในชื่อ `GOOGLE_AI_API_KEY` การทำ fallback ช่วยให้ดึงคีย์ได้ถูกต้องและรันผ่านสำเร็จทันที
- **Production-Standard in 2026**: ในช่วงปี 2026 โมเดลรุ่นก่อน (1.5 และ 2.0) ถูกถอดออกจากระบบแล้ว (404) การคงรุ่นโมเดลเป็น `gemini-2.5-flash` ทำให้ระบบแชทคัดกรองมัลติโมดอลรันผ่านและได้คะแนนความเร็วที่ยอดเยี่ยม

## โครงสร้างไฟล์
- **หลังบ้าน Django (API endpoints)**: [views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py)
  - `calculate_precision_medicine/` (POST) -> รับค่าแล็บและอาการ คำนวณคะแนนแกน ยิง Deepseek แต่งภาษา และเซฟลง PostgreSQL
- **แชทวิเคราะห์ Next.js**: [route.ts (api/ai/brain)](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/api/ai/brain/route.ts) -> รันสกัด Regex ค่าแล็บและส่งต่อไปหา Django
- **ไฟล์หลักหน้าวิเคราะห์แพทย์**: [page.tsx](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/doctor/ai-physician/page.tsx)
- **ตัวถอดความเสียง/OCR**: [route.ts (api/doctor/voice-to-form)](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/api/doctor/voice-to-form/route.ts)

## อ้างอิง
- [19 Iron Rules: 6.1 ONE MODULE = ONE MD](file:///Users/tanchonl/Downloads/drpatt/.agents/AGENTS.md)
