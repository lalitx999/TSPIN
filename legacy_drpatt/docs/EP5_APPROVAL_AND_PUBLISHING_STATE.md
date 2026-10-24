# Module: EP5 — การอนุมัติและสิทธิ์การเผยแพร่รายงาน (Report Release Workflow)

## ทำอะไร
พัฒนาระบบควบคุมลำดับสถานะการรับรองรายงานทางการแพทย์ (State Machine) และกำหนดสิทธิ์ในสกัดและเปิดดูรายงานอย่างมีธรรมาภิบาล:
1. **4 Release States:** `AI_DRAFT` → `PHYSICIAN_REVIEWED` → `PHYSICIAN_APPROVED` → `PATIENT_RELEASED`
2. **แยกหน้าที่ธุรการและแพทย์:** เจ้าหน้าที่ธุรการ (Office Staff) สามารถทำการตรวจ Administrative QA ได้ แต่ไม่สามารถเปลี่ยนสถานะเป็น `PHYSICIAN_APPROVED` หรือใช้คำว่า "Certified by Physician" แทนแพทย์ผู้รักษาได้
3. **การเปลี่ยนเนื้อหาต้องทบทวนใหม่:** หากมีการอัปเดตผลแล็บหรือประวัติสรีรวิทยา ระบบจะสร้าง `AnalysisRecord` ใหม่ และรีเซ็ตสถานะกลับเป็น `AI_DRAFT`
4. **Patient Release Gate:** คนไข้สามารถเข้าถึงและดาวน์โหลด PDF/View รายงานได้เฉพาะฉบับที่มีสถานะเป็น `PATIENT_RELEASED` เท่านั้น

---

## ทำไมถึงทำแบบนี้
1. **ความปลอดภัยทางกฎหมายและจริยธรรมแพทย์:** ป้องกันรายงานที่เป็นเพียงฉบับร่างของ AI (AI Draft) รั่วไหลไปถึงคนไข้โดยยังไม่ผ่านการอนุมัติจากแพทย์ผู้รับผิดชอบ
2. **Audit Trail 100%:** ทุกการเปลี่ยนสถานะจะบันทึกผู้ดำเนินการ (`acted_by`) เวลา (`created_at`) และหมายเหตุไว้ในโมเดล [AnalysisReportRelease](file:///Users/tanchonl/Downloads/drpatt/backend/patients/models.py#L203)

---

## โครงสร้างไฟล์
- `backend/patients/models.py`: [AnalysisReportRelease](file:///Users/tanchonl/Downloads/drpatt/backend/patients/models.py#L203)
- `backend/patients/views_ai.py`: Endpoint สำหรับจัดการการอนุมัติและสิทธิ์ดาวน์โหลด PDF
- `backend/patients/tests.py`: `ReportApprovalStateTests`

---

## จุดที่ต้องระวัง
- ห้ามแสดงคำว่า "แพทย์อนุมัติแล้ว" บนหน้าปกหรือส่วนหัวของรายงาน หากสถานะยังไม่ได้เป็น `PHYSICIAN_APPROVED`
- รายงานฉบับคนไข้ (Patient Edition) จะเปิดให้ดาวน์โหลดได้เมื่อแพทย์กด Release เท่านั้น

---

## อ้างอิง
- เอกสารเกณฑ์ตรวจรับ EP5 (รอบแก้ 22.09.2026)
- [models.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/models.py)
