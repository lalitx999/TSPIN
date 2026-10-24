# EP6 — Safety and Omics Utility Gate

- Existing safety ledger remains intervention-specific; it does not use deprecated global `CONTRAINDICATED`.
- Multi-omics requires `omics_clinical_question`, `omics_actionability_plan` and explicit `omics_informed_consent: true`.
- If any requirement is absent, the immutable ledger records `BLOCKED_NO_CLINICAL_UTILITY` and the multi-omics PDF route returns `409`.
- Patient PDF route returns `403` unless the same analysis run has a `PATIENT_RELEASED` audit transition.
