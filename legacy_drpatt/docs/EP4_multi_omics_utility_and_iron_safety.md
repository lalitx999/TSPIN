# EP4 — Multi-Omics Clinical Utility Gate & Iron Safety Protocol (30 Sep 2026)

## ทำอะไร
- บังคับใช้ **Clinical Utility Gate 12 ข้อ** สำหรับการส่งตรวจขั้นสูง (WES, Epigenomics, Microbiome, Proteomics): หากตอบคำถามเรื่อง `will_change_management == "LOW"` ระบบจะปรับสถานะการตรวจเป็น `DEFER` (ชะลอการตรวจ) ทันที
- บังคับปรัชญา **Omics เป็น Resolution Layer ไม่ใช่ Prerequisite**: สภาพทางคลินิก (ประวัติ, การตรวจร่างกาย, ผลแล็บพื้นฐาน) เป็น First-class evidence เท่าเทียมกัน Omics ทำหน้าที่เพิ่มความละเอียดความแม่นยำ ไม่ใช่เงื่อนไขบังคับในการปลดล็อก 3 Keys หรือ 9 Steps
- แยกระดับการตรวจด้วย **TEST_EVIDENCE_TIERS**:
  - `STANDARD_CLINICAL`: CBC, Chemistry, FBS, HbA1c, Lipid, LFT, RFT
  - `CLINICALLY_ACTIONABLE_ADVANCED`: Ferritin, TIBC, Transferrin Sat, Hb Typing, Anti-TPO
  - `OPTIONAL_ADVANCED`: WES, Epigenomics, Proteomics, Metabolomics
  - `RESEARCH_ONLY`: Experimental assays ที่ยังไม่มี Cutoff ทางคลินิก
- บังคับใช้ **Iron Safety Hold Protocol**: เมื่อพบ Mentzer Index < 13 (สงสัยแฝงธาลัสซีเมีย) แต่ยังไม่มีผล Ferritin ยืนยัน ระบบจะระบุสถานะเป็น `HOLD_PENDING_CONFIRMATION` เฉพาะสารเสริมอาหารธาตุเหล็ก (`IRON_SUPPLEMENTATION`) เท่านั้น ห้ามระบุเป็นข้อห้ามเด็ดขาด (Absolute Contraindication) สำหรับอาหารธรรมชาติทั่วไป

## ทำไมถึงทำแบบนี้
- เอกสาร P1-13 ถึง P1-16 ระบุว่าการส่งตรวจ Omics ราคาแพงต้องมีวัตถุประสงค์ทางคลินิกที่ชัดเจน (Clinical Question Driven) และการกักกันความปลอดภัยธาตุเหล็กต้องเจาะจงเฉพาะตัวสารเสริม ไม่กระทบอาหารตามธรรมชาติ

## โครงสร้างไฟล์ที่แก้ไข
| ไฟล์ | การเปลี่ยนแปลง |
|------|----------------|
| `backend/patients/core_contracts.py` | บังคับใช้ `clinical_utility()` 12 ข้อ และนิยาม `TEST_EVIDENCE_TIERS` 4 เกรด |
| `backend/patients/tspi_engine.py` | บังคับใช้ `evaluate_omics_utility_gate()` และระบุ `HOLD_PENDING_CONFIRMATION` เฉพาะ `IRON_SUPPLEMENTATION` |
| `backend/patients/tests.py` | เพิ่ม 2 Test Cases (Test Evidence Tiers & Mentzer Iron Hold Protocol) |

## ผลการทดสอบ
- **Ran 66 tests in 1.854s — OK** (ผ่านทั้ง 66 เคส)

## อ้างอิง
- FINAL CORE CORRECTION REQUEST (TSPI Clinical Intelligence Engine) ลงวันที่ 30 Sep 2026
- Section P1-13, P1-14, P1-15, P1-16
