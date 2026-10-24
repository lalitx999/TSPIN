import { NextResponse } from 'next/server';
import { GoogleGenerativeAI } from '@google/generative-ai';
import OpenAI from 'openai';
import { AsyncLocalStorage } from 'async_hooks';
import crypto from 'crypto';
import { getAxisName } from '@/lib/axis-definitions';
import networkRegistryData from '@/data/180_network.json';

const reportStreamStorage = new AsyncLocalStorage<{
  enqueueChunk: (chunk: string) => void;
  onChapterStart: (title: string) => void;
  onChapterComplete: (title: string, content: string) => void;
}>();

/**
 * ════════════════════════════════════════════════════════════════
 * 🏥 TSPI Precision Biological Network Intelligence Report™
 *
 * Physician Edition   — 10 บท + Appendix A-E   (25-30 หน้า)
 * Patient Edition     — 10 บท                  (ภาษาเข้าใจง่าย)
 * Multi-Omics Edition — 15 บท                  (สำหรับคนไข้ Omics)
 *
 * Pipeline:
 *   Django calculate-precision-medicine → Axis Scores (Deterministic)
 *   Deepseek Chat (Primary) → Chapter Writing
 *   Groq Llama 3.3 (Auto-Fallback)
 * ════════════════════════════════════════════════════════════════
 */

const CLINICAL_SAFETY_RULES = `
กฎเหล็กความปลอดภัยและการแพทย์ของระบบ TSPI (CRITICAL CLINICAL SAFETY RULES):
1. ONTOLOGY LOCK (ห้ามอ้างอิงแกนชีวภาพสลับความหมายกันเด็ดขาด):
   - AXIS_26 = Stem Cell & Hematopoiesis (การสร้างเม็ดเลือดแดง)
   - AXIS_27 = Glycation / Carbonyl Stress (การเกาะน้ำตาล/ความเครียดคาร์บอนิล)
   - AXIS_8 = Mitochondrial Network (เครือข่ายไมโทคอนเดรีย)
   - AXIS_34 = Neuro–Sleep–Stress–Brain Clearance (ระบบประสาทและการระบายขยะสมอง)
   * ห้ามสลับความหมายของแกนเหล่านี้เด็ดขาด! ห้ามเรียก AXIS_27 ว่าระบบเลือด หรือ Mitochondria เด็ดขาด!

2. EVIDENCE STATUS FOR EVERY STATEMENT (ระบบกำกับสถานะหลักฐาน):
   ทุกย่อหน้าที่วิเคราะห์ ต้องระบุและกำกับความน่าเชื่อถือด้วยสถานะหลักฐานต่อไปนี้เท่านั้น:
   - [MEASURED] = มีการวัดผลแล็บจริง
   - [DERIVED] = คำนวณตามดัชนีทางการแพทย์จริง
   - [CLINICAL_INFERENCE] = การอนุมานเชิงอาการแพทย์
   - [HYPOTHESIS] = สมมติฐานรอตรวจเพิ่มเติม (ห้ามสรุปเป็นความจริง และห้ามเพิ่มระดับความเสี่ยงของแกนชีวภาพนั้น)
   - [NOT_AVAILABLE] = ไม่มีข้อมูล
   * ตัวอย่าง: "[HYPOTHESIS] มีความเป็นไปได้ว่าสภาวะจุลชีพในลำไส้แปรปรวน (Microbiome Dysbiosis) เนื่องจากยังไม่มีผลการตรวจ Stool Analysis..."

3. NO DEFAULT 50/100 INFERENCES (ห้ามมโนภาวะผิดปกติเมื่อไม่มีข้อมูล):
   - แกนชีวภาพใดที่ระบุว่า "NOT ASSESSED" หรือไม่มีคะแนน ห้ามประเมินว่าเป็น "Mild" และห้ามเขียนวิเคราะห์ว่าคนไข้มีพยาธิสภาพในแกนนั้น (เช่น leaky gut, HPA dysregulation) ให้ระบุสั้นๆ ว่า "ไม่มีข้อมูลการตรวจวัดในด่านนี้ [NOT_AVAILABLE]" เท่านั้น!

4. THALASSEMIA TRAIT VS. IRON DEFICIENCY ANEMIA (การวิเคราะห์ภาวะโลหิตจาง):
   - ดัชนี Mentzer Index = MCV / RBC
   - หาก Mentzer Index น้อยกว่า 13 (เช่น MCV = 47.5 fL และ RBC = 6.76) ยืนยันรูปแบบ Microcytic Anemia ที่สงสัย Thalassemia Trait สูงมาก!
   - ห้ามสรุปทันทีว่าเป็น "Iron Deficiency Anemia (IDA)" และห้ามจ่ายธาตุเหล็ก (เช่น Ferrous Fumarate) หรือให้คนไข้ทานอาหารเสริมเหล็ก/เนื้อแดงปริมาณสูงโดยพลการเด็ดขาด!
   - แนะนำการตรวจยืนยันก่อนการรักษา: Ferritin, TIBC, Transferrin Saturation, และ Hb Typing

5. STRUCTURED HEADACHE RED-FLAG SCREENING (การคัดกรองสัญญาณอันตรายของอาการปวดศีรษะ):
   - คนไข้ที่มีอาการปวดหัวเรื้อรัง ต้องถูกตรวจเช็ค Red-Flags ก่อนประเมินสมุนไพร: ปวดเฉียบพลันรุนแรง (Thunderclap), มีไข้คอแข็ง, มีอาการทางระบบประสาทโฟคัล (อ่อนแรง, เห็นภาพซ้อน), ปวดขึ้นตอนเบ่ง/ไอ/ก้ม, มีประวัติตั้งครรภ์/มะเร็ง. หากมีข้อสงสัย ต้องส่งต่อแผนกฉุกเฉินทันที!

6. CANONICAL MODULE REGISTRY LOCK (ห้ามแต่งชื่อและกลไกสมุนไพรเอง):
   - ใช้เฉพาะโมดูลจริงที่มี H-Code ในสารบบเท่านั้น ได้แก่: RENAX (H-Code สำหรับฟื้นฟูไต/หลอดเลือด), IMO, RESHIMUNO, KS, Kerra, Minoza, Plumax, Livoxy, BoVa, Sangvichai.
   - ห้ามขยายตัวย่อผิด (เช่น KS ห้ามขยายเป็น Kappa Switcher เด็ดขาด!) และห้ามตั้งชื่อสินค้ามโนขึ้นมาใหม่ (เช่น ห้ามมี "Iron Replenish" หรือ "Neuro-Stress Module" เด็ดขาด!)

7. NO SIMULATED MOLECULAR PREDICTIONS:
   - ห้ามคาดการณ์ตัวเลขสมมติของค่าแล็บที่ไม่มีผลตรวจจริง เช่น IL-6, TNF-alpha หรือ Biological Age เด็ดขาด หากไม่มีข้อมูล ให้ระบุเป็น "NOT AVAILABLE".

8. PROFESSIONAL PRONOUNS (สรรพนามระดับสากล):
   - สำหรับคนไข้: ใช้คำสรรพนามแทนแพทย์ว่า "แพทย์ผู้ดูแล" หรือ "สถาบันการแพทย์ TSPI" และแทนคนไข้ว่า "คุณ [ชื่อคนไข้]" เท่านั้น! ห้ามใช้คำว่า "หนู, ผม, ฉัน, พี่" เด็ดขาด

9. OFFICIAL NINE RESTORATION STEPS LOCK (ห้ามเปลี่ยนชื่อหรือลำดับ Nine Restoration Steps เด็ดขาด):
   ชื่อและลำดับอันเป็นทางการของ TSPI ที่สำคัญเอกมีดังนี้เท่านั้น:
   Step 1: Detoxification
   Step 2: Microbiome Restoration
   Step 3: Immune Regulation
   Step 4: Redox Restoration
   Step 5: Mitochondrial Restoration
   Step 6: Autophagy
   Step 7: Genomic Stability
   Step 8: Genomic Regulation
   Step 9: Prakati / Biological Normalization
   * ห้ามแทนชื่อหรือสร้าง Steps ใหม่เด็ดขาด! เช่น ห้ามใช้ "Metabolic Control", "Sleep Regulation", "Hormonal Balance" หรือ "Structural Integrity" แทน Steps ทางการ!
   * AI สามารถอธิบายกิจกรรมภายใต้แต่ละ Step ได้ แต่ห้ามเปลี่ยนชื่อหรือลำดับเด็ดขาด!

10. NETWORK REGISTRY GATE (ระบบ Network ยังไม่พร้อม):
    - ต้องอ่านสถานะจาก ledger.network_registry.registry_status เท่านั้น — ตอนนี้คือ "LOADED_NOT_YET_APPROVED" (ข้อมูล Registry จริงถูกโหลดแล้ว แต่ยังไม่ได้รับการอนุมัติทางคลินิก)
    - ห้ามสร้างชื่อ Network หรือ Network score เอง (Generic network from LLM ไม่ใช่ Official 180 Networks)
    - ห้ามแสดงตัวเลข Network score เช่น 95/100, 90/100 เด็ดขาด
    - Network ใช้เพื่ออธิบายกลไกของ Axis Score เท่านั้น ไม่ใช่ตัวเลือก Module
    - ถ้าอยากกล่าวถึง Network ให้ระบุ: "[Network Mechanistic Context - PROVISIONAL. Official 180-Network Registry not yet APPROVED.]"

11. MODULE REGISTRY GATE (ระบบ Module ยังติด Blocker):
    - ต้องอ่านสถานะจาก ledger.module_registry.registry_status เท่านั้น (ตอนนี้คือ "PROVISIONAL" — ยังไม่มีโมดูลไหนได้ mapping_status = APPROVED เลยจากทั้งหมด ledger.module_registry.total_modules โมดูล)
    - ห้ามแสดง Module เป็นคำแนะนำทางคลินิก (ให้แสดงได้เฉพาะสถานะ: "PROVISIONAL CANDIDATE — NOT FOR CLINICAL USE" เท่านั้น)
    - ห้ามแสดง Matching Score, Synergy Score, Predicted Response หรือ Ranking ของ Module จนกว่า registry_status จะเป็น APPROVED
`;

