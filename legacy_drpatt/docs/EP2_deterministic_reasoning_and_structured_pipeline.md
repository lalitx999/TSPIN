# Module: EP2 Deterministic Reasoning Decoupling & Structured-First Pipeline

## ทำอะไร
- ถอด Generative AI (LLM) ออกจากการเป็น Clinical Reasoning Engine หลัก 100%
- บังคับใช้ 8-Step Enforced Pipeline (Raw Input → Extraction → Schema Validation → Safety Gate → TSPI Deterministic Engine → Approved Retrieval → Structured Result → Constrained Renderer)
- บังคับใช้หลักการ Deterministic Code: Same Input + Same Registry Version + Same Rule Version = Same Clinical Result
- บัญชีบทบาทหลักฐานทางคลินิก `MARKER_AXIS_RELATIONS` (`DIRECT_SCORING`, `SUPPORTING`, `CONFOUNDED`, `NON_SCORING`)
- ตัด System Prompt / Role leakage ออกจากข้อความเรียบเรียง (`detect_and_strip_prompt_leakage`)

## ทำไมถึงทำแบบนี้
- เพื่อทำตาม Directive ข้อ 1, 2, 8, 14 ในจดหมายควบคุมขอบเขต AI และสถาปัตยกรรมป้องกัน Hallucination
- ป้องกันไม่ให้ LLM ใช้ความเห็นส่วนตัวประเมินคะแนน Severity, Confidence, หรือ Ranking ซึ่งอาจก่อให้เกิดความเสี่ยงสูงทางคลินิก

## โครงสร้างไฟล์
- `backend/patients/tspi_engine.py`: ฟังก์ชัน `calculate_tspi_analysis()`, `MARKER_AXIS_RELATIONS`, `detect_and_strip_prompt_leakage()`
- `backend/patients/tests.py`: ชุดทดสอบ `ReportConsistencyTests` และ `TspiEngineNineStepsTests`

## จุดที่ต้องระวัง
- LLM ทำหน้าที่เฉพาะสกัดภาษาขาเข้า และเรียบเรียงภาษาขาออก ห้ามคำนวณตัวเลขคะแนนเองเด็ดขาด
- ทุกรายงานต้องอ่านผลลัพธ์จาก `AnalysisRecord.ledger` ที่สร้างขึ้นจาก Deterministic Engine เท่านั้น

## อ้างอิง
- Directive 1, 2, 8, 14 (AI Scope Control Architecture Oct 2026)
- TSPI Master Canonical Registry (30 Sep 2026)
