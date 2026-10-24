# ลำดับการไหลของข้อมูลในระบบ (Data Flow Diagrams & Workflows)

เอกสารฉบับนี้สรุปกระแสการไหลของข้อมูล (Data Flow) ใน 2 ฟีเจอร์หลักของระบบ Dr. Pat:
1. **ระบบวิเคราะห์แล็บ สแกนเอกสาร และออกรายงานผู้ป่วยพหุมิติ (Lab OCR & Report Flow)**
2. **ระบบแชทบอทซักประวัติอัตโนมัติ (LINE OA AI Auto-Intake & EMR Sync Flow)**

---

## 1. ระบบวิเคราะห์แล็บ สแกนเอกสาร และออกรายงานผู้ป่วย (Lab OCR & Report Flow)

กระบวนการนี้นำข้อความผลเลือดและข้อมูลอาการของคนไข้ไปสู่รายงานทางการแพทย์ฉบับเต็มและดาวน์โหลดไฟล์ PDF:

```
[1. Doctor Screen] ─► (Lab image/Text) ─► [2. Next.js API (lab-text-analyzer)]
       ▲                                                 │ (Gemini 2.5 JSON parse)
       │ (Returns Clean Lab JSON)                        ▼
[4. EMR Dashboard] ◄───────────────────────── [3. Next.js Client State]
       │
       ▼ (Click "Generate Report")
[5. Next.js API (report/route.ts)] ──► [6. Django REST (calculate-precision-medicine)]
       │                                                 │
       │ ◄── (Returns Scores & Dosing NSS/SPS) ◄─────────▼ (tspi_engine.py calculation)
       ▼
[7. Deepseek / Groq LLM] ──► (AI Streaming Text Chapters) ──► [8. Saved in PostgreSQL]
       │
       ▼ (Click "Download PDF")
[9. Django views_ai.py (generate_report_pdf_view)] ──► [10. WeasyPrint PDF Engine]
       │
       └──────────────────────── (Download Stream PDF) ──────────► [11. Doctor Browser]
```