const TSPI_FUNDAMENTAL_MEDICINE_RULES = `
รัฐธรรมนูญเวชศาสตร์รากฐาน TSPI (TSPI FUNDAMENTAL MEDICINE AI CONSTITUTION & REASONING PIPELINE):

1. STRICT SINGLE SOURCE OF TRUTH (Reasoning Ledger Alignment) — กฎนี้บังคับใช้กับทุกบทของทุกเล่มรายงาน (Physician, Patient, Multi-Omics) ไม่มีข้อยกเว้น:
   - กฎเหล็ก: ห้ามคำนวณ ประมาณ หรือคิดค้นตัวเลขคะแนนใหม่เด็ดขาด ไม่ว่าจะเป็นบทใดก็ตาม
   - Three Biological Keys: ต้องอ่านค่าตรงๆ จาก ledger.three_keys (metabolic_energy, biological_dynamic, biointegrity) เท่านั้น ถ้าเป็น null ให้แสดง "NOT_ASSESSED — ไม่มีข้อมูลการตรวจวัดที่เพียงพอ" ห้ามเปลี่ยนตัวเลขหรือคำนวณใหม่เด็ดขาด
   - Nine Restoration Steps: ต้องอ่านจาก ledger.nine_restoration_steps (Array ของ 9 Steps)
     * canonical_step_no และ canonical_step_name = คงที่เสมอ ตาม Official 9 Steps (ห้ามเปลี่ยน)
     * current_clinical_priority_rank = dynamic ตามคนไข้ (1 = เร่งด่วนที่สุด)
     * ใช้ current_clinical_priority_rank เพื่อเรียง priority ไม่ใช่ canonical_step_no
     * ถ้า current_clinical_priority_rank = null ให้แสดง "ยังไม่มีการประเมิน priority rank อย่างเป็นทางการ"
   - 39 Axes: ต้องอ่านคะแนนจาก ledger.thirty_nine_axes["AXIS_N"] เท่านั้น
   - Safety Gate: ต้องอ่านจาก ledger.safety_gate.status เท่านั้น (PASS/PASS_WITH_MONITORING/HOLD/CONTRAINDICATED/INSUFFICIENT_SAFETY_DATA) ห้ามแปลงเป็นตัวเลข Safety Score เด็ดขาด
   - ค่าแล็บหรือชื่อการตรวจใดๆ ที่ไม่ปรากฏใน [REASONING LEDGER]/[CONTEXT] ที่แนบมา ห้ามกล่าวถึงหรือระบุค่าตัวเลขเด็ดขาด แม้จะฟังดูสมเหตุสมผลทางคลินิกก็ตาม — ถ้าไม่มีข้อมูลให้ระบุว่า "ต้องตรวจเพิ่มเติม [NOT_AVAILABLE]"
   - ตัวเลขคะแนนและสถานะความรุนแรงต้องสอดคล้องตรงกัน 100% ข้ามทุกบทและทุกเล่มรายงาน (Physician, Patient, Multi-Omics)
   - ปิด Network score และ Module ranking หากระบบ Registry หรือ Mapping ยังไม่มี APPROVED status (ให้ใส่ PROVISIONAL CANDIDATE - NOT FOR CLINICAL USE)

2. MANDATORY DRAFT WATERMARK (ลายน้ำระบุร่าง):
   - ทุกๆ บทในรายงานนี้ถือเป็น "ร่างคำสั่งของปัญญาประดิษฐ์ที่ยังไม่ผ่านการอนุมัติและรับรองจากแพทย์"
   - บังคับใส่หัวข้อย่อยหรือสัญลักษณ์เตือนไว้ที่ส่วนแรกของบท: "AI-GENERATED CLINICAL DRAFT - PENDING PHYSICIAN REVIEW - NOT FOR PATIENT RELEASE"

3. CLINICAL PHRASING & SAFEGUARDS (ข้อจำกัดด้านน้ำเสียงและการวินิจฉัย):
   - ห้ามใช้ถ้อยคำที่ระบุการวินิจฉัยโรคอย่างเด็ดขาดและเกินจริง (เช่น ห้ามใช้คำว่า "Imaging confirms MASH" หรือ "คนไข้เป็นโรคตับอักเสบแน่นอน")
   - ให้เปลี่ยนเป็นภาษาชีววิทยาระบบและการอนุมานเชิงคลินิก เช่น "Findings are consistent with MASLD with suspected MASH..." หรือ "สภาวะทางชีววิทยาสอดคล้องกับ..."
   - ห้ามใช้คำว่า "Physician Approved" ในขั้นตอนใดๆ ตราบใดที่ยังไม่ได้รับการอนุมัติลงนามจริง

4. PHARMACOGENOMICS (ข้อมูลเภสัชพันธุศาสตร์ที่ถูกต้อง):
   - เมตฟอร์มิน (Metformin) ขับออกทางปัสสาวะในรูปที่ไม่มีการเปลี่ยนแปลง ผ่านระบบการขนส่งแบบ Active Renal Tubular Secretion (OCT2) ในไตเป็นหลัก ไม่ได้ผ่านการเมตาบอลิซึมโดยเอนไซม์ CYP450
   - ห้ามระบุว่า Metformin เมตาบอลิซึมทางตับหรือผ่านเอนไซม์ CYP450 เป็นอันขาด

5. SAFETY GATES VS. NUMERICAL SAFETY SCORES (ความปลอดภัยเป็นด่านคัดกรอง):
   - ห้ามรายงานความปลอดภัยของโมดูลหรือสารสกัดเป็นคะแนน (เช่น ความปลอดภัย 98/100)
   - ให้รายงานเป็นสถานะด่านคัดกรองความปลอดภัยอย่างเป็นทางการ: PASS (ผ่าน), PASS_WITH_MONITORING (ผ่านโดยต้องติดตามใกล้ชิด), HOLD (ระงับชั่วคราว), CONTRAINDICATED (มีข้อห้ามเด็ดขาด) หรือ INSUFFICIENT_SAFETY_DATA (ข้อมูลความปลอดภัยไม่เพียงพอ)
   - โมดูลที่มีข้อห้ามสำหรับภาวะ Thalassemia Trait (เช่น ธาตุเหล็กหรือโมดูล H-Code ที่ประกอบด้วยธาตุเหล็ก) ต้องแสดงสถานะ CONTRAINDICATED ทันทีเมื่อค่า Mentzer Index ต่ำกว่า 13

6. TRACEABLE COHORT CASES & RESEARCH EVIDENCE:
   - Case Intelligence: ห้ามสร้างตัวเลข Case Number, Match %, Response Rate เอง หากไม่มี query log จาก Clinical Database จริง ให้ระบุ: "[Case Intelligence: UNAVAILABLE. Clinical Case Database not yet connected.]"
   - Research Intelligence: ห้ามแสดง effect size, p-value, sample size หากไม่มี Study ID หรือ DOI จาก Official TSPI Research Registry ให้ระบุ: "[Research Intelligence: UNAVAILABLE. No verified Study ID from TSPI Research Registry.]"
   - Data ข้างใน [REASONING LEDGER] คือแหล่งข้อมูลเดียวที่ไว้ใจ ห้ามสร้างข้อมูลเสริมเติมนอกเหนือเด็ดขาด

7. NETWORK NARRATIVE = CLINICAL_CAUSAL_HYPOTHESIS เสมอ (P0-4.8):
   - 180-Network Registry และ Network Edges ยังไม่ได้รับการ APPROVED จากทีมคลินิก
   - ห้ามเรียก causal narrative ว่า "Official TSPI Network Propagation" หรือ "Network-driven root cause"
   - ทุก network causal cycle (เช่น Oncologic Toxicity Cycle, Bioenergetic Failure) ต้องระบุว่าเป็น [CLINICAL_CAUSAL_HYPOTHESIS — Network Registry not yet APPROVED]
   - Network อธิบายกลไกได้ แต่ห้ามใช้เป็น basis ของ Module selection หรือ Priority ranking จนกว่า edges จะ APPROVED

8. ห้าม REPORT LAYER สร้าง DOMAIN หรือ AXIS TIER ใหม่ (P0-4.4, 4.10):
   - Canonical 12 Domains มาจาก Domain Registry เท่านั้น ห้าม report สร้าง Domain ชื่อเช่น "Pulmonary & Cardiovascular", "Renal & Electrolyte", "Hematologic & Coagulation" แล้วเรียกว่า "TSPI Domain"
   - Axis role ที่ใช้ได้: PRIMARY, SECONDARY, MONITORING, CANDIDATE, NOT_ASSESSED
   - ห้ามสร้าง tier ใหม่เช่น "Tertiary Axis" เด็ดขาด

9. HYPOTHESIS ห้ามให้คะแนน และห้าม infer Module function (P0-4.1, 4.11):
   - Axis ที่ evidence_status = HYPOTHESIS หรือ assessment_status = AXIS_CANDIDATE → ห้ามปรากฏใน Top Priorities
   - ห้ามนำ HYPOTHESIS axis ไปเป็น basis ของ Module match หรือ priority ranking
   - Module ทุกตัวต้อง lookup จาก Approved Module Registry เท่านั้น ห้าม infer indication/function/mechanism จากชื่อ
   - Patient Report: ห้ามแสดงชื่อ Module ใดเลยจนกว่า Module Registry จะมี APPROVED status
   - Physician Report: ถ้าต้องแสดง Module เพื่อ QA ให้แยกเป็น "Development QA Appendix" ออกจาก Clinical Report หลัก

10. SEVERITY ≠ URGENCY ≠ DRIVER ≠ PRIORITY (P0-4.9):
    - ห้ามใช้ "Axis ที่มี severity_score สูงสุด = Primary Axis = root cause = Priority #1" โดยตรง
    - ต้องอ่านค่าแยกจาก Ledger:
      * severity_score = ระดับความผิดปกติ
      * clinical_urgency = null (รอ Django)
      * axis_role = PRIMARY/SECONDARY/MONITORING/CANDIDATE (อ่านจาก Ledger)
      * restoration_priority_rank = null (รอ Django)
    - ถ้า field เหล่านี้เป็น null ให้ระบุว่า "ยังไม่มีการประเมิน clinical urgency และ priority rank อย่างเป็นทางการ"

11. CUT-OFF AUTHORITY LABEL (P0-4.15):
    - ทุก threshold/cut-off ที่ใช้ในรายงานต้องระบุ authority type:
      * [STANDARD_CLINICAL] = มาตรฐานคลินิกสากล
      * [TSPI_SEVERITY_THRESHOLD] = เกณฑ์ TSPI ที่ ratified แล้ว
      * [PROVISIONAL_THRESHOLD] = ยังไม่ ratify — ห้ามเรียกว่า "Official TSPI Standard"
    - ถ้ายัง provisional ให้ label [PROVISIONAL_THRESHOLD] และห้ามเรียกว่า "Official TSPI Biological Cut-off"

12. CANONICAL AXIS LOCK TABLE — ห้าม Developer ตีความใหม่ (ans.txt Section 12):
    A8   = Mitochondrial Network (ไม่ใช่แหล่ง energy failure ทั่วไป; Hypoxemia ≠ direct mito measurement)
    A10  = Proteostasis–Autophagy–Lysosome (Protein quality/UPR/Autophagy)
    A26  = Stem Cell & Hematopoiesis (Hematopoietic axis)
    A27  = Glycation / Carbonyl Stress (ไม่ใช่ legacy Metabolic Balance; ต้องการ direct glycation marker)
    A29  = Bone Remodeling (primary bone axis)
    A30  = Connective Tissue Integrity (ไม่ใช่ชื่อรวมของ bone metastasis)
    A33  = Thyroid–Adrenal–Growth (Na/K/BP ใน renal illness = confounded; non-scoring)
    A34  = Neuro–Sleep–Stress–Brain Clearance (CELA อยู่ใต้ A34)
    A35  = Visceral Organ Functional Reserve (liver/kidney/heart/lung reserve)
    A37  = Oncologic Cell Fate
    A38  = Tumor Microenvironment & Metastatic Dynamics
    A39  = Genomic Regulation Homeostasis (ไม่ใช่ CELA)
    N120 = CELA (Cognitive–Emotional Loop Architecture) — Primary Axis A34 — APPROVED
    * ห้ามสลับความหมาย A29↔A30, A37↔A38, A27↔A26 เด็ดขาด

13. MODULE REGISTRY ABSOLUTE BLOCK:
    - ถ้า ledger.module_registry.approved_modules = 0 ให้ซ่อนชื่อ Module ทั้งหมดในเล่ม Physician, Patient และ Multi-Omics
    - ห้ามแสดงชื่อ Module เช่น RENAX, IMO, RESHIMUNO ในเนื้อหารายงาน clinical report หลัก จนกว่า registry_status = APPROVED

14. QUALITATIVE CONFIDENCE ONLY (NO PERCENTAGES):
    - ห้ามแสดง confidence เป็นตัวเลข % เช่น 78%, 85%, 90% ในเนื้อหารายงานเด็ดขาด
    - ให้ใช้ qualitative descriptors: VERY_HIGH / HIGH / MODERATE / LOW / VERY_LOW เท่านั้น

15. MANDATORY CLINICAL ACTION GOVERNANCE LABELS:
    - ทุกข้อความที่เป็นข้อเสนอหรือคำสั่งทางคลินิก ต้องติดป้ายกำกับหนึ่งในสี่สัญลักษณ์นี้เสมอ:
      * [CURRENT_PHYSICIAN_ORDER] = สิ่งที่แพทย์สั่งการรักษาแล้ว
      * [AI_SUGGESTED_CONSIDERATION] = ข้อเสนอพิจารณาจาก AI
      * [STANDARD_OF_CARE_REFERENCE] = มาตรฐานการรักษาอ้างอิงสากล
      * [PHYSICIAN_APPROVED_RECOMMENDATION] = ข้อแนะนำที่แพทย์อนุมัติแล้ว
    - ใน Patient Edition แสดงได้เฉพาะ [CURRENT_PHYSICIAN_ORDER] และ [PHYSICIAN_APPROVED_RECOMMENDATION] เท่านั้น

16. MULTI-OMICS RESOLUTION LAYER:
    - ข้อมูล Omics (Genomics, Metabolomics, Proteomics, Microbiome) เป็น Resolution Layer สำหรับการลงลึก ไม่ใช่ Prerequisite ในการประเมิน Axis
    - อาการ + ประวัติ + ผลแล็บ + ภาพถ่ายรังสี = First-class evidence ในการประเมิน Axis scores
    - ห้ามเขียนว่า "ต้องมีผลตรวจ Genomics ก่อนจึงจะประเมินแกนชีวภาพได้"

17. KNOWN DISEASE CONTEXT VS CURRENT SEVERITY:
    - ประวัติโรคประจำตัวเดิม (known_disease_context เช่น T2DM, HTN) เป็นบริบททางคลินิก
    - การให้ severity_score ต้องมาจากผลตรวจวัดปัจจุบันเท่านั้น ประวัติโรคเดิมเพียงอย่างเดียวไม่สามารถสร้าง severity_score ได้
`;



let cachedReportAiKeys: { deepseek?: string; groq?: string; gemini?: string } | null = null;

async function getReportAiKeys() {
  if (cachedReportAiKeys) return cachedReportAiKeys;
  let deepseekKey = process.env.DEEPSEEK_API_KEY || "";
  let groqKey = process.env.GROQ_API_KEY || "";
  let geminiKey = process.env.GEMINI_API_KEY || process.env.GOOGLE_AI_API_KEY || "";

  if (!deepseekKey || !groqKey || !geminiKey) {
    try {
      const backendBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
      const settingsRes = await fetch(`${backendBaseUrl}/api/settings/ai_settings/`);
      if (settingsRes.ok) {
        const settingsData = await settingsRes.json();
        const config = typeof settingsData.setting_value === "string"
          ? JSON.parse(settingsData.setting_value)
          : settingsData.setting_value;
        if (config) {
          if (!deepseekKey && config.deepseek_api_key) deepseekKey = config.deepseek_api_key;
          if (!groqKey && config.groq_api_key) groqKey = config.groq_api_key;
          if (!geminiKey && config.google_api_key) geminiKey = config.google_api_key;
        }
      }
    } catch (e) {
      console.warn("⚠️ Failed to fetch dynamic AI keys in report route from backend:", e);
    }
  }

  cachedReportAiKeys = {
    deepseek: deepseekKey || "dummy-key",
    groq: groqKey || "dummy-key",
    gemini: geminiKey || "dummy-key"
  };
  return cachedReportAiKeys;
}

// ─── Standard Medical Report Formatting & JSON Sanitizer ────────
// ─── P0-4.13: Cross-Report Invariant Validator ──────────────────
// บังคับตรวจสอบ Ledger ก่อน generate report ทุกครั้ง
// ถ้า FAIL → throw error และ block generation ทันที
// ─────────────────────────────────────────────────────────────────
interface InvariantViolation {
  rule_id: string;
  axis_or_field?: string;
  message: string;
}

function validateAnalysisRecord(ledger: any): void {
  const violations: InvariantViolation[] = [];

  // ── INV-1: HYPOTHESIS axis ห้ามมี severity_score ──────────────
  const axes = ledger.thirty_nine_axes || {};
  for (const [key, ax] of Object.entries(axes)) {
    const a = ax as any;
    if (a.evidence_status === "HYPOTHESIS" && a.severity_score !== null && a.severity_score !== undefined) {
      violations.push({
        rule_id: "INV-001",
        axis_or_field: key,
        message: `${key} (${a.evidence_status}) ห้ามมี severity_score = ${a.severity_score}. HYPOTHESIS never scores.`
      });
    }
  }

  // ── INV-2: HYPOTHESIS axis ห้ามมี eligible_for_priority = true ─
  for (const [key, ax] of Object.entries(axes)) {
    const a = ax as any;
    if (a.evidence_status === "HYPOTHESIS" && a.eligible_for_priority === true) {
      violations.push({
        rule_id: "INV-002",
        axis_or_field: key,
        message: `${key} is HYPOTHESIS but eligible_for_priority=true. Must be false.`
      });
    }
  }

  // ── INV-3: Three Keys ต้องเป็น DERIVED เสมอ ────────────────────
  const keys = ledger.three_keys || {};
  for (const [keyName, keyVal] of Object.entries(keys)) {
    const k = keyVal as any;
    if (k.evidence_status && k.evidence_status !== "DERIVED") {
      violations.push({
        rule_id: "INV-003",
        axis_or_field: `three_keys.${keyName}`,
        message: `three_keys.${keyName}.evidence_status = "${k.evidence_status}". Must be "DERIVED".`
      });
    }
  }

  // ── INV-4: Nine Steps canonical_step_no ต้องตรงกับ 1-9 ─────────
  const steps: any[] = ledger.nine_restoration_steps || [];
  if (Array.isArray(steps)) {
    const OFFICIAL_STEP_NAMES = [
      "Detoxification", "Microbiome Restoration", "Immune Regulation",
      "Redox Restoration", "Mitochondrial Restoration", "Autophagy",
      "Genomic Stability", "Genomic Regulation", "Prakati / Biological Normalization"
    ];
    steps.forEach((step, idx) => {
      const expectedNo = idx + 1;
      const expectedName = OFFICIAL_STEP_NAMES[idx];
      if (step.canonical_step_no !== expectedNo) {
        violations.push({
          rule_id: "INV-004",
          axis_or_field: `nine_restoration_steps[${idx}]`,
          message: `Step at index ${idx} has canonical_step_no=${step.canonical_step_no}, expected ${expectedNo}.`
        });
      }
      if (step.canonical_step_name !== expectedName) {
        violations.push({
          rule_id: "INV-004",
          axis_or_field: `nine_restoration_steps[${idx}].canonical_step_name`,
          message: `Step ${expectedNo} has name="${step.canonical_step_name}", expected "${expectedName}".`
        });
      }
    });
  }

  // ── INV-5: Network Registry ยังไม่ APPROVED ─────────────────────
  const netReg = ledger.network_registry || {};
  if (netReg.registry_status === "APPROVED") {
    // ถ้าจะ APPROVED ในอนาคตให้ลบ check นี้ออก แต่ตอนนี้ยังไม่ได้ approve
    violations.push({
      rule_id: "INV-005",
      axis_or_field: "network_registry.registry_status",
      message: "Network Registry is marked APPROVED but no clinical ratification has been recorded."
    });
  }

  // ── INV-6: Module Registry != APPROVED → Patient report gate ───
  const modReg = ledger.module_registry || {};
  if (modReg.approved_modules > 0 && modReg.registry_status !== "APPROVED") {
    violations.push({
      rule_id: "INV-006",
      axis_or_field: "module_registry",
      message: `Module registry has ${modReg.approved_modules} approved modules but registry_status="${modReg.registry_status}". Verify consistency.`
    });
  }

  // ── INV-7: Safety gate ห้ามเป็น legacy "CONTRAINDICATED" (global) ─
  // (ต้องใช้ intervention_eligibility แทน)
  if (ledger.safety_gate?.status === "CONTRAINDICATED") {
    violations.push({
      rule_id: "INV-007",
      axis_or_field: "safety_gate.status",
      message: `Global CONTRAINDICATED is deprecated. Use intervention_eligibility[] with specific intervention statuses instead.`
    });
  }

  // ── INV-9: Identity validation conflict blocks report generation ──
  const identity = ledger.identity_validation || {};
  if (identity.identity_validation_status === "CONFLICT" || identity.analysis_state === "BLOCKED_DATA_RECONCILIATION") {
    violations.push({
      rule_id: "INV-009",
      axis_or_field: "identity_validation",
      message: "Patient identity data conflict detected (BLOCKED_DATA_RECONCILIATION). Report generation is hard blocked."
    });
  }

  // ── INV-10: Axis scores must be marked DERIVED ────────────────────
  for (const [key, ax] of Object.entries(axes)) {
    const a = ax as any;
    if (a.severity_score !== null && a.severity_score !== undefined && a.score_derivation && a.score_derivation !== "DERIVED") {
      violations.push({
        rule_id: "INV-010",
        axis_or_field: `${key}.score_derivation`,
        message: `${key} has severity_score=${a.severity_score} but score_derivation="${a.score_derivation}". Must be "DERIVED".`
      });
    }
  }

  // ── INV-11: Approved modules = 0 -> Registry status must not be APPROVED ──
  if ((modReg.approved_modules ?? 0) === 0 && modReg.registry_status === "APPROVED") {
    violations.push({
      rule_id: "INV-011",
      axis_or_field: "module_registry.registry_status",
      message: "Module registry status is marked APPROVED but approved_modules count is 0."
    });
  }

  // ── INV-12: Respiratory state derived object must exist ──────────
  if (!ledger.respiratory_state || typeof ledger.respiratory_state !== "object") {
    violations.push({
      rule_id: "INV-012",
      axis_or_field: "respiratory_state",
      message: "Reasoning Ledger must contain a valid single derived respiratory_state object."
    });
  }

  // ── INV-13: Care goal mode field must exist ────────────────────────
  if (!ledger.care_goal_mode || typeof ledger.care_goal_mode !== "object") {
    violations.push({
      rule_id: "INV-013",
      axis_or_field: "care_goal_mode",
      message: "Reasoning Ledger must contain a care_goal_mode object."
    });
  }

  // ── INV-8: Mentzer index ต้องมี source provenance ───────────────
  // (ข้าม check นี้ถ้า mentzer_index = null)
  // จะ implement เต็มเมื่อ Mentzer provenance field พร้อม

  // ── รวมผลและ throw ถ้ามี violation ─────────────────────────────
  if (violations.length > 0) {
    const summary = violations.map((v, i) =>
      `[${v.rule_id}] ${v.axis_or_field ? `(${v.axis_or_field}) ` : ""}${v.message}`
    ).join("\n");
    console.error(`\n❌ ANALYSIS RECORD INVARIANT VIOLATION (${violations.length} violations):\n${summary}\n`);
    throw new Error(
      `TSPI Analysis Record failed ${violations.length} invariant check(s). Report generation blocked.\n\nViolations:\n${summary}`
    );
  }

  console.log("✅ Invariant validation passed — Analysis Record is internally consistent.");
}

