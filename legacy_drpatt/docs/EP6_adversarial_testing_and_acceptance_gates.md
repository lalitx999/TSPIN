# Module: EP6 Adversarial Testing Suite & Acceptance Gates

## ทำอะไร
- บังคับใช้ Adversarial Test Suite ครอบคลุมการโจมตีและการหลอนทุกรูปแบบ (Incomplete data, contradictory data, prompt injection, nonexistent axis, fabricated citations, safety override)
- บังคับใช้ Production Release Acceptance Gate: สั่ง BLOCK Release 100% หากมีข้อผิดพลาดระดับ P0 ล้มเหลวแม้แต่เคสเดียว
- ทดสอบความสม่ำเสมอ Same-Input Reproducibility ของ Deterministic Engine (100% Deterministic)
- ตรวจสอบความถูกต้องของรายงานทั้ง 3 Editions (Physician, Patient, Multi-Omics) ว่าอ้างอิงจาก AnalysisRecord ID เดียวกัน

## ทำไมถึงทำแบบนี้
- เพื่อทำตาม Directive ข้อ 21, 22, 23, 24, 25 ในจดหมายควบคุมขอบเขต AI และสถาปัตยกรรมป้องกัน Hallucination
- เป็นหลักประกันสุดท้ายก่อนนำระบบเข้าสู่ Physician Shadow Pilot และ Production Release ว่าสถาปัตยกรรมป้องกันการหลอนทำงานได้จริง 100%

## โครงสร้างไฟล์
- `backend/patients/tests.py`: 66 Unit Tests
- `backend/patients/tests_e2e_golden.py`: 12 End-to-End Golden Report Artifact Tests (E2E-001..E2E-012)
- `backend/patients/tests_anti_hallucination.py`: 7 Anti-Hallucination Directives Tests
- `docs/E2E_golden_report_test_results.md`: เอกสารสรุปผลการทดสอบทั้งหมด 85 เคส

## จุดที่ต้องระวัง
- ห้ามถือว่าระบบ "พร้อมใช้งาน" ตราบใดที่ชุดทดสอบ 85 เคสนี้ยังไม่ผ่าน 100%
- ทุกครั้งที่มีการอัปเดต Rule หรือ Registry ใหม่ ต้องรัน Regression Test ชุดนี้ซ้ำเสมอ

## อ้างอิง
- Directive 21, 22, 23, 24, 25 (AI Scope Control Architecture Oct 2026)
- TSPI Definition of Done & Production Gate Policy (30 Sep 2026)
