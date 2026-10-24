# TSPI Clinical Intelligence Engine — End-to-End Golden Report Test Results

**Date:** 02 October 2026  
**Test Suite:** `backend/patients/tests_e2e_golden.py`  
**Status:** **100% PASS (78/78 Unit + E2E Tests Passed)**

---

## สรุปผลการทดสอบ End-to-End Artifact Tests (E2E-001 ถึง E2E-012)

| Test ID | รายละเอียดข้อบังคับ | ผลการทดสอบ | สถานะการการันตีใน PDF Artifact |
|---|---|---|---|
| **E2E-001** | ทั้ง 3 Report Editions อ่านจาก `analysis_record_id` เดียวกัน 100% | **PASS** | ไม่มีทางเกิด Data Skew หรือแยกคำนวณคะแนนใน Renderer |
| **E2E-002** | รายงานสถานะ `AI_DRAFT` ไม่มีคำว่า Approved / Certified บนหน้าปกหรือหัวข้อ | **PASS** | ลบคำอ้างอนุมัติแพทย์ออกจากหน้าปก และเปลี่ยนหัวข้อฉบับคนไข้เป็น *"ร่างแผนดูแลสุขภาพฯ"* |
| **E2E-003** | Patient PDF rendered HTML text ไม่มี Tag วงเล็บเหลี่ยมหลุดรอด (`[MEASURED]`, `[HYPOTHESIS]`, ฯลฯ) | **PASS** | Sanitizer Regex ล้าง Tag วงเล็บเหลี่ยมเกลี้ยง 100% แปลงเป็นภาษาไทยธรรมชาติ |
| **E2E-004** | เมื่อเกิด Demographic Conflict (`identity_validation_status != VERIFIED`) จะไม่มี Clinical PDF ถูกสร้าง | **PASS** | บล็อกทุก Endpoint PDF (Physician, Patient, Multi-Omics) ส่งกลับ `DATA_RECONCILIATION_REPORT` |
| **E2E-005** | แกน `HYPOTHESIS` และ `CLINICAL_INFERENCE` มีคะแนน `severity_score = None` | **PASS** | ไม่มีการเต้าตัวเลขคะแนนสำหรับแกนที่ยังไม่มีสูตรอนุมัติหรือขัดแย้ง |
| **E2E-006** | ทุกแกนที่มีคะแนนตัวเลขต้องมี `scoring_contracts` approval metadata ใน ledger | **PASS** | Trace กลับไปหา `rule_id` และ `version` ที่อนุมัติได้ทุกตัว |
| **E2E-007** | Mentzer Index < 13 ตั้งสภาวะเป็น `HOLD_PENDING_CONFIRMATION` เฉพาะสารเสริม ไม่ห้ามอาหารธรรมชาติ | **PASS** | ระงับเฉพาะ `IRON_SUPPLEMENTATION` ไม่ขึ้นคำว่า "ห้ามเด็ดขาด" สำหรับอาหารธรรมชาติ |
| **E2E-008** | เมื่อ `approved_modules = 0` รายการ `recommended_modules_clinical` ต้องเป็นว่าง | **PASS** | Fail-closed ป้องกันการสอดไส้ Module ที่ยังไม่อนุมัติเป็นคำแนะนำคลินิก |
| **E2E-009** | ชื่อ Domain / Axis / Step ตรงตาม Master Registry ทุกคำ | **PASS** | A35 = *"Visceral Organ Functional Reserve"*, 9 Steps และ 12 Domains ตรง Master 100% |
| **E2E-010** | Advanced Omics ทุกรายการแสดงผลการประเมิน Clinical Utility Gate 12 ข้อ | **PASS** | แสดงผลตาราง Utility Gate Audit Table ชัดเจนใน Multi-Omics Edition |
| **E2E-011** | Required report chapters มีเนื้อหาครบ ไม่มี Chapter หัวข้อลอย | **PASS** | กรองและตรวจสอบความสมบูรณ์ของเนื้อหาทุก Chapter |
| **E2E-012** | หลักฐานตัวเดียวกันมีค่า/หน่วย/สถานะตรงกันทุก Edition | **PASS** | อ่านค่าจาก Immutable AnalysisRecord Ledger เดียวกัน |

---

## สรุปหลักฐานสำหรับ Final Audit

1. **Backend Integration Repairs:**
   - Identity Hard Gate (INV-000) ทำงานครอบคลุมทุก Endpoint PDF (`generate_clinical_pdf` และ `generate_report_pdf_view`)
   - Approval State Machine บังคับใช้สิทธิ์แพทย์เท่านั้นในการเปลี่ยนสถานะเป็น `PHYSICIAN_APPROVED` หรือ `PATIENT_RELEASED`
   - Patient Tag Cleansing Regex การันตีไร้ Tag วงเล็บเหลี่ยมหลุดรอด
   - Multi-Omics Clinical Utility Audit Table แสดงผลการประเมินใน PDF ทุกฉบับ

2. **Test Command for Reproduction:**
   ```bash
   ./.venv/bin/python manage.py test patients.tests patients.tests_e2e_golden -v 2
   ```