// ─── Standard Medical Report Formatting & JSON Sanitizer ────────
function cleanMarkdownContent(content: string): string {
  if (!content) return "";
  let trimmed = content.trim();

  // Remove markdown code blocks if the LLM wrapped the JSON in it
  if (trimmed.startsWith("```json")) {
    trimmed = trimmed.replace(/^```json\s*/, "").replace(/\s*```$/, "").trim();
  } else if (trimmed.startsWith("```")) {
    trimmed = trimmed.replace(/^```\s*/, "").replace(/\s*```$/, "").trim();
  }

  let finalContent = trimmed;

  // Check if it's a JSON string
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try {
      const parsed = JSON.parse(trimmed);
      
      // Case 1: Array of objects or strings
      if (Array.isArray(parsed)) {
        finalContent = parsed.map((item: any) => {
          if (typeof item === 'string') return item;
          if (typeof item === 'object' && item !== null) {
            return item.content || item.clinical_baseline_content || item.analysis_summary || JSON.stringify(item);
          }
          return String(item);
        }).join("\n\n");
      }
      // Case 2: Object
      else if (typeof parsed === 'object' && parsed !== null) {
        if (parsed.content && typeof parsed.content === 'string') {
          finalContent = parsed.content;
        } else {
          const keys = Object.keys(parsed);
          if (keys.length === 1 && Array.isArray(parsed[keys[0]])) {
            finalContent = parsed[keys[0]].join("\n\n");
          } else {
            let md = "";
            for (const [key, value] of Object.entries(parsed)) {
              if (key.toLowerCase() === 'title' || key.toLowerCase() === 'chapter') {
                continue;
              }
              const formatKey = key
                .split('_')
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');
              
              md += `**${formatKey.toUpperCase()}**\n\n`;
              if (Array.isArray(value)) {
                md += value.map(val => `- ${val}`).join('\n') + '\n\n';
              } else if (typeof value === 'object' && value !== null) {
                md += JSON.stringify(value, null, 2) + '\n\n';
              } else {
                md += `${value}\n\n`;
              }
            }
            finalContent = md.trim();
          }
        }
      }
    } catch (e) {
      console.warn("Graceful JSON parsing fallback in route.ts:", e);
    }
  }

  // Double check if the nested content is still stringified JSON (recursive parse)
  if (finalContent !== trimmed && (finalContent.trim().startsWith("{") || finalContent.trim().startsWith("["))) {
    finalContent = cleanMarkdownContent(finalContent);
  }

  // Clean literal "\n" strings instead of actual newlines
  if (finalContent.includes("\\n")) {
    finalContent = finalContent.replace(/\\n/g, "\n");
  }
  if (finalContent.includes("\\\"")) {
    finalContent = finalContent.replace(/\\"/g, '"');
  }

  // 🩺 STANDARD MEDICAL FORMATTING: Strip '#' characters and convert to bold text headings
  const lines = finalContent.split("\n");
  const processedLines = lines.map(line => {
    const trimmedLine = line.trim();
    if (trimmedLine.startsWith("#")) {
      const match = trimmedLine.match(/^(#+)\s*(.*)$/);
      if (match) {
        const titleText = match[2].trim();
        return `**${titleText.toUpperCase()}**`;
      }
    }
    return line;
  });

  return processedLines.join("\n").trim();
}

// ─── AI Writing Engine: Deepseek → Groq fallback (Streaming) ─────
async function aiWrite(system: string, user: string, maxTokens = 32000): Promise<string> {
  const tokens = maxTokens;
  // Groq (fallback only, used when DeepSeek errors) is rate-limited on this account to
  // 12,000 tokens/minute total (prompt + completion) — requesting the same huge budget
  // as DeepSeek would make the fallback itself fail with rate_limit_exceeded, defeating
  // its purpose as a safety net. Cap it well under that ceiling instead.
  const groqTokens = Math.min(tokens, 6000);
  const store = reportStreamStorage.getStore();
  if (store) {
    let chapterTitle = "บทวิเคราะห์ระบบชีวภาพ";
    const foundLine = user
      .split("\n")
      .map(line => line.trim())
      .find(line => /^(?:สร้าง|วิเคราะห์)\s*(?:บทที่\s*|Chapter\s*)\d+/i.test(line));
    if (foundLine) {
      chapterTitle = foundLine.replace(/^(?:สร้าง|วิเคราะห์)\s*/i, "").replace(/:+$/, "").trim();
    }
    store.onChapterStart(chapterTitle);
  }

  const keys = await getReportAiKeys();
  let fullContent = "";
  let streamSuccess = false;

  // 1. Try DeepSeek AI
  if (keys.deepseek && keys.deepseek !== "dummy-key") {
    try {
      const deepseekClient = new OpenAI({ apiKey: keys.deepseek, baseURL: "https://api.deepseek.com/v1" });
      const stream = await deepseekClient.chat.completions.create({
        model: "deepseek-chat",
        messages: [{ role: "system", content: system }, { role: "user", content: user }],
        temperature: 0.6,
        max_tokens: tokens,
        stream: true,
      });

      for await (const chunk of stream) {
        const content = chunk.choices[0]?.delta?.content || "";
        if (content) {
          fullContent += content;
          if (store) store.enqueueChunk(content);
        }
      }
      if (fullContent) streamSuccess = true;
    } catch (e: any) {
      console.warn("⚠️ DeepSeek stream failed, falling back to Groq/Gemini:", e.message?.slice(0, 80));
    }
  }

  // 2. Try Groq (Llama 3.3) Fallback
  if (!streamSuccess && keys.groq && keys.groq !== "dummy-key") {
    try {
      const groqClient = new OpenAI({ apiKey: keys.groq, baseURL: "https://api.groq.com/openai/v1" });
      const stream = await groqClient.chat.completions.create({
        model: "llama-3.3-70b-versatile",
        messages: [{ role: "system", content: system }, { role: "user", content: user }],
        temperature: 0.6,
        max_tokens: groqTokens,
        stream: true,
      });

      for await (const chunk of stream) {
        const content = chunk.choices[0]?.delta?.content || "";
        if (content) {
          fullContent += content;
          if (store) store.enqueueChunk(content);
        }
      }
      if (fullContent) streamSuccess = true;
    } catch (err: any) {
      console.warn("⚠️ Groq stream failed, falling back to Gemini:", err.message?.slice(0, 80));
    }
  }

  // 3. Try Gemini 2.5 Flash Fallback
  if (!streamSuccess && keys.gemini && keys.gemini !== "dummy-key") {
    try {
      const genAI = new GoogleGenerativeAI(keys.gemini);
      const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash", systemInstruction: system });
      const result = await model.generateContentStream(user);

      for await (const chunk of result.stream) {
        const text = chunk.text();
        if (text) {
          fullContent += text;
          if (store) store.enqueueChunk(text);
        }
      }
      if (fullContent) streamSuccess = true;
    } catch (gemErr: any) {
      console.error("❌ All AI writing engines (Deepseek, Groq, Gemini) failed:", gemErr.message);
      throw gemErr;
    }
  }

  const cleaned = cleanMarkdownContent(fullContent);
  if (store) {
    let chapterTitle = "บทวิเคราะห์ระบบชีวภาพ";
    const foundLine = user
      .split("\n")
      .map(line => line.trim())
      .find(line => /^(?:สร้าง|วิเคราะห์)\s*(?:บทที่\s*|Chapter\s*)\d+/i.test(line));
    if (foundLine) {
      chapterTitle = foundLine.replace(/^(?:สร้าง|วิเคราะห์)\s*/i, "").replace(/:+$/, "").trim();
    }
    store.onChapterComplete(chapterTitle, cleaned);
  }
  return cleaned;
}

// ─── Stable hash of the clinical inputs used to compute a Reasoning Ledger ──────
// ใช้เพื่อรู้ว่า input (labs/symptoms) เปลี่ยนไปหรือไม่ระหว่างการ generate รายงานหลาย
// editions ของคนไข้คนเดียวกัน — ถ้า input เดิม ให้ reuse ledger เดิมแทนการคำนวณใหม่
// เพื่อให้ Physician/Patient/Multi-Omics editions ได้ตัวเลขตรงกัน 100%
function computeInputsHash(patientData: any): string {
  const normalized = JSON.stringify({
    labs: patientData.labs ?? null,
    symptoms: patientData.symptoms ?? null,
  });
  return crypto.createHash('sha256').update(normalized).digest('hex');
}

// ─── Fetch 39 Axis Scores from Django ───────────────────────────
async function getDjangoAxisScores(patientId: string, patientData: any, authHeader: string): Promise<any> {
  const backendBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
  const res = await fetch(
    `${backendBaseUrl}/api/patients/${patientId}/calculate-precision-medicine/`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(authHeader ? { "Authorization": authHeader } : {})
      },
      body: JSON.stringify({ labs: patientData.labs, symptoms: patientData.symptoms }),
    }
  );

  if (!res.ok) {
    const errorText = await res.text().catch(() => "");
    console.error(`❌ Django axis scores request failed (${res.status}):`, errorText);
    throw new Error(
      `ไม่สามารถคำนวณคะแนนแกนชีวภาพและ Safety Gate จากระบบหลังบ้านได้ (Django ตอบกลับ ${res.status}) — ไม่สามารถออกรายงานได้อย่างปลอดภัย`
    );
  }

  const d = await res.json();
  return {
    scores: d.axes_scores || d.axis_scores || d.scores || d.calculated_scores || {},
    mentzer_index: d.mentzer_index ?? null,
    three_keys: d.analysis?.three_keys ?? null,
    nine_restoration_steps: d.analysis?.nine_restoration_steps ?? null,
    module_registry_status: d.analysis?.module_registry_status ?? null,
    // P0-D: Django now computes the full evidence-status ledger (tspi_engine.py) — pass it
    // through so buildReasoningLedger() can use it directly instead of re-deriving in TS.
    thirty_nine_axes: d.analysis?.thirty_nine_axes ?? null,
    network_registry: d.analysis?.network_registry ?? null,
    analysis_record_id: d.analysis_record_id ?? null,
    is_valid: d.is_valid ?? null,
  };
}

// ─── Server-side patient record fetch/update for the Analysis Snapshot cache ────
// ไม่ใช้ @/utils/api/services (getPatient/updatePatient) เพราะไฟล์นั้นอ่าน token จาก
// localStorage ซึ่งไม่มีอยู่ฝั่ง server — ต้อง forward Authorization header ที่รับมาจาก
// client เองแทน
async function fetchPatientRecord(patientId: string, authHeader: string): Promise<any> {
  const backendBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
  try {
    const res = await fetch(`${backendBaseUrl}/api/patients/${patientId}/`, {
      headers: authHeader ? { "Authorization": authHeader } : {}
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    console.warn("⚠️ Failed to fetch patient record for snapshot cache check:", e);
    return null;
  }
}

async function updatePatientExtraData(patientId: string, authHeader: string, extraData: any): Promise<void> {
  const backendBaseUrl = process.env.NEXT_PUBLIC_API_URL || "https://tspi-backend.tanchonhomserverxxx.online";
  const res = await fetch(`${backendBaseUrl}/api/patients/${patientId}/`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...(authHeader ? { "Authorization": authHeader } : {})
    },
    body: JSON.stringify({ extra_data: extraData })
  });
  if (!res.ok) {
    throw new Error(`Failed to persist analysis snapshot (Django ${res.status})`);
  }
}

const OFFICIAL_9_STEPS = [
  "Detoxification",
  "Microbiome Restoration",
  "Immune Regulation",
  "Redox Restoration",
  "Mitochondrial Restoration",
  "Autophagy",
  "Genomic Stability",
  "Genomic Regulation",
  "Prakati / Biological Normalization"
];