### ขั้นตอนการไหลของข้อมูล:
1. **Lab Data Ingestion (การแปลงข้อความผลแล็บ)**: แพทย์วางข้อความดิบหรือรูปผลแล็บที่ด่าน [lab-ocr](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/doctor/lab-ocr) -> ส่งไปที่ API `lab-text-analyzer` -> ใช้โมเดล **Gemini 2.5 Flash** สกัดค่าแล็บออกมาเป็น JSON พร้อมประเมินค่าความเสี่ยง -> ส่งกลับมาพรีวิวบนแดชบอร์ดแพทย์
2. **Precision Scoring (การคำนวณแกนชีวภาพหลังบ้าน)**: เมื่อแพทย์ยืนยันผลแล็บและกดคำนวณ -> หน้าบ้านจะส่งคำขอไปยังหลังบ้าน Django (`calculate_precision_medicine` ใน [views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py)) -> เรียกใช้ [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py) ดึงค่าน้ำหนักคงที่และหาค่า NSS, SPS พร้อมจับคู่สูตรยา TSPI -> อัปเดตตาราง `PatientBiologicalRecord` ใน PostgreSQL และส่งคืนค่าความรุนแรงกลับหน้าบ้าน
3. **AI Writing & RAG (การเรียบเรียงเอกสารชีวภาพ)**: Next.js API `report/route.ts` รับผลคะแนนแกนชีวภาพ -> กรองวิจัยเด่นตามหัวข้อจากคลัง RAG -> ส่งให้ Deepseek เขียนเนื้อหาผลการประเมินทีละบท -> สตรีมข้อมูลผลลัพธ์แบบทีละบรรทัดแสดงให้แพทย์ตรวจทาน และเก็บเนื้อหาร่างลงฟิลด์ `extra_data` ของตารางผู้ป่วย
4. **PDF Generation (การเรนเดอร์ PDF)**: เมื่อกดดาวน์โหลด -> ลิงก์ตรงจะเรียกไปที่ `generate_report_pdf_view` ใน [views_ai.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_ai.py) -> นำบทความที่ AI สตรีมจัดเก็บเสร็จแทนค่าลงเทมเพลต [precision_medicine_report_v4.html](file:///Users/tanchonl/Downloads/drpatt/backend/patients/templates/patients/precision_medicine_report_v4.html) -> `WeasyPrint` แปลงเป็นเอกสาร PDF สำหรับส่งพิมพ์ให้คนไข้

---

## 2. ระบบแชทบอทซักประวัติอัตโนมัติ (LINE OA AI Auto-Intake & EMR Sync Flow)

กระบวนการนี้เชื่อมโยงคนไข้ตั้งแต่สแกนเปิดแชท บอทคุยบันทึกอาการ จนถึงการจัดกลุ่มลง EMR:

```
[1. User on LINE OA] ──► (Sends "ปวดข้อ เหนื่อยง่าย") ──► [2. Django LINE Webhook]
                                                                  │
                                            ┌─────────────────────┴─────────────────────┐
                                            ▼ (Linked?)                                 ▼ (Unlinked?)
                                    [3. YES: AI Intake Chat]                    [3.1 NO: Link Account]
                                            │ (Call Groq Llama 3)                       │ (Gen temporary token)
                                            ▼                                           ▼
                                    [4. Programmatic AI QC]                     [3.2 Send Flex Message]
                                            │ (Check findings & duration)               │ (Redirects to App Login)
                                            ▼                                           ▼
                                    [5. Save to LineChat]                       [3.3 Link via Phone]
                                            │                                           │ (Delete token, save ID)
                                            ▼                                           ▼
                                    [6. Update Patient EMR] ◄───────────────────────────┘
                                     - chief_complaint updated
                                     - PatientBiologicalRecord created
```

### ขั้นตอนการไหลของข้อมูล:
1. **LINE Message Delivery (สัญญาณ Webhook เข้า)**: คนไข้ส่งข้อความทักหาบอท LINE OA -> สัญญาณ Webhook ส่งเข้าที่ Endpoint `line_webhook` ใน [views_line.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_line.py)
2. **Identity Evaluation (ประเมินตัวตนคนไข้)**:
   * **ยังไม่ได้ผูกบัญชี (Unlinked)**: ระบบจะสร้าง temporary token แล้วยิง Flex Message ลิงก์ URL `http://localhost:3000/patient/login?t=token` กลับไป เพื่อให้ผู้ใช้เข้าสู่ระบบยืนยันตัวตนด้วยหมายเลขโทรศัพท์ เมื่อผ่านแล้ว บัญชี LINE User ID จะถูกผูกกับ EMR ถาวร
   * **ผูกบัญชีเรียบร้อย (Linked)**: เข้าสู่กระบวนการซักประวัติตามปกติ
3. **AI Intake & Safety Gate (ซักประวัติและดักความปลอดภัย)**: ระบบดึงประวัติการคุย 10 ข้อความล่าสุดจากตาราง `LineChat` -> ส่งให้ Groq Llama 3.3 ประมวลผลพร้อมตอบคำถามสุภาพและสรุปสถานะการป่วยเป็น JSON บล็อกท้ายแชท -> นำ JSON มาผ่าน **Programmatic QC Checklist** (เช็คว่าบอทถามระยะเวลากับอาการครบถ้วนหรือไม่ก่อนกดบันทึก 완료) -> ตอบกลับคนไข้ผ่าน LINE OA
4. **PostgreSQL Database Sync (อัปเดตข้อมูลอัตโนมัติ)**: เมื่อ AI ประเมินสถานะแชทเป็น `completed` -> ดึงค่าประมาณคะแนนความเสี่ยงที่สกัดได้จากแชทบันทึกลงตารางคะแนนแกนชีวภาพ `PatientBiologicalRecord` พร้อมอัปเดตช่องอาการเด่น `chief_complaint` ในตารางคนไข้ทันที
5. **Audit Logging (บันทึกประวัติความโปร่งใส)**: ทุกกระบวนการจะสร้างข้อมูลล็อกบันทึกลงตาราง `AuditLog` เพื่อระบุการจัดการข้อมูลคนไข้ตาม พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล (PDPA)
