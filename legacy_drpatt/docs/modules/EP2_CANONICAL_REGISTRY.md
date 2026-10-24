# EP2 — Canonical Registry Lock

## Source of truth

`backend/patients/tspi_engine.py` เป็น registry authority เดียวสำหรับ:

- 39 axes (`A1`–`A39`) พร้อมชื่อ canonical
- 12 domains พร้อม code, name, axes และ domain type
- 9 restoration steps พร้อมลำดับและชื่อที่ล็อกไว้

ผลวิเคราะห์จะบันทึก `canonical_registry.version` และสำเนา `canonical_domains` ใน immutable `AnalysisRecord` เพื่อให้ renderer ไม่เดา mapping เอง

## Fail checks

`validate_analysis_record()` ตรวจ invariant เพิ่มเติม:

- `INV-008`: axis key หรือ axis code/name ไม่ตรง registry
- `INV-009`: จำนวน/ลำดับ/ชื่อ restoration step ไม่ตรง registry
- `INV-010`: domain code/name/axis mapping ไม่ตรง canonical 12-domain registry

ledger ที่ invariant ไม่ผ่านมี `is_valid: false`; renderer ใน EP5 จะปฏิเสธ ledger ที่ invalid ก่อนเผยแพร่

## Regression check

```bash
cd backend
python manage.py test patients.tests.ValidateAnalysisRecordTests patients.tests.TspiEngineNineStepsTests
```