function buildReasoningLedger(pd: any, axisScores: any, mentzerIndex: number | null, djangoKeys?: { three_keys?: any; nine_restoration_steps?: any; module_registry_status?: any; thirty_nine_axes?: any; network_registry?: any; analysis_record_id?: string | null } | null): any {
  const cleanScores: Record<number, number | null> = {};
  for (let i = 1; i <= 39; i++) {
    const rawVal = axisScores[`AXIS_${i}`] || axisScores[String(i)];
    let score = typeof rawVal === "number" ? rawVal : rawVal?.score ?? rawVal?.value ?? null;
    if (score === 50) {
      score = null;
    }
    cleanScores[i] = score;
  }

  const getAvg = (list: number[]) => {
    let sum = 0;
    let count = 0;
    for (const ax of list) {
      if (cleanScores[ax] !== null && cleanScores[ax] !== undefined) {
        sum += cleanScores[ax]!;
        count++;
      }
    }
    return count > 0 ? Math.round(sum / count) : null;
  };

  // ── Three Keys / Nine Restoration Steps — คำนวณที่ Django (tspi_engine.py) เป็น
  // single source of truth แล้ว (backend/patients/tspi_engine.py calculate_tspi_analysis)
  // ที่นี่แค่ประกอบ ledger จากผลลัพธ์ที่ Django ส่งมา ไม่คำนวณเองอีกต่อไป
  // Fallback (คำนวณเองด้วยสูตรเดิม) ใช้เฉพาะกรณี Django ไม่ส่ง field มา (เช่น เวอร์ชันเก่า/error)
  // ── P0-4.2 FIX: Three Keys ต้องเป็น DERIVED เสมอ พร้อม coverage/formula version ──────
  // (MEASURED ใช้สำหรับค่าแล็บดิบเท่านั้น เช่น HbA1c, CBC — ไม่ใช่ system-level construct)
  const KEY_AXIS_GROUPS = {
    metabolic_energy:  { axes: [5, 6, 7, 8, 9, 10],                             label: "Metabolic Energy" },
    biological_dynamic:{ axes: [20, 21, 22, 23, 31, 32, 33, 34],                label: "Biological Dynamic" },
    biointegrity:      { axes: [15, 16, 17, 18, 19, 24, 25, 26, 27, 28, 29, 30, 37, 38, 39], label: "Biointegrity" },
  };

  let rawThreeKeys = djangoKeys?.three_keys;
  let three_keys: Record<string, any>;

  if (rawThreeKeys) {
    // Django ส่งมา — ใส่ metadata เพิ่มเติมให้ครบ
    three_keys = {};
    for (const [key, group] of Object.entries(KEY_AXIS_GROUPS)) {
      const dk = (rawThreeKeys as any)[key] || {};
      const assessedAxes = group.axes.filter(ax => cleanScores[ax] !== null);
      three_keys[key] = {
        score: dk.score ?? null,
        evidence_status: "DERIVED",           // ← P0-4.2: บังคับ DERIVED เสมอ
        formula_version: dk.calculation_version ?? "keys-v1.0",
        contributing_axis_ids: group.axes,
        assessed_axes_count: assessedAxes.length,
        total_axes_in_group: group.axes.length,
        assessment_coverage: `${assessedAxes.length}/${group.axes.length}`,
        confidence: dk.confidence ?? null,
        key_uncertainty: assessedAxes.length < group.axes.length ? "PARTIAL_DATA" : "FULL_DATA",
        label: group.label,
        note: "Disturbance Score: higher = more disturbed (not health score)"
      };
    }
  } else {
    console.warn("⚠️ Django ไม่ได้ส่ง three_keys มา — fallback คำนวณใน TypeScript (ควรตรวจสอบ backend)");
    three_keys = {};
    for (const [key, group] of Object.entries(KEY_AXIS_GROUPS)) {
      const score = getAvg(group.axes);
      const assessedAxes = group.axes.filter(ax => cleanScores[ax] !== null);
      three_keys[key] = {
        score,
        evidence_status: "DERIVED",
        formula_version: "keys-v1.0-fallback",
        contributing_axis_ids: group.axes,
        assessed_axes_count: assessedAxes.length,
        total_axes_in_group: group.axes.length,
        assessment_coverage: `${assessedAxes.length}/${group.axes.length}`,
        confidence: score !== null ? 0.60 : null,  // fallback confidence ต่ำกว่า Django
        key_uncertainty: assessedAxes.length < group.axes.length ? "PARTIAL_DATA" : "FULL_DATA",
        label: group.label,
        note: "Disturbance Score (fallback). Django backend should provide this value."
      };
    }
  }

  // ── P0-4.3 FIX: Nine Steps — canonical_step_no/name คงที่เสมอ; priority rank = dynamic ─
  // ห้าม reorder/rename canonical step ตามความเร่งด่วนของคนไข้
  let rawNineSteps = djangoKeys?.nine_restoration_steps;
  let nine_restoration_steps: any[];

  if (rawNineSteps && Array.isArray(rawNineSteps)) {
    // Django ส่ง array มา — map กับ canonical step ตาม canonical_step_no
    nine_restoration_steps = OFFICIAL_9_STEPS.map((canonicalName, idx) => {
      const canonicalNo = idx + 1;
      const djangoStep = (rawNineSteps as any[]).find(
        (s: any) => s.canonical_step_no === canonicalNo || s.name === canonicalName
      ) || {};
      return {
        canonical_step_no: canonicalNo,         // ← คงที่เสมอ ห้ามเปลี่ยน
        canonical_step_name: canonicalName,      // ← คงที่เสมอ ห้ามเปลี่ยน
        current_clinical_priority_rank: djangoStep.priority_rank ?? null,  // ← dynamic
        current_step_status: djangoStep.status ?? "NOT_ASSESSED",          // ← dynamic
        assessment_status: djangoStep.assessment_status ?? "NOT_ASSESSED"
      };
    });
  } else {
    // Fallback: คำนวณ priority rank จาก Axis scores — canonical_step_no/name คงที่เสมอ
    console.warn("⚠️ Django ไม่ได้ส่ง nine_restoration_steps มา — fallback คำนวณใน TypeScript");
    const stepAxisMap = [
      cleanScores[15], cleanScores[17], getAvg([1, 2, 3, 4]), cleanScores[9], cleanScores[8],
      cleanScores[10], getAvg([11, 12]), cleanScores[39], cleanScores[35],
    ];
    // คำนวณ priority rank จาก disturbance score (สูงกว่า = เร่งด่วนกว่า)
    const rankedIndices = stepAxisMap
      .map((score, idx) => ({ idx, score }))
      .filter(x => x.score !== null && x.score !== undefined)
      .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
      .map((x, rank) => ({ idx: x.idx, rank: rank + 1 }));
    const rankMap: Record<number, number> = {};
    rankedIndices.forEach(({ idx, rank }) => { rankMap[idx] = rank; });

    nine_restoration_steps = OFFICIAL_9_STEPS.map((canonicalName, idx) => ({
      canonical_step_no: idx + 1,              // ← คงที่เสมอ
      canonical_step_name: canonicalName,       // ← คงที่เสมอ
      current_clinical_priority_rank: rankMap[idx] ?? null,  // ← dynamic
      current_step_status: stepAxisMap[idx] !== null ? "ASSESSED" : "NOT_ASSESSED",
      assessment_status: stepAxisMap[idx] !== null ? "ASSESSED" : "NOT_ASSESSED"
    }));
  }

  // ── P0-4.5/4.6/4.7/4.8/4.9 FIX: Axis Assessment พร้อม HYPOTHESIS no-score rule ────────
  //
  // HYPOTHESIS_AXES: Axes ที่ไม่มี Direct Lab Marker สนับสนุนโดยตรง
  //   → ห้ามมี severity_score (P0-4.1: HYPOTHESIS never scores)
  //   → assessment_status = AXIS_CANDIDATE
  //   → ไม่เข้า Priority ranking หรือ Module matching
  //
  // CONTEXT_ONLY_AXES: Axes ที่มี evidence แต่เป็นเพียง supporting context
  //   → marker_relation_type = CONTEXT_ONLY หรือ CONFOUNDED
  //   → score = CLINICAL_INFERENCE (ไม่ใช่ DERIVED)
  //
  // Canonical Axis Lock (P0-4.1 Section 12 / ans.txt บรรทัด 364-376):
  //   A8  = Mitochondrial Network
  //   A27 = Glycation / Carbonyl Stress (ไม่ใช่ legacy Metabolic Balance)
  //   A29 = Bone Remodeling (primary bone axis)
  //   A30 = Connective Tissue Integrity (ไม่ใช่ bone metastasis)
  //   A33 = Thyroid–Adrenal–Growth (Na/K/BP = confounded; non-scoring)
  //   A34 = Neuro–Sleep–Stress–Brain Clearance
  //   A35 = Visceral Organ Functional Reserve
  //   A37 = Oncologic Cell Fate
  //   A38 = Tumor Microenvironment & Metastatic Dynamics

  // Axes ที่ evidence_status = HYPOTHESIS (severity_score ต้อง null)
  const HYPOTHESIS_AXES = new Set([8, 16, 17, 19, 28, 30, 34]);

  // Axes ที่ marker เป็น SUPPORTING/CONFOUNDED → CLINICAL_INFERENCE
  // (มี evidence แต่ high confounding — A27 ต้องการ direct glycation marker; A33 confounded โดย renal)
  const CLINICAL_INFERENCE_AXES = new Set([27, 33]);

  // Axes ที่ oncology context → ถ้ามี evidence ให้ ASSESSED_CONTEXTUALLY (ไม่ใช่ NOT_AVAILABLE)
  const ONCOLOGY_CONTEXT_AXES = new Set([37, 38]);

  // P0-D: Django (tspi_engine.py) now computes this classification once as the source of
  // truth — use it directly when present. The block below is kept as a fallback only for
  // when the backend hasn't been deployed with the P0-A changes yet (avoid re-deriving a
  // second, possibly-drifting copy of the same evidence/HYPOTHESIS logic in TypeScript).
  let thirty_nine_axes: Record<string, any>;
  if (djangoKeys?.thirty_nine_axes && Object.keys(djangoKeys.thirty_nine_axes).length > 0) {
    thirty_nine_axes = djangoKeys.thirty_nine_axes;
  } else {
  console.warn("⚠️ Django ไม่ได้ส่ง thirty_nine_axes มา — fallback คำนวณใน TypeScript (ควรตรวจสอบ backend)");
  thirty_nine_axes = {};
  for (let i = 1; i <= 39; i++) {
    let axisScore = cleanScores[i];  // อาจถูก null ได้โดย HYPOTHESIS rule
    const name = getAxisName(i);

    // ── กำหนด evidence_status ก่อน ────────────────────────────────
    let evidence_status: string;
    let assessment_status: string;
    let axis_role = "CANDIDATE";
    let eligible_for_priority = true;
    let eligible_for_module_match = true;
    let marker_relation_type = "DIRECT_SCORING";  // P0-4.6 default
    let source_type_note = "LAB";                 // P0-4.7 default

    if (axisScore === null) {
      evidence_status = "NOT_AVAILABLE";
      assessment_status = "NOT_ASSESSED";
      eligible_for_priority = false;
      eligible_for_module_match = false;

    } else if (HYPOTHESIS_AXES.has(i)) {
      // P0-4.1 FIX: HYPOTHESIS → severity = null, NOT_SCORED
      evidence_status = "HYPOTHESIS";
      assessment_status = "AXIS_CANDIDATE";
      axisScore = null;              // ← บังคับ null — HYPOTHESIS never scores
      eligible_for_priority = false;
      eligible_for_module_match = false;
      marker_relation_type = "NON_SCORING";

    } else if (CLINICAL_INFERENCE_AXES.has(i)) {
      // P0-4.5: A27/A33 — risk context ≠ measured burden → CLINICAL_INFERENCE
      evidence_status = "CLINICAL_INFERENCE";
      assessment_status = "ASSESSED";
      marker_relation_type = "CONFOUNDED";  // P0-4.6
      eligible_for_module_match = false;

    } else if (ONCOLOGY_CONTEXT_AXES.has(i)) {
      // P0-4.5: A37/A38 — ถ้ามี evidence context → ASSESSED_CONTEXTUALLY (ไม่ใช่ NOT_AVAILABLE)
      evidence_status = "CLINICAL_INFERENCE";
      assessment_status = "ASSESSED_CONTEXTUALLY";
      marker_relation_type = "SUPPORTING";

    } else {
      // Axes ที่มี Lab สนับสนุนโดยตรง → DERIVED
      evidence_status = "DERIVED";
      assessment_status = "ASSESSED";
    }

    // ── severity_band (เฉพาะ axes ที่มีคะแนน) ──────────────────────
    let severity_band: string;
    let severity_score: number | null = axisScore;

    if (severity_score === null) {
      severity_band = assessment_status === "AXIS_CANDIDATE" ? "NOT_SCORED" : "NOT_ASSESSED";
    } else if (severity_score <= 15) {
      severity_band = "Optimal";
    } else if (severity_score <= 30) {
      severity_band = "Early Biological Disturbance";
    } else if (severity_score <= 60) {
      severity_band = "Functional Disturbance";
    } else if (severity_score <= 80) {
      severity_band = "Pathological Disturbance";
    } else {
      severity_band = "Critical Value";
    }

    // ── P0-4.9 FIX: แยก severity / urgency / role / priority ────────
    // (ปัจจุบัน fallback ให้ข้อมูล static; Django จะ enrich ต่อไป)
    const axis_assessment: Record<string, any> = {
      code: `A${i}`,
      name,
      // Scoring
      severity_score,
      severity_band,
      scoring_formula_version: "axis-v1.0",
      // Evidence
      evidence_status,
      marker_relation_type,      // P0-4.6: DIRECT_SCORING | SUPPORTING | CONTEXT_ONLY | CONFOUNDED | NON_SCORING
      source_type_note,          // P0-4.7: LAB | HISTORY | CLINICAL_INFERENCE | etc.
      // Status
      assessment_status,
      axis_role,                 // P0-4.9/4.10: PRIMARY | SECONDARY | MONITORING | CANDIDATE | NOT_ASSESSED
      // Priority flags
      eligible_for_priority,
      eligible_for_module_match,
      // P0-4.9 extra fields (Django จะ fill จริงใน future)
      clinical_urgency: null,
      causal_driver_probability: null,
      restoration_priority_rank: null,
      treatment_priority_rank: null,
    };

    thirty_nine_axes[`AXIS_${i}`] = axis_assessment;
  }
  }

  // ── P0-4.14 FIX: Safety Gate — intervention-specific eligibility แทน global CONTRAINDICATED ─
  // (global CONTRAINDICATED ทำให้เข้าใจว่าทุก intervention ถูกห้าม — ผิด concept)
  let safety_status = "PASS";
  const global_alerts: string[] = [];
  const intervention_eligibility: Array<{
    intervention_id: string;
    status: "PASS" | "MONITOR" | "HOLD" | "CONTRAINDICATED" | "INSUFFICIENT_DATA";
    reason_rule_id: string;
    required_confirmation: string[];
  }> = [];

  if (mentzerIndex !== null && mentzerIndex < 13) {
    // Mentzer < 13 → สงสัย Thalassemia Trait → ห้ามจ่าย Iron เท่านั้น ไม่ใช่ทุก intervention
    safety_status = "PASS_WITH_MONITORING";
    global_alerts.push(
      `🚨 CRITICAL: Mentzer Index = ${mentzerIndex.toFixed(2)} (< 13). Pattern consistent with Thalassemia Trait. ` +
      `Iron supplementation is HOLD pending Hb Typing + Ferritin confirmation. ` +
      `Other interventions require individual safety assessment."`
    );
    intervention_eligibility.push({
      intervention_id: "IRON_SUPPLEMENTATION",
      status: "HOLD",
      reason_rule_id: "MENTZER_THAL_GATE_001",
      required_confirmation: ["Ferritin", "TIBC", "Transferrin Saturation", "Hb Typing"]
    });
    intervention_eligibility.push({
      intervention_id: "HIGH_DOSE_RED_MEAT_DIET",
      status: "HOLD",
      reason_rule_id: "MENTZER_THAL_GATE_001",
      required_confirmation: ["Hb Typing"]
    });
  }

  // ── Network Registry Gate
  // ไฟล์ 180_Network.json มีข้อมูลจริงแล้ว (โหลดจาก data/last_dta/180_Network.json) แต่ยังไม่ได้รับ
  // การยืนยัน status = APPROVED จากทีมคลินิก — ledger นี้แค่ทำให้ registry ที่มีอยู่จริง
  // "มองเห็นได้" โดยระบบ (มี metadata จริง ไม่ใช่ string เปล่าในพรอมต์) ยังไม่เปิดให้ LLM
  // อ้างชื่อ/คะแนน Network จนกว่า registry_status จะถูกเปลี่ยนเป็น APPROVED
  const network_registry = djangoKeys?.network_registry ?? {
    registry_status: "LOADED_NOT_YET_APPROVED",
    total_networks: networkRegistryData.metadata?.total_networks ?? null,
    source_version: networkRegistryData.version ?? null,
    blocker_reason: "Official 180-Network Registry data is loaded but has not been clinically APPROVED. Do not generate network names or network scores.",
    display_instruction: "PROVISIONAL CANDIDATE — NOT FOR CLINICAL USE. Networks may be referenced only as mechanistic context, never with a numeric score, until registry_status becomes APPROVED."
  };

  // ── Module Registry Gate
  // สถานะจริงจาก Django (tspi_engine.py) — เช็คว่ามีโมดูลไหนใน Master Data ถูกตั้ง
  // mapping_status = APPROVED บ้างหรือยัง ตอนนี้ยังไม่มีเลย (PROVISIONAL ทั้งหมด)
  const module_registry = djangoKeys?.module_registry_status
    ? {
        registry_status: djangoKeys.module_registry_status.status,
        total_modules: djangoKeys.module_registry_status.total_modules,
        approved_modules: djangoKeys.module_registry_status.approved_modules,
        blocker_reason: "Module Registry mapping_status is not APPROVED for any module yet.",
        display_instruction: "PROVISIONAL CANDIDATE — NOT FOR CLINICAL USE. Do not display Matching Score, Synergy Score, Predicted Response, or Ranking until registry_status becomes APPROVED."
      }
    : {
        registry_status: "PROVISIONAL",
        total_modules: null,
        approved_modules: 0,
        blocker_reason: "Module Registry status unavailable from backend.",
        display_instruction: "PROVISIONAL CANDIDATE — NOT FOR CLINICAL USE."
      };

  // ── Case Intelligence Gate
  // ⚠️ Clinical Case Database ยังไม่พร้อมใช้งาน — ห้ามแสดง Case Number หรือ Match % สมมติ
  // เมื่อ Clinical Database พร้อม ให้เปลี่ยน status เป็น AVAILABLE และส่งผล query จริงเข้ามา
  const ai_case_intelligence = {
    registry_status: "UNAVAILABLE",
    blocker_reason: "Clinical Case Database not yet connected. No query log available.",
    display_instruction: "PROVISIONAL CANDIDATE — NOT FOR CLINICAL USE. Do not generate case numbers, match percentages, or response rates without a verified database query result."
  };

  // ── Research Intelligence Gate
  // ⚠️ Research Database ยังไม่ได้เชื่อมต่อกับแหล่งข้อมูลจริง — ห้ามแสดงตัวเลข effect size, p-value
  // หรือ sample size ที่ไม่มี Study ID จากฐานข้อมูลจริง
  // เมื่อ Research Registry พร้อม ให้ load จาก verified study database และ pass เข้ามาที่นี่
  const research_database = [
    {
      registry_status: "UNAVAILABLE",
      blocker_reason: "Research Registry not yet connected. No verified Study IDs available.",
      display_instruction: "PROVISIONAL CANDIDATE — NOT FOR CLINICAL USE. Do not display effect sizes, p-values, or sample sizes without a verified Study ID and DOI from the official TSPI Research Registry."
    }
  ];

  return {
    framework_version: "39-axis-master-260715",
    // P0-C: prefer the immutable Django AnalysisRecord id so PDF export and other editions
    // can look up the exact same record (ans.txt problem #9); fall back to a per-run id only
    // if Django didn't persist one (e.g. older backend).
    analysis_record_id: djangoKeys?.analysis_record_id ?? `TSPI-${Date.now()}`,
    identity_validation: (djangoKeys as any)?.identity_validation ?? {
      identity_validation_status: "VERIFIED",
      analysis_state: "ANALYSIS_READY",
      conflict_details: []
    },
    care_goal_mode: (djangoKeys as any)?.care_goal_mode ?? {
      mode: "NOT_SET",
      source: "default",
      note: "Must be set by physician before report generation."
    },
    respiratory_state: (djangoKeys as any)?.respiratory_state ?? {
      classification: "NOT_ASSESSED",
      pO2: null,
      pCO2: null,
      classification_confidence: "INSUFFICIENT_DATA",
      rule_id: null,
      physician_review_required: true
    },
    domain_mapping: {
      canonical_domains: [
        { code: "D1", name: "Domain 1 — Immune–Infection Governance" },
        { code: "D2", name: "Domain 2 — Metabolic–Energy Core" },
        { code: "D3", name: "Domain 3 — Genomic–Longevity Programming" },
        { code: "D4", name: "Domain 4 — Detox–Digestive–Gut Ecosystem" },
        { code: "D5", name: "Domain 5 — Vascular–Circulation–Stroke Prevention" },
        { code: "D6", name: "Domain 6 — Repair–Fibrosis–Regeneration" },
        { code: "D7", name: "Domain 7 — Musculoskeletal & Structural Integrity" },
        { code: "D8", name: "Domain 8 — Endocrine Network" },
        { code: "D9", name: "Domain 9 — Neuro–Sleep–Stress" },
        { code: "D10", name: "Domain 10 — Organ Axis + Oncology" },
        { code: "D11", name: "Domain 11 — Regeneration & Repair System" },
        { code: "D12", name: "Domain 12 — Proteostasis & Cellular Integrity" }
      ],
      clinical_problem_groups: [
        { group: "Renal & Electrolyte", axes: ["A33", "A35"] },
        { group: "Oncologic Dynamics", axes: ["A36", "A37", "A38"] }
      ]
    },
    three_keys,
    nine_restoration_steps,
    thirty_nine_axes,
    safety_gate: {
      status: safety_status,
      global_alerts,                   // P0-4.14: global alerts แยก
      intervention_eligibility,        // P0-4.14: intervention-specific eligibility
    },
    network_registry,
    module_registry,
    ai_case_intelligence,
    research_database,
    pharmacogenomics: {
      metformin_clearance: "Excreted unchanged in urine via active renal tubular secretion (OCT2). Not metabolized by CYP450.",
      atorvastatin_clearance: "Metabolized primarily by CYP3A4. Concomitant use with strong CYP3A4 inhibitors increases exposure and risk of myopathy.",
      amlodipine_clearance: "Metabolized slowly by CYP3A4."
    },
    status: "AI-GENERATED CLINICAL DRAFT - PENDING PHYSICIAN REVIEW - NOT FOR PATIENT RELEASE"
  };
}

