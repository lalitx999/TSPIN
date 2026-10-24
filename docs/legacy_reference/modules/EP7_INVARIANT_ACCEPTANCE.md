# EP7 — Final Core Invariant Acceptance

## Invariants ที่ต้องผ่าน

1. Identity/source ownership conflict ไม่สร้าง biological record หรือ analysis snapshot
2. ทุก renderer ใช้ immutable `AnalysisRecord` ไม่ recompute จากข้อมูลปัจจุบัน
3. Axis/domain/step code-name mapping ต้องตรง canonical registry
4. HYPOTHESIS axis ไม่มี numeric score และไม่เข้า priority/module matching
5. Patient artifact ต้องมี `PATIENT_RELEASED` audit transition
6. Multi-omics ต้องผ่าน Clinical Utility Gate
7. AnalysisRecord แก้ไขย้อนหลังผ่าน `.save()` ไม่ได้

## รันก่อน push/deploy (R0 และ QA โดยผู้ดูแล)

```bash
cd backend
python manage.py migrate patients 0017
python manage.py migrate patients 0018
python manage.py migrate patients 0019
python manage.py migrate patients 0020
python manage.py test patients.tests.IdentityConflictGateTests patients.tests.GenerateClinicalPdfGatingTests patients.tests.AnalysisRecordProvenanceTests patients.tests.OmicsUtilityGateTests patients.tests.ScoringContractGateTests patients.tests.ValidateAnalysisRecordTests patients.tests.TspiEngineNineStepsTests
```

## สิ่งที่ไม่ควรอ้างว่าอนุมัติแล้ว

Scoring contract ทางคลินิก (rule owner, threshold, approval signature) ยังต้องได้รับการอนุมัติจากแพทย์จริง ระบบจึงเก็บ rule/version/evidence provenance และ gate อื่นครบก่อน แต่ไม่สร้างคำว่า “approved scoring rule” ขึ้นเอง
