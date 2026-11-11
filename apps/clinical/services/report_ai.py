"""
AI Authoring & Grounded Narrative Synthesis Service for 3 Precision Report Editions (EP 6):
1. Physician Edition (5 Chapters, Evidence Tags, Ontology-locked Systems Reasoning)
2. Patient Edition (7 Chapters, Warm Natural Thai, Zero Internal Codes/Raw Scores)
3. Multi-Omics Edition (Smart Gate: 3 Readiness Chapters if no Omics data, or Deep Omics Profiling)
"""

import logging
from typing import Any, Dict, List, Optional
import httpx
from django.conf import settings
from django.utils import timezone

from clinical.engine import TspiClinicalEngine
from clinical.invariants import CANONICAL_12_DOMAINS, CANONICAL_39_AXES, ClinicalInvariantValidator

logger = logging.getLogger('tspi.clinical')


class PrecisionReportAIWriter:
    """
    เครื่องยนต์ AI เขียนรายงาน 3 ฉบับ (แพทย์, คนไข้, Multi-Omics) จากเวชระเบียนจริง
    """

    @classmethod
    def extract_patient_clinical_snapshot(cls, patient, scores_dict: Dict[int, Optional[int]], doctor_notes: str = "") -> Dict[str, Any]:
        """รวบรวมข้อมูลเวชระเบียนจริง (SOAP, Vitals, Labs, 39 Axes, Modules, Omics) แบบ Single Source of Truth"""
        latest_soap = patient.histories.filter(is_deleted=False).order_by('-visit_date', '-id').first()
        vitals = latest_soap.vitals if (latest_soap and isinstance(latest_soap.vitals, dict)) else {}

        extra = patient.extra_data if isinstance(patient.extra_data, dict) else {}
        biomarkers_raw = extra.get('biomarkers') if isinstance(extra.get('biomarkers'), dict) else {}
        labs_list = []
        abnormal_labs = []
        for k, m in biomarkers_raw.items():
            if isinstance(m, dict) and 'value' in m:
                entry = {
                    'code': k,
                    'name': m.get('name') or k,
                    'value': m.get('value'),
                    'unit': m.get('unit', ''),
                    'is_abnormal': bool(m.get('is_abnormal')),
                    'target_axis': m.get('target_axis', ''),
                }
                labs_list.append(entry)
                if entry['is_abnormal']:
                    abnormal_labs.append(entry)

        omics_data = extra.get('omics') if isinstance(extra.get('omics'), dict) else {}
        has_omics = bool(
            omics_data and any(
                omics_data.get(k) for k in ('genomics', 'microbiome', 'metabolomics', 'proteomics', 'ngs')
            )
        )

        # Dysfunctional & Assessed Axes
        all_axes = TspiClinicalEngine.get_all_axes()
        assessed_axes = []
        dysfunctional_axes = []
        unassessed_count = 0
        for ax in all_axes:
            ax_id = ax.get('axis_id')
            sc = scores_dict.get(ax_id)
            if sc is None:
                unassessed_count += 1
            else:
                item = {
                    'axis_id': ax_id,
                    'name': CANONICAL_39_AXES.get(ax_id, ax.get('name')),
                    'domain_title': ax.get('domain_title'),
                    'score': int(sc),
                }
                assessed_axes.append(item)
                if int(sc) >= 60:
                    dysfunctional_axes.append(item)
        dysfunctional_axes.sort(key=lambda x: x['score'], reverse=True)

        domain_scores = TspiClinicalEngine.calculate_domain_scores(scores_dict)
        matched_modules = TspiClinicalEngine.match_therapeutic_recommendations(dysfunctional_axes, limit=6) if dysfunctional_axes else []

        # Approved protocols / whitelist
        approved_protocols = extra.get('approved_protocols') if isinstance(extra.get('approved_protocols'), list) else []

        return {
            'patient': patient,
            'latest_soap': latest_soap,
            'vitals': vitals,
            'labs_list': labs_list,
            'abnormal_labs': abnormal_labs,
            'omics_data': omics_data,
            'has_omics': has_omics,
            'assessed_axes': assessed_axes,
            'dysfunctional_axes': dysfunctional_axes,
            'unassessed_count': unassessed_count,
            'domain_scores': domain_scores,
            'matched_modules': matched_modules,
            'approved_protocols': approved_protocols,
            'doctor_notes': doctor_notes,
        }

    @classmethod
    def _build_prompt_summary(cls, snap: Dict[str, Any]) -> str:
        p = snap['patient']
        soap = snap['latest_soap']
        v = snap['vitals']

        vitals_str = ", ".join(filter(None, [
            f"BP {v.get('bp_systolic')}/{v.get('bp_diastolic')} mmHg" if v.get('bp_systolic') else "",
            f"HR {v.get('pulse')} bpm" if v.get('pulse') else "",
            f"Temp {v.get('temperature')} C" if v.get('temperature') else "",
            f"BMI {v.get('bmi')}" if v.get('bmi') else "",
        ])) or "ยังไม่ได้บันทึกสัญญาณชีพ"

        labs_str = ", ".join(
            f"{l['name']}: {l['value']} {l['unit']} ({'ผิดปกติ' if l['is_abnormal'] else 'ปกติ'})"
            for l in snap['labs_list']
        ) or "ยังไม่มีผลตรวจแล็บชีวเคมี"

        dys_str = ", ".join(
            f"AXIS_{ax['axis_id']} ({ax['name']}): {ax['score']}/100"
            for ax in snap['dysfunctional_axes'][:12]
        ) or "ไม่พบแกนที่มีคะแนน >= 60"

        mod_str = ", ".join(
            f"{m.get('code')} ({m.get('name')})"
            for m in snap['matched_modules']
        ) or "ยังไม่มีโมดูลที่แนะนำ"

        return (
            f"ผู้ป่วย: {p.full_name} (HN: {p.hn}), อายุ {p.age or '-'} ปี, เพศ {p.get_gender_display()}\n"
            f"ประวัติแพ้ยา/อาหาร: {p.allergies or 'ไม่มี'}\n"
            f"ยาประจำตัว: {p.current_medications or 'ไม่ได้ระบุ'}\n"
            f"สัญญาณชีพ: {vitals_str}\n"
            f"SOAP Subjective: {soap.subjective if soap and soap.subjective else 'ไม่ได้บันทึก'}\n"
            f"SOAP Objective: {soap.objective if soap and soap.objective else 'ไม่ได้บันทึก'}\n"
            f"SOAP Assessment: {soap.assessment if soap and soap.assessment else 'ไม่ได้บันทึก'}\n"
            f"SOAP Plan: {soap.plan if soap and soap.plan else 'ไม่ได้บันทึก'}\n"
            f"ผลแล็บชีวเคมี: {labs_str}\n"
            f"จำนวนแกนที่ประเมินแล้ว: {len(snap['assessed_axes'])}/39 แกน (ยังไม่ประเมิน {snap['unassessed_count']} แกน)\n"
            f"แกนที่ผิดปกติ (>= 60): {dys_str}\n"
            f"โมดูลพฤกษเคมีที่จับคู่ได้: {mod_str}\n"
            f"ข้อมูล Omics: {snap['omics_data'] if snap['has_omics'] else 'ไม่มีข้อมูล NGS/Microbiome/Metabolomics'}"
        )

    @classmethod
    def compose_three_editions(
        cls,
        patient,
        scores_dict: Dict[int, Optional[int]],
        doctor_summary: str = "",
        use_ai: bool = True,
    ) -> Dict[str, Any]:
        """
        สร้างเนื้อหาทั้ง 3 ฉบับ (physician, patient, multiomics) พร้อม Metadata
        พยายามเรียก FastAPI AI Service ก่อน หากไม่พร้อมใช้จะสังเคราะห์จาก Grounded Snapshot ทันที
        """
        snap = cls.extract_patient_clinical_snapshot(patient, scores_dict, doctor_notes=doctor_summary)
        summary_text = cls._build_prompt_summary(snap)

        editions_data = None
        generated_by = "grounded_deterministic"

        if use_ai:
            ai_url = getattr(settings, 'AI_SERVICE_URL', '').rstrip('/')
            if ai_url:
                try:
                    headers = {"Content-Type": "application/json"}
                    token = getattr(settings, 'INTERNAL_API_TOKEN', '')
                    if token:
                        headers["X-Internal-Token"] = token
                    resp = httpx.post(
                        f"{ai_url}/api/v1/reports/compose",
                        json={
                            "patient_summary": summary_text,
                            "has_omics": snap['has_omics'],
                            "doctor_notes": doctor_summary,
                        },
                        headers=headers,
                        timeout=25.0,
                    )
                    if resp.status_code == 200:
                        payload = resp.json()
                        if payload.get("success") and isinstance(payload.get("editions"), dict):
                            editions_data = payload["editions"]
                            generated_by = "ai_gateway"
                except Exception as exc:
                    logger.info(f"[PrecisionReportAIWriter] Using grounded synthesis fallback: {exc}")

        if not editions_data:
            editions_data = cls._build_grounded_editions(snap)

        # บังคับ Sanitize เนื้อหาฉบับคนไข้เสมอตาม Pillar 15 Patient Safety Barrier
        sanitized_patient_chapters = []
        for ch in editions_data.get('patient', []):
            if not isinstance(ch, dict):
                continue
            sanitized_patient_chapters.append({
                'title': ClinicalInvariantValidator.sanitize_patient_prose(str(ch.get('title', ''))),
                'content': ClinicalInvariantValidator.sanitize_patient_prose(str(ch.get('content', ''))),
            })

        return {
            'physician': editions_data.get('physician', []),
            'patient': sanitized_patient_chapters,
            'multiomics': editions_data.get('multiomics', []),
            'omics_available': snap['has_omics'],
            'generated_by': generated_by,
            'generated_at': timezone.now().isoformat(),
        }

    @classmethod
    def _build_grounded_editions(cls, snap: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
        """สร้างเนื้อหาทั้ง 3 ฉบับจากข้อมูล EMR จริงแบบ Deterministic (Zero Hallucination)"""
        p = snap['patient']
        soap = snap['latest_soap']
        v = snap['vitals']
        dys = snap['dysfunctional_axes']
        labs = snap['labs_list']
        abn_labs = snap['abnormal_labs']
        mods = snap['matched_modules']
        doc_notes = snap['doctor_notes']

        vitals_line = ", ".join(filter(None, [
            f"ความดัน {v.get('bp_systolic')}/{v.get('bp_diastolic')} mmHg" if v.get('bp_systolic') else "",
            f"ชีพจร {v.get('pulse')} ครั้ง/นาที" if v.get('pulse') else "",
            f"อุณหภูมิ {v.get('temperature')} °C" if v.get('temperature') else "",
            f"BMI {v.get('bmi')}" if v.get('bmi') else "",
        ])) or "[NOT_AVAILABLE] ยังไม่ได้บันทึกสัญญาณชีพ"

        # ---------------- 1. PHYSICIAN EDITION (5 Chapters) ----------------
        top_dys_text = (
            "\n".join(f"- [DERIVED] AXIS_{ax['axis_id']} ({ax['name']} — {ax['domain_title']}): คะแนน {ax['score']}/100" for ax in dys[:8])
            if dys else "- [DERIVED] ไม่พบแกนชีวภาพที่มีคะแนนความผิดปกติ >= 60 จากแกนที่ประเมินแล้ว"
        )
        labs_text = (
            "\n".join(f"- [MEASURED] {l['name']}: {l['value']} {l['unit']} ({'ผิดปกติ' if l['is_abnormal'] else 'ปกติ'})" for l in labs)
            if labs else "- [NOT_AVAILABLE] ยังไม่มีบันทึกผลตรวจแล็บชีวเคมีในเวชระเบียน"
        )
        mods_text = (
            "\n".join(f"- {m.get('code')} ({m.get('name')}): {(m.get('description') or '')[:160]}" for m in mods)
            if mods else "- [NOT_AVAILABLE] ยังไม่มีโมดูลที่จับคู่ได้ กรุณาตรวจประเมิน 39 แกนเพิ่มเติม"
        )

        physician_chapters = [
            {
                'title': 'Chapter 1 — TSPI Biological State Summary & Red Flag Safety Screening',
                'content': (
                    f"[CLINICAL_INFERENCE] ผู้ป่วย {p.full_name} (HN: {p.hn}, อายุ {p.age or '-'} ปี, เพศ {p.get_gender_display()}) "
                    f"ได้รับการประเมิน 39 แกนแล้ว {len(snap['assessed_axes'])}/39 แกน (รอตรวจเพิ่มเติม {snap['unassessed_count']} แกน)\n"
                    f"- สัญญาณชีพ: {vitals_line}\n"
                    f"- การคัดกรองความปลอดภัย (Allergies): {p.allergies or 'ไม่พบประวัติแพ้ยาที่ระบุ'} | ยาประจำตัว: {p.current_medications or 'ไม่ได้ระบุ'}\n"
                    f"{'- ความเห็นแพทย์ผู้ตรวจ: ' + doc_notes if doc_notes else ''}"
                ).strip(),
            },
            {
                'title': 'Chapter 2 — Clinical Evidence Integration (SOAP & Lab Biomarkers)',
                'content': (
                    f"[CLINICAL_INFERENCE] ประวัติอาการสำคัญ (SOAP Subjective): {soap.subjective if soap and soap.subjective else '[NOT_AVAILABLE] ยังไม่มีบันทึกซักประวัติ SOAP'}\n"
                    f"[MEASURED] ผลการตรวจร่างกายและห้องปฏิบัติการ:\n{labs_text}"
                ),
            },
            {
                'title': 'Chapter 3 — 39 Biological Axes & Systems Coupling Reasoning',
                'content': (
                    f"สรุปแกนชีวภาพที่พบความผิดปกติระดับเซลล์ (เรียงตามความรุนแรง):\n{top_dys_text}\n"
                    f"หมายเหตุ: แกนชีวภาพที่ยังไม่มีผลตรวจ ({snap['unassessed_count']} แกน) ถูกคงสถานะเป็น [NOT_AVAILABLE] ตามกฎ Ontology Lock"
                ),
            },
            {
                'title': 'Chapter 4 — Target Modules Intervention Matrix (Fail-Closed Safety)',
                'content': (
                    f"โมดูลพฤกษเคมีที่ระบบจับคู่ได้จากแกนชีวภาพที่ผิดปกติ (ต้องผ่านการตรวจสอบปฏิกิริยาระหว่างยากับแพทย์ก่อนสั่งจ่าย):\n{mods_text}"
                ),
            },
            {
                'title': 'Chapter 5 — Clinical Monitoring & Follow-up Protocol',
                'content': (
                    f"แผนการติดตามผลทางคลินิก: {soap.plan if soap and soap.plan else 'นัดหมายประเมินอาการและผลแล็บซ้ำใน 4–8 สัปดาห์ เพื่อประเมินการฟื้นตัวของแกนชีวภาพเป้าหมาย'}\n"
                    f"รายงานนี้ใช้สนับสนุนการตัดสินใจของแพทย์ (Pillar 15 CDSS) ไม่ทดแทนการตรวจวินิจฉัยของแพทย์ผู้รักษา"
                ),
            },
        ]

        # ---------------- 2. PATIENT EDITION (7 Chapters, Sanitized Natural Thai) ----------------
        domain_focus = [
            d['title'] for d in snap['domain_scores']
            if d.get('avg_score') is not None and d['avg_score'] >= 60
        ]
        patient_known = (
            f"จากการตรวจประเมินสุขภาพเชิงลึกของท่าน พบประเด็นที่ทีมแพทย์ให้ความสำคัญเป็นพิเศษในกลุ่มระบบ: {', '.join(domain_focus[:4])}."
            if domain_focus
            else "ข้อมูลสุขภาพเบื้องต้นของท่านได้รับการบันทึกเข้าสู่ระบบของคลินิกเรียบร้อยแล้ว ขณะนี้ยังไม่พบสัญญาณความเสื่อมรุนแรงจากข้อมูลที่มีอยู่"
        )
        patient_labs_note = (
            f"โดยผลตรวจทางห้องปฏิบัติการล่าสุดพบค่าที่ควรดูแลเพิ่มเติม ได้แก่ {', '.join(l['name'] for l in abn_labs[:5])}"
            if abn_labs
            else "หากท่านมีผลตรวจเลือดเพิ่มเติม สามารถนำมาให้ทีมแพทย์ประเมินร่วมกันได้ในการนัดครั้งถัดไป"
        )

        patient_chapters = [
            {
                'title': '1. สิ่งที่เราทราบแน่ชัดเกี่ยวกับร่างกายของคุณ',
                'content': f"{patient_known} {patient_labs_note}".strip(),
            },
            {
                'title': '2. สิ่งที่เป็นแนวโน้มและทีมแพทย์กำลังดูแลเพิ่มเติม',
                'content': (
                    f"อาการที่ท่านได้เล่าให้ทีมแพทย์ฟัง ({soap.subjective[:180] if soap and soap.subjective else 'ประวัติสุขภาพทั่วไป'}) "
                    f"ช่วยให้แพทย์เชื่อมโยงภาพรวมการทำงานของร่างกาย ทั้งด้านพลังงานระดับเซลล์ การย่อยและดูดซึม และการอักเสบสะสม เพื่อวางแผนดูแลให้ตรงจุดที่สุด"
                ),
            },
            {
                'title': '3. ข้อมูลที่ยังรอการตรวจยืนยันเพิ่มเติม',
                'content': (
                    f"ปัจจุบันยังมีข้อมูลสุขภาพบางส่วน (จำนวน {snap['unassessed_count']} มิติย่อย) ที่ยังไม่ได้ทำการตรวจวัดโดยตรง "
                    f"ทีมแพทย์จึงยังไม่สรุปผลในส่วนดังกล่าวจนกว่าจะได้ผลตรวจที่ชัดเจน เพื่อความปลอดภัยสูงสุดของท่าน"
                ),
            },
            {
                'title': '4. อาการสำคัญที่ควรสังเกตและแจ้งทีมแพทย์ทันที',
                'content': (
                    f"{'เนื่องจากท่านมีประวัติแพ้: ' + p.allergies + ' โปรดแจ้งทีมแพทย์และเภสัชกรทุกครั้งก่อนรับผลิตภัณฑ์หรือยาใดๆ ' if p.allergies else ''}"
                    "หากมีอาการผิดปกติเฉียบพลัน เช่น แน่นหน้าอก หายใจลำบาก เวียนศีรษะรุนแรง หรือมีไข้สูง ควรติดต่อคลินิกหรือพบแพทย์ทันที"
                ),
            },
            {
                'title': '5. สิ่งที่ทีมแพทย์จะติดตามในนัดครั้งต่อไป',
                'content': (
                    "ทีมแพทย์จะติดตามการตอบสนองของอาการ ความเปลี่ยนแปลงของสัญญาณชีพ และค่าผลตรวจเลือดซ้ำอย่างใกล้ชิด "
                    "ท่านสามารถช่วยทีมแพทย์ได้โดยการจดบันทึกอาการประจำวัน คุณภาพการนอนหลับ และอาการทางเดินอาหารมาพูดคุยในนัดครั้งหน้า"
                ),
            },
            {
                'title': '6. การตรวจเพิ่มเติมที่อาจช่วยตอบคำถามสุขภาพของคุณ',
                'content': (
                    "แพทย์อาจพิจารณาแนะนำการตรวจเลือดเฉพาะทางหรือการตรวจสมดุลจุลินทรีย์ลำไส้เพิ่มเติม "
                    "เฉพาะรายการที่จะช่วยให้การปรับแผนดูแลสุขภาพของท่านแม่นยำและเห็นผลชัดเจนยิ่งขึ้น"
                ),
            },
            {
                'title': '7. แผนดูแลสุขภาพที่แพทย์แนะนำและแนวทางปฏิบัติตัว',
                'content': (
                    f"{'แผนดูแลจากแพทย์: ' + doc_notes if doc_notes else 'ขณะนี้แผนฟื้นฟูสุขภาพเชิงลึกอยู่ระหว่างการพิจารณาและปรับให้เหมาะสมเฉพาะบุคคลโดยแพทย์ผู้ดูแล'} "
                    "ในระหว่างนี้แนะนำให้พักผ่อนให้เพียงพอ 7–8 ชั่วโมง เลี่ยงอาหารน้ำตาลสูงและอาหารแปรรูป และดื่มน้ำสะอาดอย่างเพียงพอ"
                ),
            },
        ]

        # ---------------- 3. MULTI-OMICS EDITION (Smart Gate: 3 Readiness or Deep Omics) ----------------
        if not snap['has_omics']:
            multiomics_chapters = [
                {
                    'title': 'Chapter 1 — Omics Readiness & Missing Datasets',
                    'content': (
                        "[NOT_AVAILABLE] การตรวจสอบคลังข้อมูลระดับโมเลกุลของคนไข้พบว่า **ยังไม่มีชุดข้อมูล Multi-Omics** "
                        "ได้แก่ Genomics (NGS/SNPs), Gut Microbiome (16S rRNA/Shotgun), Metabolomics (Organic Acids), และ Cytokine/Proteomics Panel "
                        "ระบบจึงยังไม่สามารถออกรายงาน Multi-Omics ระดับยีนและเมตาบอไลต์แบบสมบูรณ์ได้"
                    ),
                },
                {
                    'title': 'Chapter 2 — Clinical Utility of Targeted Omics Testing',
                    'content': (
                        f"[CLINICAL_INFERENCE] จากสภาวะแกนชีวภาพที่มีแนวโน้มตึงตัวในปัจจุบัน ({', '.join(d['title'] for d in snap['domain_scores'] if d.get('avg_score') and d['avg_score'] >= 60)[:3] or 'การประเมินเบื้องต้น'}) "
                        "ชุดตรวจ Multi-Omics ที่คุ้มค่าทางคลินิกควรพิจารณาส่งตรวจตามลำดับคือ: "
                        "1) Gut Microbiome & Zonulin (ประเมินภาวะ Dysbiosis และ Tight Junction), "
                        "2) Pharmacogenomics CYP450 Panel (ประเมินความปลอดภัยการเมตาบอลิซึมยาและสารพฤกษเคมี), "
                        "3) Organic Acids / Mitochondrial Metabolomics"
                    ),
                },
                {
                    'title': 'Chapter 3 — Preliminary Phenotype-based Inferences [HYPOTHESIS]',
                    'content': (
                        f"[HYPOTHESIS] การเชื่อมโยงจากอาการทางคลินิกและผลตรวจพื้นฐานเท่าที่มี ({len(labs)} รายการแล็บ, {len(dys)} แกนที่คะแนน >= 60) "
                        "ถือเป็นเพียงสมมติฐานเบื้องต้นระดับฟีโนไทป์เท่านั้น มีความไม่แน่นอนสูงและไม่สามารถใช้แทนผลการตรวจ Genomics หรือ Microbiome จริงได้"
                    ),
                },
            ]
        else:
            omics = snap['omics_data']
            multiomics_chapters = [
                {
                    'title': 'บทที่ 1 — Executive Summary: Multi-Omics Health Overview',
                    'content': f"[MEASURED] บูรณาการชุดข้อมูล Omics ของผู้ป่วย ({', '.join(omics.keys())}) ร่วมกับคะแนน 39 แกนชีววิทยาและประวัติคลินิก",
                },
                {
                    'title': 'บทที่ 2 — Genomics, Pharmacogenomics & Microbiome Cross-talk',
                    'content': f"[MEASURED] ข้อมูลระดับโมเลกุลที่ตรวจพบ: {omics}",
                },
                {
                    'title': 'บทที่ 3 — Metabolomics, Mitochondrial Network & Personalized Modules',
                    'content': f"[DERIVED] แกนชีวภาพเป้าหมายที่สอดคล้องกับผล Omics:\n{top_dys_text}\nโมดูลแนะนำ:\n{mods_text}",
                },
            ]

        return {
            'physician': physician_chapters,
            'patient': patient_chapters,
            'multiomics': multiomics_chapters,
        }