// ─── Build Axis Score Summary Text ──────────────────────────────
function buildAxisText(axisScores: any): string {
  if (!axisScores || Object.keys(axisScores).length === 0)
    return "ไม่มีข้อมูล Axis Scores — แนะนำรัน calculate-precision-medicine ก่อน";
  return Object.entries(axisScores)
    .map(([k, v]: [string, any]) => {
      const score = typeof v === "number" ? v : v?.score ?? v?.value ?? null;
      if (score === null || score === undefined || score === 50) {
        return `- ${k}: NOT ASSESSED (ไม่มีข้อมูลการตรวจวัดในด่านนี้ - Evidence Status: NOT_AVAILABLE / Confidence: None / Effect on axis score: None)`;
      }
      const lvl =
        score > 75 ? "Severe" : score > 50 ? "Moderate" : score > 25 ? "Mild" : "Normal";
      return `- ${k}: ${score}/100 (${lvl} - Evidence Status: MEASURED)`;
    })
    .join("\n");
}

// ─── Build Patient Context String ───────────────────────────────
function buildContext(pd: any, axisScores: any, mentzerIndex: number | null, ledger: any): string {
  const labs = pd.labs || {};
  const profile = pd.profile || {};

  let mentzerWarning = "";
  if (mentzerIndex !== null && mentzerIndex !== undefined) {
    mentzerWarning = `
CLINICAL DATA FLAG: Mentzer Index calculated as ${mentzerIndex}.
`;
    if (mentzerIndex < 13) {
      mentzerWarning += `WARNING: Mentzer Index is < 13 (${mentzerIndex}). This is a strong indicator of THALASSEMIA TRAIT rather than simple Iron Deficiency Anemia (IDA).
CLINICAL CONTRAINDICATION: DO NOT recommend iron supplements, iron-dosing modules (e.g. Ferrous Fumarate), or high-iron red meat/liver diets. Recommend Hb Typing, Ferritin, and Serum Iron to rule out Thalassemia before iron therapy.
`;
    }
  }

  return `
ข้อมูลคนไข้:
- ชื่อ: ${profile.first_name || profile.fname || ""} ${profile.last_name || profile.lname || ""}
- อายุ: ${profile.age || "ไม่ระบุ"} ปี
- เพศ: ${profile.gender || "ไม่ระบุ"}
- โรคหลัก: ${profile.diagnosis || profile.underlying_disease || "ไม่ระบุ"}
- ยาที่ใช้: ${pd.medications || profile.current_medications || "ไม่ระบุ"}
- อาการสำคัญ / SOAP Note: ${pd.symptoms || "ไม่ระบุ"}
- ประวัติทางการแพทย์: ${pd.history || "ไม่ระบุ"}
${mentzerWarning}
ผลแล็บ:
- FBS: ${labs.fbs || "ไม่ระบุ"} mg/dL
- HbA1c: ${labs.hba1c || "ไม่ระบุ"} %
- Doppler: ${labs.doppler || "ไม่ระบุ"}
- Cholesterol: ${labs.Cholesterol || labs.cholesterol || "ไม่ระบุ"}
- Triglycerides: ${labs.Triglycerides || labs.triglycerides || "ไม่ระบุ"}
- hs-CRP: ${labs["hs-CRP"] || labs.crp || "ไม่ระบุ"}
- MCV: ${labs.mcv || "ไม่ระบุ"} fL
- RBC: ${labs.rbc || "ไม่ระบุ"} million/µL
- Hb: ${labs.hb || "ไม่ระบุ"} g/dL
- Hct: ${labs.hct || "ไม่ระบุ"} %
- แล็บอื่นๆ: ${JSON.stringify(labs)}

คะแนน 39 Biological Axes:
${buildAxisText(axisScores)}

Genomics: ${JSON.stringify(pd.genomics || {})}
Microbiome: ${JSON.stringify(pd.microbiome || {})}
Metabolomics: ${JSON.stringify(pd.metabolomics || {})}
Proteomics: ${JSON.stringify(pd.proteomics || {})}

[REASONING LEDGER - SINGLE SOURCE OF TRUTH]
${JSON.stringify(ledger, null, 2)}
  `.trim();
}

// ═══════════════════════════════════════════════════════════════════
//  📋 PHYSICIAN EDITION — TSPI FUNDAMENTAL MEDICINE ENGINE
// ═══════════════════════════════════════════════════════════════════
async function generatePhysicianReport(ctx: string, ax: any): Promise<Record<string, any>> {
  const SYS = `คุณคือ TSPI Chief Medical Officer ผู้เชี่ยวชาญ Precision Medicine และ Systems Biology ระดับสูงสุด
วิเคราะห์ข้อมูลคนไข้ตาม TSPI 11-Step Reasoning Pipeline:
Clinical Evidence → Three Biological Keys → Nine Restoration Steps → Twelve Domains → 39 Axes → 180 Networks → Research Intelligence → Case Intelligence → 200 Modules → Disease Interpretation → Final Reports

หลักสำคัญ: 
- ตัวโรคปลายทาง (Disease Interpretation) เป็นเพียงผลสรุปสำหรับสื่อสารแพทย์ในขั้นตอนสุดท้าย ห้ามใช้ชื่อโรคเป็นตัวตั้งต้นของการวิเคราะห์เด็ดขาด!
- หากไม่มีข้อมูลให้ระบุว่า "ต้องตรวจเพิ่มเติม [NOT_AVAILABLE]" ห้ามเดาสุ่ม
- กฎเหล็กด้านรูปแบบ: ห้ามใช้เครื่องหมายแฮชหรือชาร์ป (#, ##, ###) ในการทำหัวข้อ ให้ใช้ตัวหนาพิมพ์ใหญ่หรือตัวหนาธรรมดาสำหรับหัวข้อแทน ห้ามส่งข้อมูลรูปแบบ JSON หรือโค้ดคอมพิวเตอร์ปะปนในเนื้อหา
- ห้ามใช้ Emoji หรือสัญลักษณ์รูปภาพ (เช่น ✅ 🚨 ⚠️ 🔴 🟢 🎉) ในเนื้อหาเด็ดขาด เอกสารนี้เป็นเอกสารทางการแพทย์ระดับวิชาชีพ ให้ใช้ข้อความหรือคำระบุสถานะแทน (เช่น "ผ่าน", "ข้อควรระวัง", "อันตราย")

${CLINICAL_SAFETY_RULES}

${TSPI_FUNDAMENTAL_MEDICINE_RULES}`;

  const chs: Record<string, any> = {};
  const axText = buildAxisText(ax);

  // ── Chapter 1: TSPI Biological State Summary & Safety Screening ──
  console.log("📝 [Physician] Chapter 1: TSPI Biological State Summary & Safety Screening");
  chs["1"] = {
    title: "Chapter 1 — TSPI Biological State Summary & Red Flag Safety Screening",
    content: await aiWrite(SYS, `${ctx}

สร้าง Chapter 1: TSPI Biological State Summary (หน้าสรุปภาวะทางชีวภาพของคนไข้เพื่อให้แพทย์เข้าใจใน 30 วินาที):

กฎเหล็ก: ห้ามคำนวณหรือประมาณตัวเลขคะแนนใหม่เด็ดขาด ให้อ่านตัวเลขจาก [REASONING LEDGER] ที่แนบมาเท่านั้น

1. **THREE BIOLOGICAL KEYS — อ่านจาก REASONING LEDGER เท่านั้น**:
   - ต้องอ่านและแสดงคะแนนตรงๆ จาก ledger.three_keys ดังนี้:
     * Metabolic Energy Score (axis_disturbance_score: คะแนนสูง = ระบบมีความผิดปกติมาก)
     * Biological Dynamic Score (axis_disturbance_score: คะแนนสูง = ระบบมีความผิดปกติมาก)
     * Biointegrity Score (axis_disturbance_score: คะแนนสูง = ระบบมีความผิดปกติมาก)
   - ถ้าคะแนนใดเป็น null ให้แสดง: "NOT_ASSESSED — ไม่มีข้อมูลการตรวจวัดที่เพียงพอในกลุ่มแกนนี้"
   - ห้ามเปลี่ยนตัวเลขหรือคำนวณใหม่เด็ดขาด!

2. **NINE RESTORATION STEPS PRIORITY — อ่านจาก REASONING LEDGER เท่านั้น**:
   - ledger.nine_restoration_steps คือ Array ของ 9 Steps โดย:
     * 'canonical_step_no' + 'canonical_step_name' = คงที่ตาม Official TSPI ห้ามเปลี่ยน
     * 'current_clinical_priority_rank' = dynamic ตามคนไข้ (1 = เร่งด่วนสุด)
   - เรียง Steps ตาม current_clinical_priority_rank เพื่อแสดง Priority Order
   - ถ้า current_clinical_priority_rank = null ให้ระบุ: "ยังไม่มีการประเมิน clinical priority rank อย่างเป็นทางการ"
   - ชื่อ canonical_step_name ต้องแสดงตรงตามที่อยู่ใน Ledger เท่านั้น (Official 9 Steps)

3. **TOP 10 BIOLOGICAL RESTORATION PRIORITIES**:
   - จัดลำดับความสำคัญการฟื้นฟูทางชีวภาพ 10 อันดับแรก โดยตั้งชื่อตามระบบชีวภาพ (Biological Priority) เช่น "Priority 1: Restore Renal Energy Network", "Priority 2: Reduce Carbonyl Stress", "Priority 3: Restore Mitochondrial Network" (ห้ามตั้งชื่อตามชื่อโรคเด็ดขาด!)

4. **SAFETY GATE STATUS — อ่านจาก REASONING LEDGER เท่านั้น**:
   - ต้องอ่าน ledger.safety_gate.status และแสดงเป็นสถานะ: PASS, PASS_WITH_MONITORING, HOLD, CONTRAINDICATED, หรือ INSUFFICIENT_SAFETY_DATA
   - ห้ามแปลงเป็นตัวเลข Safety Score เด็ดขาด!
   - ถ้า ledger.safety_gate.global_alerts มีข้อความ ให้แสดงพร้อมระบุข้อห้ามทางคลินิกทันที
   - ledger.safety_gate.intervention_eligibility คือรายการ intervention แบบ specific:
     * status = HOLD → ห้ามใช้ intervention นั้นจนกว่าจะยืนยัน required_confirmation ครบ
     * status = CONTRAINDICATED → ห้ามใช้เด็ดขาด
     * ห้ามบอกว่า "ทุก intervention ถูกห้าม" ถ้าแค่บางรายการเท่านั้นที่ HOLD
   - ตรวจคัดกรองสัญญาณอันตราย (Red Flags ที่ triggered จากข้อมูลจริงเท่านั้น) หากพบ ให้แจ้งเตือนและระบุคำสั่งส่งต่อแผนกฉุกเฉินทันที`),
  };


  // ── Chapter 2: Evidence Integration, Evidence Chains & Contradiction Engine ──
  console.log("📝 [Physician] Chapter 2: Evidence Chains & Contradiction Engine");
  chs["2"] = {
    title: "Chapter 2 — Evidence Integration, Evidence Chains & Contradiction Engine",
    content: await aiWrite(SYS, `${ctx}

สร้าง Chapter 2: Evidence Integration, Evidence Chains & Contradiction Engine:

1. **MARKER REGISTRY & BIOLOGICAL CUT-OFFS**:
   - วิเคราะห์ค่าแล็บ CBC และอื่นๆ โดยอ้างอิง TSPI Biological Cut-off 5 ระดับ (Optimal, Early Disturbance, Functional Disturbance, Pathological Disturbance, Critical Value)
   - แสดงค่า Mentzer Index (MCV / RBC) และกฎเหล็ก: หาก Mentzer Index < 13 ต้องเน้นย้ำเตือนทันทีว่า "สงสัยภาวะ Thalassemia Trait สูงมาก" และห้ามเริ่มจ่ายธาตุเหล็ก/Ferrous Fumarate จนกว่าจะตรวจ Ferritin และ Hb Typing ยืนยัน

2. **EVIDENCE CHAIN GRAPH**:
   - บังคับสร้างห่วงโซ่หลักฐานแบบวิถี เช่น:
     Hb typing absent → Hb ต่ำ → MCV ต่ำมาก → Mentzer Index < 13 → สงสัยพาหะธาลัสซีเมียแฝง → ความมั่นใจ 83%

3. **CONTRADICTION ANALYSIS BLOCK**:
   - ตรวจสอบความขัดแย้งของตัวบ่งชี้ทางคลินิก (เช่น Microcytic Anemia ที่สอดคล้องทั้ง Thalassemia Trait และ IDA) ชี้แจงส่วนขาดของข้อมูลอย่างเปิดเผย และระบุระดับความไม่แน่นอน

4. **5-LEVEL CONFIDENCE BREAKDOWN**:
   - ระบุระดับความเชื่อมั่นแยก 5 มิติ: Data Confidence (X%), Evidence Confidence (Y%), Biological Confidence (Z%), Module Confidence (W%), Prediction Confidence (V%)`),
  };

  // ── Chapter 3: 39 Biological Axes & 180 Networks Reasoning ──
  console.log("📝 [Physician] Chapter 3: Systems Biology & Network Reasoning");
  chs["3"] = {
    title: "Chapter 3 — Thirty-Nine Biological Axes & One Hundred Eighty Networks Reasoning",
    content: await aiWrite(SYS, `${ctx}
${axText}

สร้าง Chapter 3: 39 Biological Axes & 180 Networks Reasoning:
1. บังคับวิเคราะห์ตามลำดับขั้น: Clinical Evidence → 12 Domains → 39 Biological Axes → 180 Networks
2. ประเมินแกนชีวภาพที่มีความผิดปกติหลัก (Primary/Secondary Axes) เฉพาะที่มีข้อมูลตรวจจริง แกนที่ไม่มีข้อมูล (NOT ASSESSED) ให้ลงสถานะเป็น [NOT_AVAILABLE] เท่านั้น
3. อธิบายการส่งผ่านความบกพร่องข้ามแกน (Network Propagation / Chain Effect) และกลไกการชดเชยที่ล้มเหลว (Homeostatic failure)
4. ทุกย่อหน้าวิเคราะห์ต้องกำกับด้วยสถานะหลักฐาน: [MEASURED], [DERIVED], [CLINICAL_INFERENCE], [HYPOTHESIS]`),
  };

  // ── Chapter 4: AI Case Intelligence & Research-Backed Module Matrix ──
  console.log("📝 [Physician] Chapter 4: Module Matrix, Case & Research Intelligence");
  chs["4"] = {
    title: "Chapter 4 — Target Modules Intervention Matrix (AI Case & Research Intelligence)",
    content: await aiWrite(SYS, `${ctx}
${axText}

สร้าง Chapter 4: Target Modules Intervention Matrix (AI Case & Research Intelligence):

กฎเหล็ก: ห้ามสร้างตัวเลข Case Number, Match %, Response Rate, Effect Size, p-value หรือ Sample Size เอง
ต้องอ่านสถานะจาก [REASONING LEDGER] และแสดงตามสถานะ Registry เท่านั้น

1. **AI CASE INTELLIGENCE — ตรวจสอบสถานะ Registry ก่อน**:
   - อ่าน ledger.ai_case_intelligence.registry_status
   - ถ้า registry_status = "UNAVAILABLE": แสดง "[Case Intelligence: UNAVAILABLE. Clinical Case Database not yet connected. Cannot generate case numbers or match percentages.]"
   - ห้ามสร้างตัวเลขเช่น Case #387, Match 92%, Response Rate 89% โดยไม่มีข้อมูลจาก Database จริงเด็ดขาด!

2. **RESEARCH INTELLIGENCE — ตรวจสอบสถานะ Registry ก่อน**:
   - อ่าน ledger.research_database[0].registry_status
   - ถ้า registry_status = "UNAVAILABLE": แสดง "[Research Intelligence: UNAVAILABLE. No verified Study IDs from TSPI Research Registry. Cannot display effect sizes or p-values.]"
   - โมดูลที่รู้จักจาก Official H-Code List: RENAX, IMO, RESHIMUNO, KS, Kerra, Minoza, Plumax, Livoxy, BoVa, Sangvichai
   - อธิบายได้ว่าโมดูลเหล่านี้มีกลไกทางชีววิทยาใด แต่ห้ามใส่ตัวเลขงานวิจัยสมมติ

3. **MODULE MATCHING STATUS — ตรวจสอบ Blocker**:
   - Module Registry ยังไม่มี APPROVED mapping — แสดงสถานะ: "PROVISIONAL CANDIDATE — NOT FOR CLINICAL USE" สำหรับทุก Module
   - ห้ามแสดง Synergy Score, Predicted Response Rate หรือ Module Ranking จนกว่า Registry จะมี APPROVED status

4. **PHYSICIAN-IN-THE-LOOP SIGN-OFF WORKSPACE**:
   - [ ] Approve Plan
   - [ ] Reject Plan
   - [ ] Defer pending additional data (เช่น รอผล Ferritin, Hb typing, Stool analysis)
   - ลงชื่อแพทย์ผู้ประเมิน: ___________________ เลขใบประกอบวิชาชีพ: _________`),
  };

  // ── Chapter 5: Biological Restoration Monitoring & Disease Interpretation ──
  console.log("📝 [Physician] Chapter 5: Biological Restoration Monitoring & Disease Interpretation");
  chs["5"] = {
    title: "Chapter 5 — Clinical Monitoring & Final Disease Interpretation",
    content: await aiWrite(SYS, `${ctx}

สร้าง Chapter 5: Clinical Monitoring & Final Disease Interpretation:
1. **BIOLOGICAL RESTORATION MONITORING**:
   - กำหนดเกณฑ์และแผนการติดตามผลชีวภาพ (CBC, AST, ALT, ALP, GGT, Creatinine, eGFR, Lipid, HbA1c, hs-CRP, Vitamin D) ที่ช่วงเวลา 30, 90, 180 วัน
   - ระบุเกณฑ์หยุดยา/ส่งต่อ (Stopping & Referral Criteria)

2. **DISEASE INTERPRETATION (FINAL TRANSLATION LAYER)**:
   - นำเสนอสรุปการวินิจฉัยโรคตามกรอบแพทย์แผนปัจจุบันเป็น "ชั้นการแปลความหมายปลายทางสำหรับสื่อสารแพทย์" (Final Translation Layer) ย้ำเตือนว่าตัวโรคเป็นเพียงผลลัพธ์จากเครือข่ายชีววิทยาที่เสียสมดุล`),
  };

  return chs;
}

