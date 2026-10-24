# ความเชื่อมโยงระหว่างไฟล์ (System Dependency Map)

แผนผังความเชื่อมโยงนี้อธิบายโครงสร้างการพึ่งพากันและการนำเข้าโค้ด (Imports) ภายในระบบ **Dr. Pat (TSPI)** ทั้งฝั่ง Backend และ Frontend เพื่อช่วยให้นักพัฒนาเห็นภาพการทำงานก่อนปรับปรุงโค้ด:

---

## 1. ผังการนำเข้าโค้ดฝั่งหลังบ้าน (Backend Python Import Dependency Map)

```
[config/urls.py]
      │
      ├─► (include) [accounts/urls.py] ──► (imports) [accounts/views.py] ──► (imports) [patients/models.py]
      │
      └─► (include) [patients/urls.py]
               │
               ├─► (imports) [patients/views.py]
               │         │
               │         ├─► (imports) [patients/models.py]
               │         └─► (imports) [patients/tspi_engine.py]
               │
               ├─► (imports) [patients/views_ai.py]
               │         │
               │         ├─► (imports) [patients/models.py]
               │         └─► (imports) [patients/tspi_engine.py]
               │
               └─► (imports) [patients/views_line.py]
                         │
                         └─► (imports) [patients/models.py]
```

### รายละเอียดการเรียกไฟล์ (Backend Import Matrix):
1. **[patients/views.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views.py)**:
   * **นำเข้า**: `Patient`, `PatientBiologicalRecord`, `AuditLog`, `ClinicalKnowledge`, `TspiSettings`, `PatientHistory`, `Appointment`, `PdpaConsent`, `AutomationTask` จาก [models.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/models.py)
   * **นำเข้า**: `calculate_tspi_analysis` จาก [tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py) เพื่อใช้ประเมินคะแนนแกนชีวภาพ
2. **[patients/views_ai.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_ai.py)**:
   * **นำเข้า**: `ClinicalKnowledgeSegment`, `Patient`, `PatientBiologicalRecord`, `Appointment` จาก [models.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/models.py)
   * **นำเข้า**: `markdown_to_html` (ฟังก์ชันท้องถิ่น) เพื่อแปลงบทวิเคราะห์ดิบเป็นหน้าเว็บสำหรับพิมพ์ PDF
3. **[patients/views_line.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/views_line.py)**:
   * **นำเข้า**: `Patient`, `PatientBiologicalRecord`, `LineLinkingToken`, `LineChat`, `AuditLog` จาก [models.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/models.py)
4. **[patients/tspi_engine.py](file:///Users/tanchonl/Downloads/drpatt/backend/patients/tspi_engine.py)**:
   * **อ่านข้อมูลดิบ (I/O)**: `/Users/tanchonl/Downloads/drpatt/data/last_dta/TSPI Modules Master Data + Training_Pairs.json` (ฐานข้อมูลยาสมุนไพรและโครงสร้างแกน)

---

## 2. ผังความเชื่อมโยงของระบบหน้าบ้าน (Frontend Next.js Dependency Map)

```
[Doctor Dashboard UI Component]
      │
      ▼
[src/app/doctor/ai-physician/page.tsx]
      │
      ├─► (HTTP Fetch) [src/app/api/ai/report/route.ts] (Streaming API Route)
      │                     │
      │                     ├─► (Genkit / OpenAI Call) [Deepseek/Groq APIs]
      │                     └─► (HTTP Fetch) [backend/patients/views.py] (calculate-precision-medicine)
      │
      └─► (HTTP Fetch) [src/app/api/doctor/lab-text-analyzer/route.ts] (OCR Extract)
                            │
                            └─► (Gemini Call) [GoogleGenerativeAI API]
```

### รายละเอียดการเชื่อมโยงส่วนงานหน้าบ้าน (Frontend Import Matrix):
1. **[precision-medicine-flow.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/lib/precision-medicine-flow.ts)**:
   * **นำเข้า**: `precisionEngine` จาก [tspi-engine.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/lib/tspi-engine.ts) เพื่อเป็นระบบสำรองดึงข้อมูล
   * **นำเข้า**: `ai` (Genkit Config) จาก [genkit.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/lib/genkit.ts)
   * **นำเข้า**: `axesData` จาก `src/data/39_last_x.json`
2. **[tspi-engine.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/lib/tspi-engine.ts)**:
   * **นำเข้า**: `axesData` จาก `src/data/39_last_x.json` (รายละเอียด 39 แกน)
   * **นำเข้า**: `modulesDb` จาก `src/data/200_module_tspi.json` (รายละเอียดโมเดลสมุนไพร)
   * **นำเข้า**: `labMapping` จาก `src/data/lab_mapping.json` (จับคู่แล็บดิบกับพหุมิติ)
   * **นำเข้า**: `clinicalRules` จาก `src/data/clinical_rules.json` (สูตรเงื่อนไขตรวจสอบ)
3. **[api/ai/report/route.ts](file:///Users/tanchonl/Downloads/drpatt/frontend/src/app/api/ai/report/route.ts)**:
   * **ประสานงาน**: ยิงเรียก REST Call ไปฝั่งหลังบ้านที่พอร์ต `http://localhost:8000/api/patients/{id}/calculate-precision-medicine/` เพื่อประเมินประวัติต่อเนื่อง
