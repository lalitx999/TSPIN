# Module: EP4 Role-Based Permission Matrix & Prompt Governance

## ทำอะไร
- แยกสิทธิ์การใช้งานระหว่าง Patient AI และ Physician AI อย่างเด็ดขาด
- Patient AI: อนุญาตเฉพาะการให้ความรู้ (Education), อธิบายผลลัพธ์ที่อนุมัติแล้ว, แนะนำความปลอดภัย ห้ามวินิจฉัย สั่งยา หรือสรุปข้อสรุปคลินิกโดยไม่มีการอนุมัติ
- Physician AI: อนุญาตให้แสดง HYPOTHESIS หรือการวิเคราะห์สนับสนุนได้ แต่ต้องติดป้ายสถานะชัดเจนว่าต้องผ่านการตรวจทานจากแพทย์
- บังคับใช้ Report Approval State Transition (`AI_DRAFT` → `PHYSICIAN_REVIEWED` → `PHYSICIAN_APPROVED` → `PATIENT_RELEASED`)
- ลบข้อความที่แอบอ้างว่า "แพทย์อนุมัติแล้ว" ออกจากรายงานที่อยู่ในสถานะ `AI_DRAFT`

## ทำไมถึงทำแบบนี้
- เพื่อทำตาม Directive ข้อ 4, 5, 11, 15, 17 ในจดหมายควบคุมขอบเขต AI และสถาปัตยกรรมป้องกัน Hallucination
- ป้องกันไม่ให้ผู้ป่วยได้รับข้อความที่เข้าใจผิดว่าเป็นคำสั่งแพทย์ หรือรายงานที่ยังไม่ผ่านการอนุมัติหลุดไปถึงมือผู้ป่วย

## โครงสร้างไฟล์
- `backend/patients/models.py`: โมเดล `AnalysisReportRelease` ควบคุมสถานะ Release State
- `backend/patients/views_ai.py`: ฟังก์ชัน `transition_report_release()` จำกัดสิทธิ์เฉพาะแพทย์ และ `generate_report_pdf_view()`
- `backend/patients/output_validator.py`: ด่านเปลี่ยนคำพูดแอบอ้างอนุมัติเป็นคำว่า "ร่างแผนดูแลสุขภาพ..."

## จุดที่ต้องระวัง
- รายงานฉบับผู้ป่วย (Patient Edition) จะไม่สามารถดึงข้อมูลได้เลย (HTTP 403 Forbidden) ตราบใดที่สภาวะยังไม่อยู่ในสถานะ `PATIENT_RELEASED`
- การเปลี่ยนสถานะเป็น `PHYSICIAN_APPROVED` ต้องระบุ `physician_id` และ timestamp การอนุมัติจริงเท่านั้น

## อ้างอิง
- Directive 4, 5, 11, 15, 17 (AI Scope Control Architecture Oct 2026)
- TSPI Report Approval State Machine (30 Sep 2026)