// ═══════════════════════════════════════════════════════════════════
//  👤 PATIENT EDITION — 7 บท (ภาษาเข้าใจง่าย ≤ 10 หน้า ไม่มี Module/Axis/Score)
// ═══════════════════════════════════════════════════════════════════
async function generatePatientReport(ctx: string, ax: any): Promise<Record<string, any>> {
  // P1 Patient Edition — 7 บท ภาษาธรรมชาติ ≤ 10 หน้า (หมอ อนุมัติก่อนปล่อย)
  // ❌ ห้ามใช้ Axis code (A8, A27)
  // ❌ ห้ามใช้ evidence tags ([MEASURED], [HYPOTHESIS])
  // ❌ ห้ามแสดงตัวเลข score (68/100)
  // ❌ ห้ามแสดงชื่อ Module (RENAX, IMO) จนกว่า Registry APPROVED
  // ❌ ห้ามใช้ Footer "for healthcare professionals only"
  // ❌ ห้าม AI บอก terminal phase / end-of-life โดยไม่มี physician approval
  // ✅ Red flag event-driven เฉพาะจาก safety_gate จริง

  const SYS = `คุณคือผู้ช่วยแพทย์ TSPI ที่สื่อสารกับคนไข้โดยตรง
ใช้ภาษาไทยที่อบอุ่น เข้าใจง่าย ไม่ใช้ศัพท์เทคนิคซับซ้อนโดยไม่อธิบาย
ให้กำลังใจและความหวังอย่างสมเหตุสมผล มีความเห็นอกเห็นใจ
ห้ามสั่งการรักษาโดยตรง ให้ระบุว่าต้องปรึกษาแพทย์เสมอ

กฎเหล็กด้านเนื้อหา (P1 Patient Edition Rules):
- ห้ามใช้รหัสแกนชีวภาพ เช่น A8, A27, AXIS_8 เด็ดขาด — อธิบายเป็นภาษาธรรมชาติ
- ห้ามใช้ป้ายกำกับหลักฐาน เช่น [MEASURED], [DERIVED], [HYPOTHESIS] — ใช้คำธรรมชาติแทน
- ห้ามแสดงตัวเลขคะแนน เช่น "68/100" หรือ "คะแนน 75" เด็ดขาด
- ห้ามแสดงชื่อโมดูลใดๆ (RENAX, IMO, RESHIMUNO) จนกว่าทีมแพทย์ยืนยัน
- ห้ามใช้ศัพท์ภายใน เช่น Registry, PROVISIONAL, Ledger, canonical
- ห้ามบอกว่าคนไข้อยู่ใน "ระยะสุดท้าย" หรือ "end-of-life" โดยไม่มีคำสั่งจากแพทย์
- การสื่อสารเรื่องภาวะสงสัยโลหิตจาง Thalassemia: ห้ามใช้คำว่า "ธาลัสซีเมียแฝง" หรือ "iron overload" โดยไม่มีผลยืนยัน ให้ใช้คำว่า "พบรูปแบบที่สงสัย Thalassemia Trait — ต้องยืนยันด้วย Hemoglobin Typing"
- QA Release Gate (ห้ามหลุดเด็ดขาด):
  * ❌ ห้ามมีหัวข้อ "แพทย์อนุมัติแล้ว" หากเนื้อหาระบุว่ายังไม่อนุมัติ
  * ❌ ห้ามมี Footer หรือข้อความ "for healthcare professionals only" ใน Patient Edition
  * ❌ ห้ามมีข้อความภาษาต่างประเทศ (เช่น ภาษาจีน หรือภาษาอังกฤษ) ปะปนในรายงานภาษาไทย
  * ❌ ห้ามระบุว่า "สัญญาณชีพทรงตัว" หากผลแล็บหรือ Vital signs มีภาวะ hypoxemia หรือ hypotension
- Red flag แสดงเฉพาะสิ่งที่เกี่ยวข้องกับเคสจริงเท่านั้น ห้ามแสดง generic checklist ที่ไม่สัมพันธ์กับอาการ

กฎเหล็กด้านรูปแบบ:
- ห้ามใช้ # ## ### ในการทำหัวข้อ
- ห้ามใช้ Emoji หรือสัญลักษณ์รูปภาพ
- ใช้ **ตัวหนา** สำหรับหัวข้อแทน
- ห้ามส่งข้อมูลในรูปแบบ JSON, {}, [] หรือโค้ด

${CLINICAL_SAFETY_RULES}

${TSPI_FUNDAMENTAL_MEDICINE_RULES}`;

  const chs: Record<string, any> = {};

  // ── บท 1: สิ่งที่เราทราบแน่ชัดเกี่ยวกับร่างกายของคุณ ──
  console.log("📝 [Patient] บท 1: สิ่งที่ทราบแน่ชัด");
  chs["1"] = {
    title: "สิ่งที่เราทราบแน่ชัดเกี่ยวกับร่างกายของคุณ",
    content: await aiWrite(SYS, `${ctx}

เขียนเนื้อหา "สิ่งที่เราทราบแน่ชัด" สำหรับคนไข้:
- อธิบายผลการตรวจที่วัดได้จริงและอาการที่ทีมแพทย์ยืนยันแล้ว
- ใช้ภาษาธรรมชาติ เช่น "ผลเลือดพบว่าไตทำงานหนักผิดปกติ" แทนการระบุค่าตัวเลขทางเทคนิค
- ชี้แจงจุดแข็งของร่างกายที่ยังทำงานได้ดีเพื่อสร้างกำลังใจ
- ความยาว: กระชับ ไม่เกิน 1-2 หน้า
- ห้ามใช้รหัส Axis, ตัวเลข score, หรือชื่อ Module เด็ดขาด`),
  };

  // ── บท 2: สิ่งที่เป็นไปได้แต่ยังต้องยืนยัน ──
  console.log("📝 [Patient] บท 2: ยังต้องยืนยัน");
  chs["2"] = {
    title: "สิ่งที่เป็นไปได้แต่ยังต้องยืนยันเพิ่มเติม",
    content: await aiWrite(SYS, `${ctx}

เขียนเนื้อหา "สิ่งที่เป็นไปได้แต่ยังต้องยืนยัน" สำหรับคนไข้:
- อธิบายสิ่งที่ทีมแพทย์สงสัยและกำลังติดตาม โดยยังไม่สรุปเป็นความจริง
- ใช้ภาษาที่ชัดเจนว่า "ยังเป็นการคาดการณ์" เช่น "ทีมแพทย์กำลังติดตามว่า..."
- ระบุว่าต้องการการตรวจอะไรเพิ่มเติมเพื่อยืนยัน
- ความยาว: กระชับ ไม่เกิน 1 หน้า
- ห้ามสรุปว่าคนไข้เป็นโรคหรือมีภาวะใดเด็ดขาด ถ้ายังไม่ยืนยัน`),
  };

  // ── บท 3: สิ่งที่ยังไม่มีข้อมูล ──
  console.log("📝 [Patient] บท 3: ยังไม่มีข้อมูล");
  chs["3"] = {
    title: "สิ่งที่ยังไม่มีข้อมูลเพียงพอ",
    content: await aiWrite(SYS, `${ctx}

เขียนเนื้อหา "สิ่งที่ยังไม่มีข้อมูล" สำหรับคนไข้:
- อธิบายว่ายังมีบางระบบในร่างกายที่ยังไม่มีข้อมูลการตรวจวัด
- ใช้ภาษาที่ไม่น่ากลัว เช่น "ยังไม่มีการตรวจบางอย่าง จึงยังไม่ทราบสถานะ"
- เน้นว่า "ไม่มีข้อมูล ≠ ผิดปกติ" — ยังไม่ได้แปลว่ามีปัญหา
- ความยาว: กระชับ ไม่เกิน 0.5 หน้า`),
  };

  // ── บท 4: สิ่งที่ต้องระวังและแจ้งทีมแพทย์ทันที ──
  console.log("📝 [Patient] บท 4: สัญญาณเตือนและความปลอดภัย");
  chs["4"] = {
    title: "สิ่งที่ต้องระวังและแจ้งทีมแพทย์ทันที",
    content: await aiWrite(SYS, `${ctx}

เขียนเนื้อหา "สิ่งที่ต้องระวัง" สำหรับคนไข้:
- อ่านจาก ledger.safety_gate.global_alerts และ ledger.safety_gate.intervention_eligibility เพื่อระบุข้อระวังเฉพาะเคสนี้
- แสดงเฉพาะ Red Flag ที่เกี่ยวข้องกับอาการของคนไข้จริงๆ เท่านั้น (ไม่ใช่ generic checklist)
- ถ้ามี intervention ที่ HOLD ให้อธิบายเป็นภาษาธรรมชาติ เช่น "ในขณะนี้ยังไม่ควรทานธาตุเหล็กจนกว่าจะตรวจยืนยันก่อน"
- ระบุอาการที่ต้องรีบไปพบแพทย์ฉุกเฉินทันที (เฉพาะที่เกี่ยวข้องกับเคสนี้)
- ห้ามบอกว่า "CONTRAINDICATED ทั้งหมด" ถ้าแค่บางรายการเท่านั้นที่ HOLD
- ความยาว: ชัดเจน ไม่เกิน 1 หน้า`),
  };

  // ── บท 5: สิ่งที่ทีมจะติดตามต่อ ──
  console.log("📝 [Patient] บท 5: แผนติดตาม");
  chs["5"] = {
    title: "สิ่งที่ทีมแพทย์จะติดตามต่อไป",
    content: await aiWrite(SYS, `${ctx}

เขียนเนื้อหา "แผนติดตาม" สำหรับคนไข้:
- อธิบายสิ่งที่ทีมแพทย์จะติดตามในการนัดครั้งต่อไป
- ใช้ภาษาที่อบอุ่นและให้ความมั่นใจ เช่น "ทีมจะดูแลอย่างใกล้ชิด"
- บอกคนไข้ว่าตนเองสามารถช่วยได้อย่างไร เช่น การจดบันทึกอาการ
- ห้ามระบุ threshold ทางเทคนิคหรือตัวเลขแล็บ
- ความยาว: กระชับ ไม่เกิน 0.5 หน้า`),
  };

  // ── บท 6: การตรวจที่อาจช่วยตอบคำถามของคุณ ──
  console.log("📝 [Patient] บท 6: การตรวจเพิ่มเติม");
  chs["6"] = {
    title: "การตรวจเพิ่มเติมที่อาจช่วยตอบคำถามของคุณ",
    content: await aiWrite(SYS, `${ctx}

เขียนเนื้อหา "การตรวจเพิ่มเติม" สำหรับคนไข้:
- แนะนำการตรวจที่จะช่วยตอบคำถามที่ยังไม่ชัดเจน
- อธิบายเป็นภาษาธรรมชาติว่า "ทำไมถึงต้องตรวจ" และ "จะรู้อะไรเพิ่มขึ้น"
- เฉพาะการตรวจที่จะเปลี่ยนแนวทางการดูแลจริงๆ เท่านั้น ห้ามแนะนำเพียงเพราะ "ยังไม่มีข้อมูล"
- ถ้า Mentzer Index < 13 ให้แนะนำตรวจ Hemoglobin Typing + Ferritin เพื่อยืนยัน Thalassemia Trait
- ความยาว: กระชับ ไม่เกิน 1 หน้า`),
  };

  // ── บท 7: แผนที่แพทย์อนุมัติแล้ว + ผู้ติดต่อ ──
  console.log("📝 [Patient] บท 7: แผนที่อนุมัติแล้ว");
  chs["7"] = {
    title: "แผนดูแลสุขภาพที่แพทย์อนุมัติแล้ว",
    content: await aiWrite(SYS, `${ctx}

เขียนเนื้อหา "แผนที่อนุมัติแล้ว" สำหรับคนไข้:
- สรุปสิ่งที่แพทย์อนุมัติให้ทำได้เลย (ถ้ามี) เช่น การปรับวิถีชีวิต
- ถ้าแผนยังอยู่ระหว่างการตรวจสอบ ให้บอกว่า "อยู่ระหว่างการพิจารณาของทีมแพทย์"
- ห้ามแสดงชื่อโมดูลสมุนไพรใดๆ จนกว่าทีมแพทย์จะยืนยันอย่างเป็นทางการ
- ปิดท้ายด้วย:
  * ชื่อ/เบอร์ติดต่อทีมแพทย์ (ถ้ามีข้อมูล)
  * "รายงานนี้เป็นเครื่องมือสื่อสารระหว่างคนไข้และทีมแพทย์ — ไม่ใช่การวินิจฉัยโรค"
  * ช่องลงนามแพทย์ผู้อนุมัติ: ___________________ วันที่: _________`),
  };

  return chs;
}


