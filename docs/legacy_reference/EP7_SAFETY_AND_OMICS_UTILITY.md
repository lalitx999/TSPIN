# Module: EP7 — Safety Protocols และ Omics Clinical Utility Gate

## ทำอะไร
พัฒนาระบบความปลอดภัยทางการแพทย์ (Clinical Safety) และการควบคุมการแนะนำการตรวจ Omics:
1. **แยก Critical Value จาก TSPI Severity:** แยกผลแล็บวิกฤต (`LAB_CRITICAL_VALUE`) ออกจากระดับความรุนแรงของแกน TSPI (`TSPI_SEVERITY_BAND`)
2. **Iron Safety HOLD Protocol:** ปรับสถานะคำแนะนำการเสริมธาตุเหล็กเป็น `HOLD_PENDING_CONFIRMATION` พร้อมระบุรายการตรวจยืนยันที่ต้องสั่งเพิ่ม (Ferritin, TIBC, Transferrin Saturation, Hb Typing) ป้องกันการสั่งเสริมธาตุเหล็กสุ่มสี่สุ่มห้าในเคสที่เป็น Thalassemia trait
3. **12-Field Clinical Utility Gate:** การแนะนำให้ตรวจ Omics ต้องผ่านการประเมินความจำเป็น 12 ข้อ หากผลลัพธ์ไม่ช่วยเปลี่ยนแนวทางการรักษา (`will_change_management = LOW`) ให้กำหนดสถานะเป็น `DEFER`

---

## ทำไมถึงทำแบบนี้
1. **Medical Safety First:** ธาตุเหล็กไม่ใช่ยาบำรุงที่เสริมได้โดยไม่ตรวจสถานะธาตุเหล็กและชนิดฮีโมโกลบิน
2. **Value-Based Precision Medicine:** การตรวจ Omics ที่มีค่าใช้จ่ายสูง ต้องมีคำถามทางคลินิกและแผนการรักษาที่ชัดเจนรองรับ ไม่ใช่แนะนำเพราะขาดข้อมูล

---

## โครงสร้างไฟล์
- `backend/patients/core_contracts.py`: [clinical_utility()](file:///Users/tanchonl/Downloads/drpatt/backend/patients/core_contracts.py#L11)
- `backend/patients/tspi_engine.py`: [evaluate_omics_utility_gate()](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py#L378)
- `backend/patients/tests.py`: `OmicsUtilityGate12FieldsTests`

---

## อ้างอิง
- เอกสารเกณฑ์ตรวจรับ EP7 (รอบแก้ 22.09.2026)
