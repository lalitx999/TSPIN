# EP5 — Report Release State

รายงานแต่ละ edition ของ immutable `AnalysisRecord` มี audit trail แยกใน `AnalysisReportRelease`:

`AI_DRAFT → PHYSICIAN_REVIEWED → PHYSICIAN_APPROVED → PATIENT_RELEASED`

ใช้ `POST /api/ai/report-release-transition/` โดย clinical staff เท่านั้น และต้องส่ง `analysis_record_id`, `edition` (`PHYSICIAN`, `PATIENT`, `MULTI_OMICS`) กับ `target_state` ตามลำดับถัดไปเท่านั้น

Migration R0 ใหม่: `0018_analysis_report_release.py` ไม่มีการลบข้อมูลเดิม