// ═══════════════════════════════════════════════════════════════════
//  🔬 MULTI-OMICS EDITION — 15 บท (ครบตามต้นแบบ)
// ═══════════════════════════════════════════════════════════════════
async function generateMultiOmicsReport(ctx: string, ax: any, hasOmics: boolean): Promise<Record<string, any>> {
  const SYS = `คุณคือ TSPI Multi-Omics Chief Scientist ผู้เชี่ยวชาญด้าน Genomics, Epigenomics, Microbiome, Metabolomics, Proteomics
วิเคราะห์ข้อมูลหลายชั้น (Multi-Omics) และเชื่อมโยงกับโครงข่ายชีวภาพ 39 แกน 180 Networks 200 Modules
**หลักสำคัญ**: ถ้าไม่มีข้อมูล Omics จริง ให้ระบุว่า "ไม่มีข้อมูล — แนะนำตรวจ [ชื่อการตรวจ]" ห้ามเดาสุ่มข้อมูล
ตอบภาษาไทยทางการแพทย์ขั้นสูง
กฎเหล็กด้านรูปแบบการจัดรูปแบบ (Formatting Rules):
- ห้ามใช้เครื่องหมายแฮชหรือชาร์ป (#, ##, ###) ในการทำหัวข้อเด็ดขาด เพื่อให้ข้อมูลดูเป็นรายงานวิทยาศาสตร์การแพทย์ที่เป็นมาตรฐานสากล
- ห้ามใช้ Emoji หรือสัญลักษณ์รูปภาพ (เช่น ✅ 🚨 ⚠️ 🔴 🟢 🎉) ในเนื้อหาเด็ดขาด ให้ใช้ข้อความหรือคำระบุสถานะแทน
- ให้ใช้ตัวหนาพิมพ์ใหญ่หรือตัวหนาธรรมดาสำหรับหัวข้อต่างๆ แทน เช่น **CHAPTER 1: MULTI-OMICS OVERVIEW**, **1.1 EXECUTIVE SUMMARY** หรือ **GENOMIC EXPRESSION RISK**
- ห้ามส่งข้อมูลในรูปแบบ JSON, เครื่องหมายปีกกา {}, วงเล็บเหลี่ยม [], หรือโค้ดคอมพิวเตอร์ปะปนในเนื้อหารายงานเด็ดขาด ให้เขียนเป็นเนื้อหาบรรยายทางวิทยาศาสตร์ที่มีระเบียบสวยงาม ใช้ตารางมาร์กดาวน์แบบทั่วไปได้

${CLINICAL_SAFETY_RULES}

${TSPI_FUNDAMENTAL_MEDICINE_RULES}`;

  const chs: Record<string, any> = {};
  const axText = buildAxisText(ax);

  if (!hasOmics) {
    console.log("📝 [Multi-Omics] Generating Omics Readiness Report (No Omics data found)");
    
    // Chapter 1: Omics Readiness & Missing Datasets
    chs["1"] = {
      title: "Chapter 1 — Omics Readiness & Missing Datasets",
      content: await aiWrite(SYS, `${ctx}
      
สร้าง Chapter 1: Omics Readiness & Missing Datasets
1. บังคับจัดเรียงย่อหน้าวิเคราะห์หลักทั้งหมดตามรูปแบบ: [Evidence] → [Inference] → [Confidence] → [Action]
2. ตรวจเช็คข้อมูลที่ขาดหายไปอย่างชัดเจน: ไม่มีข้อมูล Genomics (NGS), ไม่มีข้อมูล Gut Microbiome (16S rRNA), ไม่มีข้อมูล Metabolomics, และไม่มีข้อมูล Proteomics/Cytokine Panel
3. ชี้แจงแก่แพทย์ว่ายังขาดชุดข้อมูลการวิเคราะห์หลายชั้น ทำให้ไม่สามารถจัดทำเล่มรายงานแบบละเอียดเชิงลึกได้
4. แนะนำชุดตรวจที่จำเป็นเร่งด่วนตามอาการทางคลินิก (SOAP Note) ของผู้ป่วย`)
    };

    // Chapter 2: Clinical Utility of Omics Testing
    chs["2"] = {
      title: "Chapter 2 — Clinical Utility of Omics Testing",
      content: await aiWrite(SYS, `${ctx}

สร้าง Chapter 2: Clinical Utility of Omics Testing
1. บังคับจัดเรียงย่อหน้าวิเคราะห์หลักทั้งหมดตามรูปแบบ: [Evidence] → [Inference] → [Confidence] → [Action]
2. ระบุเป้าหมายการตรวจแต่ละประเภทที่จะมาช่วยเปิดเผยความจริงทางชีวภาพของคนไข้รายนี้ (เช่น ตรวจ Gut Microbiome เพื่อดูภาวะ Dysbiosis, ตรวจ Pharmacogenomics เพื่อเลี่ยงผลข้างเคียงของยา หรือตรวจ CYP เพื่อดูการขจัดสารพิษของตับ)
3. ระบุความคุ้มค่า (Clinical Utility) และจัดลำดับความสำคัญของชุดตรวจที่แพทย์ควรพิจารณาส่งตรวจก่อน-หลัง`)
    };

    // Chapter 3: Preliminary Phenotype-based Inferences
    chs["3"] = {
      title: "Chapter 3 — Preliminary Phenotype-based Inferences",
      content: await aiWrite(SYS, `${ctx}
${axText}

สร้าง Chapter 3: Preliminary Phenotype-based Inferences
1. บังคับจัดเรียงย่อหน้าวิเคราะห์หลักทั้งหมดตามรูปแบบ: [Evidence] → [Inference] → [Confidence] → [Action]
2. ทำการประเมินเชิงระบบชีวภาพเบื้องต้น (Preliminary Assessment) จากข้อมูลฟีโนไทป์ทางคลินิก ผลเลือดพื้นฐาน และอาการเท่าที่มี
3. เตือนแพทย์อย่างเป็นทางการว่าการประเมินนี้เป็นเพียงสมมติฐานเบื้องต้น [HYPOTHESIS] เท่านั้น และมีข้อจำกัดอย่างสูง ห้ามนำไปจ่ายโมดูลฟื้นฟูขั้นสูงจนกว่าจะได้รับข้อมูลยืนยันจาก Omics หรือแพทย์ตรวจยืนยันอาการ`)
    };

    return chs;
  }

  // บท 1 — Multi-Omics Health Overview
  console.log("📝 [Multi-Omics] บท 1 Overview");
  chs["1"] = {
    title: "บทที่ 1 — Executive Summary: Multi-Omics Health Overview",
    content: await aiWrite(SYS, `${ctx}

สร้างบทที่ 1:

## ภาพรวมสุขภาพหลายชั้น (Multi-Omics Overview)
ข้อมูลที่นำมาวิเคราะห์:
Clinical phenotype | ผลเลือด | Imaging | Genomics/NGS | Epigenomics |
Microbiome | Metabolomics | Proteomics | Pharmacogenomics | Lifestyle data |
TSPI 39 Biological Axes | 180 Biological Networks | 200 Herbal Phytochemical Modules

## สิ่งที่ AI สรุปได้
- ปัญหาหลักของผู้ป่วย
- Network ที่เสียสมดุลมากที่สุด
- Omics ที่สนับสนุนข้อสรุปนั้น
- ความเสี่ยงสำคัญในอนาคต
- โมดูลที่เหมาะสมที่สุด
- สิ่งที่ควรติดตามซ้ำ`),
  };

  // บท 2 — Data Quality & Evidence Confidence
  console.log("📝 [Multi-Omics] บท 2 Data Quality");
  chs["2"] = {
    title: "บทที่ 2 — Data Quality & Evidence Confidence",
    content: await aiWrite(SYS, `${ctx}

สร้างบทที่ 2 — ระดับความมั่นใจของข้อมูล:

**หลักการ**: ป้องกันไม่ให้ AI วิเคราะห์เกินข้อมูลที่มีจริง

## High Confidence (มีหลักฐานหลายชั้นยืนยัน)
ข้อสรุปใดที่ AI มั่นใจสูง เพราะมีผลตรวจยืนยันหลายชั้น

## Moderate Confidence (มีผลเลือดและอาการสนับสนุน)
ข้อสรุปที่อนุมานจากข้อมูลที่มี

## Low Confidence (เป็นสมมติฐาน ต้องตรวจเพิ่ม)
สิ่งที่ AI ยังไม่แน่ใจ และต้องการข้อมูลเพิ่มเติม

## การตรวจที่แนะนำเพื่อเพิ่มความแม่นยำ
ระบุรายการตรวจที่ยังขาดอยู่`),
  };

  // บท 3 — Clinical Phenome Integration
  console.log("📝 [Multi-Omics] บท 3 Clinical Phenome");
  chs["3"] = {
    title: "บทที่ 3 — Clinical Phenome Integration",
    content: await aiWrite(SYS, `${ctx}

สร้างบทที่ 3:

## ข้อมูลทางคลินิกที่ใช้วิเคราะห์
อาการหลัก | โรคประจำตัว | ระยะเวลาป่วย | ประวัติยา | ประวัติการรักษา |
ประวัติผ่าตัด | อาหาร | การนอน | ความเครียด | การขับถ่าย | การออกกำลังกาย

## การเชื่อมโยง Clinical → Biological (Phenome Integration)
Clinical symptoms
  ↓
Organ systems
  ↓
Biological axes
  ↓
Omics evidence
  ↓
Module matching

## Clinical Phenotype Profile
วิเคราะห์ Phenotype ของคนไข้รายนี้ว่าอยู่ในกลุ่มไหน`),
  };

  // บท 4 — Genomics / NGS Report
  console.log("📝 [Multi-Omics] บท 4 Genomics");
  chs["4"] = {
    title: "บทที่ 4 — Genomics / NGS Report",
    content: await aiWrite(SYS, `${ctx}

สร้างบทที่ 4:

ถ้าไม่มีข้อมูล NGS: ระบุ "ไม่มีผล NGS" และแนะนำการตรวจที่ควรทำ
ถ้ามีข้อมูล: วิเคราะห์

## Gene Variants ที่ตรวจพบ
SNPs | Cancer-related mutations | Drug metabolism genes

## Detoxification Genes
CYP1A1, CYP1B1, GSTP1, NQO1, SOD2

## Inflammation Genes
TNF-α, IL-6, IL-10, NF-κB variants

## Lipid Metabolism Genes
APOE, APOB, LDLR variants

## Methylation-Related Genes
MTHFR, COMT, BHMT

## Mitochondrial Function Genes
## Genomic Stability Genes

## AI ตอบคำถาม:
- ยีนใดมีความเสี่ยง?
- ความเสี่ยงนั้นเกี่ยวข้องกับโรคใด?
- ต้องระวังยาอะไร?
- โมดูลใดอาจช่วย biological pathway นั้น?
- ต้องตรวจอะไรเพิ่ม?`),
  };

  // บท 5 — Pharmacogenomics & Drug-Herb Safety
  console.log("📝 [Multi-Omics] บท 5 Pharmacogenomics");
  chs["5"] = {
    title: "บทที่ 5 — Pharmacogenomics & Drug–Herb Safety",
    content: await aiWrite(SYS, `${ctx}

สร้างบทที่ 5:

## CYP450 Enzyme Analysis
- CYP2D6: metabolizes codeine, tamoxifen, antidepressants
- CYP2C19: metabolizes PPIs, clopidogrel, antidepressants
- CYP3A4: metabolizes statins, calcium channel blockers
- SLCO1B1: statin transport → myopathy risk
- NAT2: isoniazid, hydralazine metabolism
- GST, UGT: detoxification enzymes

## Drug Sensitivity Assessment
Statin intolerance risk | Chemotherapy sensitivity | Anticoagulant risk

## Drug–Herb Safety Report
ยาที่ควรระวัง + สมุนไพรที่ควรระวังเมื่อใช้ร่วมกัน
ความเสี่ยงต่อตับ | ต่อไต | เลือดออก | น้ำตาลต่ำ | ความดันต่ำ

**หลักสำคัญ**: โมดูลทุกตัวต้องผ่าน Safety Filter ก่อนเสนอให้แพทย์พิจารณา

(ถ้าไม่มีผล Pharmacogenomics: ระบุและแนะนำการตรวจ)`),
  };

  // บท 6 — Epigenomics
  console.log("📝 [Multi-Omics] บท 6 Epigenomics");
  chs["6"] = {
    title: "บทที่ 6 — Epigenomics Report",
    content: await aiWrite(SYS, `${ctx}

สร้างบทที่ 6:

ถ้าไม่มีข้อมูล Epigenomics: ระบุและแนะนำการตรวจ
ถ้ามีข้อมูล: วิเคราะห์

## Biological Age Analysis
- DNA Methylation Age (Epigenetic Clock)
- Biological Age vs Chronological Age (Gap)
- Immune Age
- Metabolic Age
- Inflammation Age
- Liver Age
- Gut Age

## Methylation Pattern Analysis
Gene expression regulation risk
Methylation imbalance indicators

## Epigenetic Imbalance Map
เชื่อมโยงกับ: การอักเสบเรื้อรัง | การนอน | ความเครียด | อาหาร | ไมโครไบโอม | สารพิษ | การออกกำลังกาย | โมดูลสมุนไพร

## Output
- Biological age gap
- Reversal potential (%)
- Lifestyle priority จาก Epigenomics
- Module priority จาก Epigenomics`),
  };

  // บท 7 — Microbiome Report
  console.log("📝 [Multi-Omics] บท 7 Microbiome");
  chs["7"] = {
    title: "บทที่ 7 — Microbiome Report",
    content: await aiWrite(SYS, `${ctx}

สร้างบทที่ 7:

ถ้าไม่มีผลตรวจ Microbiome: ระบุและแนะนำการตรวจ (Gut Microbiome Analysis)
ถ้ามีข้อมูล: วิเคราะห์

## Alpha Diversity & Beta Diversity
ความหลากหลายของจุลชีพในลำไส้

## Key Bacteria Analysis
- Akkermansia muciniphila
- Bifidobacterium
- Lactobacillus
- Faecalibacterium prausnitzii
- Roseburia intestinalis
- Prevotella
- Bacteroides
- SCFA-producing bacteria
- Pathobionts

## Dysbiosis Index
ระดับความเสียสมดุลของจุลชีพ

## AI ตอบคำถาม:
- ลำไส้มีความหลากหลายดีหรือไม่?
- เชื้อดีต่ำหรือไม่?
- เชื้อก่ออักเสบสูงหรือไม่?
- มีแนวโน้ม SIBO / gut inflammation?
- เกี่ยวข้องกับตับ ภูมิแพ้ ภูมิคุ้มกัน สมอง เมตาบอลิซึมอย่างไร?

## Module Matching จาก Microbiome
Prebiotic modules | Fiber modules | Fermentation modules | Gut barrier modules | Anti-inflammatory gut modules`),
  };

  // บท 8 — Metabolomics
  console.log("📝 [Multi-Omics] บท 8 Metabolomics");
  chs["8"] = {
    title: "บทที่ 8 — Metabolomics Report",
    content: await aiWrite(SYS, `${ctx}

สร้างบทที่ 8:

ถ้าไม่มีผล Metabolomics: ระบุและแนะนำการตรวจ
ถ้ามีข้อมูล: วิเคราะห์

## Short-Chain Fatty Acids (SCFAs)
Butyrate | Acetate | Propionate | Lactate | Succinate

## Bile Acid Profile

## Inflammatory Metabolites
TMAO | Kynurenine | Tryptophan metabolites

## Energy Metabolism Metabolites
Carnitine | Amino acids | Organic acids

## Antioxidant Status
Glutathione-related metabolites | NAD-related metabolites

## Metabolite → Pathway → Network → Disease Mapping
ตัวอย่าง: Butyrate ต่ำ → Gut barrier อ่อน → Inflammation สูง → เลือกโมดูล Fiber/Microbiome

## Module Support จาก Metabolomics
โมดูลที่ช่วยปรับสมดุล Metabolome ของคนไข้`),
  };

  // บท 9 — Proteomics & Cytokine Network
  console.log("📝 [Multi-Omics] บท 9 Proteomics");
  chs["9"] = {
    title: "บทที่ 9 — Proteomics & Cytokine Network Report",
    content: await aiWrite(SYS, `${ctx}

สร้างบทที่ 9:

ถ้าไม่มีผล Proteomics: ระบุและแนะนำการตรวจ
ถ้ามีข้อมูล: วิเคราะห์

## Cytokine Panel Analysis
- IL-6 (pro-inflammatory)
- TNF-alpha
- IL-1β
- IL-10 (anti-inflammatory)
- CRP / hs-CRP

## Growth Factors
- VEGF (vascular)
- IGF-1 (metabolic)
- FGF21 (liver/metabolic)

## Cardiovascular Proteins
- ApoB / ApoA1 ratio
- Albumin
- Complement proteins
- Coagulation proteins

## Protein Signaling Network
Protein signaling → Inflammation network → Immune regulation → Cancer/Metabolic/Vascular risk → Module selection

## Output
- Inflammation signature
- Immune imbalance signature
- Vascular risk signature
- Tissue repair signature`),
  };

  // บท 10 — Mitochondrial & Energy Network
  console.log("📝 [Multi-Omics] บท 10 Mitochondrial");
  chs["10"] = {
    title: "บทที่ 10 — Mitochondrial & Energy Network Report",
    content: await aiWrite(SYS, `${ctx}

สร้างบทที่ 10:

## ข้อมูลที่ใช้วิเคราะห์
Lactate | Pyruvate | ATP-related markers | Organic acids |
Fatigue score | Exercise tolerance | HbA1c | Lipid profile |
CoQ10 status (ถ้ามี) | Oxidative stress markers

## Mitochondrial Function Assessment
- Cellular energy production capacity
- Mitochondrial stress level
- Fat oxidation efficiency
- Glucose oxidation balance
- Redox balance (Oxidative stress)
- Autophagy status
- Recovery capacity

## Energy Metabolism Analysis
Metabolic flexibility | Exercise adaptation capacity

## Module Recommendations สำหรับ Mitochondria
โมดูลที่สนับสนุน:
- Mitochondrial energy production
- Autophagy activation
- Redox balance
- Metabolic flexibility
- Exercise adaptation`),
  };

  // บท 11 — Integrated 39 Axes Mapping
  console.log("📝 [Multi-Omics] บท 11 Integrated 39 Axes");
  chs["11"] = {
    title: "บทที่ 11 — Integrated 39 Biological Axes Mapping",
    content: await aiWrite(SYS, `${ctx}
${axText}

สร้างบทที่ 11 — รวมข้อมูลทั้งหมดแปลงเป็นคะแนน 39 แกน:

รวม: Clinical + Labs + Imaging + Genomics + Epigenomics + Microbiome + Metabolomics + Proteomics

สำหรับแต่ละแกน ระบุ:
- คะแนน 0–100
- ระดับผิดปกติ (Normal/Mild/Moderate/Severe)
- หลักฐานที่ใช้ (Labs / Omics ที่สนับสนุน)
- ระดับความมั่นใจ (High/Moderate/Low)
- โมดูลที่เกี่ยวข้อง
- Biomarker ที่ควรติดตาม`),
  };

  // บท 12 — 180 Networks Mapping
  console.log("📝 [Multi-Omics] บท 12 180 Networks");
  chs["12"] = {
    title: "บทที่ 12 — 180 Living Biological Networks Mapping",
    content: await aiWrite(SYS, `${ctx}
${axText}

สร้างบทที่ 12:

## Network Heatmap (Multi-Omics Informed)
จัดอันดับทุก Network จากข้อมูล Multi-Omics:

Networks ตัวอย่าง:
- Gut–Liver Axis | Gut–Brain Axis | Immune–Inflammatory Network
- Mitochondrial Network | Redox Network | Lipid Network
- Detoxification Network | Autophagy Network
- Genomic Stability Network | Microvascular Network

## Disease Network Map
Network ใดเสียมากที่สุด | ผลักโรค | ควรฟื้นฟูก่อน

## Recovery Network Map
Network ใดกำลังตอบสนองดี | ฟื้นตัว

## Root Network Drivers
Top 10 Network Drivers ที่ผลักโรคมากที่สุด

## Network Propagation Map
เส้นทาง: Root Network → Chain → Clinical Disease

## Network–Module Matching
Network ใดตอบสนองต่อโมดูลใด`),
  };

  // บท 13 — Herbal Module Multi-Omics Matching
  console.log("📝 [Multi-Omics] บท 13 Module Matching");
  chs["13"] = {
    title: "บทที่ 13 — Herbal Module Multi-Omics Matching Engine",
    content: await aiWrite(SYS, `${ctx}

สร้างบทที่ 13 — เชื่อมมัลติโอมิคผู้ป่วยกับมัลติโอมิคโมดูลสมุนไพร:

ข้อมูลโมดูลที่ AI ใช้:
Phytochemical profile | Target proteins | Gene expression effects |
Pathway enrichment | Microbiome effects | Metabolomic effects |
Anti-inflammatory profile | Mitochondrial effects | Safety profile | Clinical outcomes

## การจับคู่โมดูลสำหรับแต่ละรายการ (ตาม MODULE REGISTRY GATE — ห้ามให้คะแนนหรือจัดอันดับเป็นตัวเลขเด็ดขาด):
- ระบุ **สถานะ**: "PROVISIONAL CANDIDATE — NOT FOR CLINICAL USE" ทุกโมดูล (Module Registry ยังไม่มี mapping_status = APPROVED)
- อธิบาย **กลไกเชิงคุณภาพ** ว่าโมดูลนี้เชื่อมโยงกับ Axis ที่ผิดปกติและ Omics pathway ใดบ้าง โดยไม่ใช้ตัวเลขคะแนน (ห้ามใช้คำว่า Match Score, Coverage Score, Reversal Score, Synergy Score หรือ Ranking)
- ระบุ **สถานะความปลอดภัย** ตาม Safety Gate เท่านั้น: PASS / PASS_WITH_MONITORING / HOLD / CONTRAINDICATED / INSUFFICIENT_SAFETY_DATA (ห้ามใช้ตัวเลข เช่น "ความปลอดภัย 98/100")

## Top Modules แสดงเหตุผลแบบ TSPI Format:
Module X เหมาะกับผู้ป่วยเพราะ:
- ครอบคลุม [Network] ที่เสียสมดุล
- สนับสนุน [Omics pathway]
- ลด [inflammatory/metabolic signature]
- Case Intelligence: ห้ามอ้างว่ามีผู้ป่วยคล้ายกันตอบสนองดี เว้นแต่มี query log จาก Clinical Database จริง — หากไม่มีให้ระบุ "[Case Intelligence: UNAVAILABLE. Clinical Case Database not yet connected.]"`),
  };

  // บท 14 — Personalized Network Intervention Plan
  console.log("📝 [Multi-Omics] บท 14 Intervention Plan");
  chs["14"] = {
    title: "บทที่ 14 — Personalized Network Intervention Plan",
    content: await aiWrite(SYS, `${ctx}

สร้างบทที่ 14 — แผนแทรกแซง 3 ระยะ:

## Phase 1: Stabilization (สัปดาห์ 1–4)
เป้าหมาย: ลดอาการรุนแรง ลดการอักเสบ ปรับขับถ่าย ลด disease network burden
- Module list (Tier 1)
- ขนาดตามแพทย์สั่ง
- Lifestyle plan
- Exercise plan
- Food plan
- Monitoring biomarkers
- Criteria for adjustment

## Phase 2: Restoration (เดือน 2–4)
เป้าหมาย: ฟื้นฟู microbiome, mitochondria, gut barrier, liver metabolism
- Module list
- Lifestyle plan
- Exercise plan
- Food plan
- Monitoring biomarkers
- Criteria for adjustment

## Phase 3: Resilience (เดือน 5–12)
เป้าหมาย: ลดการพึ่งพา สร้าง biological resilience ป้องกันโรคกลับมา
- Module list (maintenance)
- Lifestyle plan
- Exercise plan
- Food plan
- Monitoring biomarkers`),
  };

  // บท 15 — Prognosis, Risk & Follow-up
  console.log("📝 [Multi-Omics] บท 15 Prognosis & Risk");
  chs["15"] = {
    title: "บทที่ 15 — Prognosis, Risk Prediction & Follow-up Omics Roadmap",
    content: await aiWrite(SYS, `${ctx}

สร้างบทที่ 15:

## การพยากรณ์โรคและความเสี่ยง

### ถ้าไม่เปลี่ยนพฤติกรรม:
- ความเสี่ยง 1 ปี
- ความเสี่ยง 3 ปี
- ความเสี่ยง 5 ปี

### ถ้าทำตามแผนฟื้นฟู TSPI:
- ผลลัพธ์ที่คาดหวัง 1/3/5 ปี

## Disease Risk Analysis
Metabolic disease | Fatty liver | Diabetes | CKD | Cardiovascular disease | Cancer risk | Cognitive decline | Autoimmune activation | Frailty | Sarcopenia

## Follow-up Testing Roadmap

### Essential (ทุกคน)
CBC | Liver | Kidney | Lipid | HbA1c | hs-CRP | Urinalysis

### Advanced (แนะนำ)
Microbiome | Vitamin D | Ferritin | B12 | Homocysteine | Insulin | HOMA-IR

### Precision (สำหรับผู้ป่วย Multi-Omics)
Metabolomics update | Proteomics | Epigenetic age | NGS update | Pharmacogenomics | Cytokine panel

## FINAL OUTPUT — Top 5 Summary
**Top 5 Risks**: ความเสี่ยงหลัก 5 อันดับ
**Top 5 Root Drivers**: ตัวขับดันโรค 5 อันดับ
**Top 5 Modules**: โมดูลที่แนะนำ 5 อันดับ
**Top 5 Lifestyle Priorities**: สิ่งที่ต้องเปลี่ยนในวิถีชีวิต 5 อันดับ
**Top 5 Tests to Follow**: ผลตรวจที่ต้องติดตาม 5 อันดับ

---
**หลักการสำคัญของ TSPI Multi-Omics Report**:
Patient Multi-Omics → Biological Pathways → 180 Networks → 39 Axes → Disease Network → Herbal Module Multi-Omics → Network Matching → Personalized Plan (Pending Physician Review)

---
*รายงานนี้เป็นเครื่องมือช่วยวิเคราะห์เชิงระบบชีวภาพ ไม่ใช่การวินิจฉัยแทนแพทย์
การใช้โมดูลสมุนไพร ขนาดรับประทาน การปรับยา หรือการหยุดยาใดๆ ต้องอยู่ภายใต้การพิจารณาของแพทย์หรือผู้เชี่ยวชาญที่ดูแลผู้ป่วยเท่านั้น*`),
  };

  return chs;
}

// ═══════════════════════════════════════════════════════════════════
//  🚀 MAIN API HANDLER
// ═══════════════════════════════════════════════════════════════════
export async function POST(req: Request) {
  try {
    const authHeader = req.headers.get("authorization") || "";
    const body = await req.json();
    const { patientId, patientData, reportType } = body;

    if (!patientId || !patientData) {
      return NextResponse.json({ error: "Missing required patient data" }, { status: 400 });
    }

    console.log(`\n${"═".repeat(60)}`);
    console.log(`🏥 TSPI Report (Streaming): Patient=${patientId} | Edition=${reportType}`);
    console.log(`${"═".repeat(60)}`);

    // Step 1: Get Axis Scores + Reasoning Ledger — reuse a same-day, same-input
    // snapshot across editions so Physician/Patient/Multi-Omics always score identically
    const inputsHash = computeInputsHash(patientData);
    const patientRecord = await fetchPatientRecord(patientId, authHeader);
    const cachedSnapshot = patientRecord?.extra_data?.latest_analysis_snapshot;
    const today = new Date().toISOString().slice(0, 10);

    let ledger: any;
    let axisScores: any;
    let mentzerIndex: number | null;

    if (cachedSnapshot && cachedSnapshot.inputsHash === inputsHash && cachedSnapshot.computedAt?.slice(0, 10) === today) {
      console.log(`♻️ Reusing cached Reasoning Ledger (run ${cachedSnapshot.runId}) — inputs unchanged since last computation today`);
      ledger = cachedSnapshot.ledger;
      axisScores = cachedSnapshot.axisScores;
      mentzerIndex = cachedSnapshot.mentzerIndex;
    } else {
      const djangoRes = await getDjangoAxisScores(patientId, patientData, authHeader);
      axisScores = djangoRes.scores;
      mentzerIndex = djangoRes.mentzer_index;
      console.log(`✅ Axis Scores: ${Object.keys(axisScores).length} axes loaded`);

      ledger = buildReasoningLedger(patientData, axisScores, mentzerIndex, {
        three_keys: djangoRes.three_keys,
        nine_restoration_steps: djangoRes.nine_restoration_steps,
        module_registry_status: djangoRes.module_registry_status
      });

      // ── P0-4.13: Invariant Validation — block generation ถ้า Ledger ผิด ──
      // ต้อง pass ก่อน persist snapshot และก่อน generate report ทุกครั้ง
      validateAnalysisRecord(ledger);

      try {
        await updatePatientExtraData(patientId, authHeader, {
          ...(patientRecord?.extra_data || {}),
          latest_analysis_snapshot: {
            runId: `run_${Date.now()}`,
            inputsHash,
            ledger,
            axisScores,
            mentzerIndex,
            computedAt: new Date().toISOString()
          }
        });
      } catch (snapshotErr) {
        console.warn("⚠️ Failed to persist analysis snapshot (report generation continues):", snapshotErr);
      }
    }

    // Step 2: Build patient context
    const patientCtx = buildContext(patientData, axisScores, mentzerIndex, ledger);
    const edition = (reportType || "physician").toLowerCase();

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        const enqueueChunk = (chunk: string) => {
          controller.enqueue(encoder.encode(JSON.stringify({ type: "content_chunk", chunk }) + "\n"));
        };
        const onChapterStart = (title: string) => {
          controller.enqueue(encoder.encode(JSON.stringify({ type: "chapter_start", title }) + "\n"));
        };
        const onChapterComplete = (title: string, content: string) => {
          controller.enqueue(encoder.encode(JSON.stringify({ type: "chapter_complete", title, content }) + "\n"));
        };

        try {
          controller.enqueue(encoder.encode(JSON.stringify({ type: "start", edition }) + "\n"));

          let chapters: Record<string, any> = {};

          await reportStreamStorage.run({ enqueueChunk, onChapterStart, onChapterComplete }, async () => {
            if (edition === "multi-omics") {
              const pd = patientData || {};
              const hasGenomics = pd.genomics && Object.keys(pd.genomics).length > 0;
              const hasMicrobiome = pd.microbiome && Object.keys(pd.microbiome).length > 0;
              const hasProteomics = pd.proteomics && Object.keys(pd.proteomics).length > 0;
              const hasOmics = !!(hasGenomics || hasMicrobiome || hasProteomics);
              chapters = await generateMultiOmicsReport(patientCtx, axisScores, hasOmics);
            } else if (edition === "patient") {
              chapters = await generatePatientReport(patientCtx, axisScores);
            } else {
              chapters = await generatePhysicianReport(patientCtx, axisScores);
            }
          });

          // Build full Markdown report
          const editionLabel =
            edition === "patient"
              ? "TSPI PATIENT BIOLOGICAL NETWORK REPORT™\nYour Personalized Health Restoration Blueprint"
              : edition === "multi-omics"
              ? "TSPI Multi-Omics Biological Network Report™\nScope for AI-Generated Patient & Physician Report"
              : "TSPI Precision Biological Network Intelligence Report™\nPhysician Edition — Version 1.0";

          let fullReport = `# ${editionLabel}\n\n`;
          fullReport += `---\n*Patient ID: ${patientId} | Generated: ${new Date().toLocaleString("th-TH")}*\n\n`;
          fullReport += `---\n\n`;

          const chaptersArray: Array<{ chapterTitle: string; content: string }> = [];
          for (const [, ch] of Object.entries(chapters)) {
            fullReport += `## ${ch.title}\n\n${ch.content}\n\n---\n\n`;
            chaptersArray.push({
              chapterTitle: ch.title,
              content: ch.content
            });
          }

          fullReport += `\n---\n**ข้อความจำกัดความรับผิดชอบ**\nรายงานนี้เป็นเครื่องมือช่วยวิเคราะห์เชิงระบบชีวภาพ ไม่ใช่การวินิจฉัยแทนแพทย์\nการใช้โมดูลสมุนไพร ขนาดรับประทาน การปรับยา หรือการหยุดยาใดๆ ต้องอยู่ภายใต้การพิจารณาของแพทย์หรือผู้เชี่ยวชาญที่ดูแลผู้ป่วยเท่านั้น`;

          const chapterCount = Object.keys(chapters).length;
          console.log(`\n✅ Report Complete (Streaming): ${chapterCount} chapters | Edition: ${edition}`);

          controller.enqueue(encoder.encode(JSON.stringify({
            type: "complete",
            reportId: `TSPI-${patientId}-${Date.now()}`,
            fullReport,
            chapters: chaptersArray,
            biologicalScores: axisScores,
            reasoningLedger: ledger,
            edition: reportType,
            chaptersCount: chapterCount,
          }) + "\n"));

          controller.close();
        } catch (error: any) {
          console.error("❌ TSPI Streaming Report Error:", error);
          controller.enqueue(encoder.encode(JSON.stringify({
            type: "error",
            message: error.message || "TSPI Report Engine failed"
          }) + "\n"));
          controller.close();
        }
      }
    });

    return new Response(stream, {
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
      }
    });
  } catch (error: any) {
    console.error("❌ TSPI Report Error:", error);
    return NextResponse.json(
      { error: "TSPI Report Engine failed", details: error.message },
      { status: 500 }
    );
  }
}
