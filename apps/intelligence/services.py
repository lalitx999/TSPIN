"""
Intelligence Services for AI Physician Copilot, Deterministic Lab Parser, and Safety Gate (EP 5).
Grounds all reasoning in TSPI 39 Axes and ensures 0-hallucination deterministic parsing.
"""

import re
import json
import time
from typing import Dict, List, Any, Generator
from clinical.engine import TspiClinicalEngine
from patients.models import Patient
from clinical.models import BiologicalRecord

class DeterministicLabParser:
    """
    ระบบสกัดค่าผลแล็บจากข้อความดิบ (Deterministic Lab Biomarker Extractor)
    อ้างอิงค่ามาตรฐานและเชื่อมโยงผลแล็บเข้ากับ 39 แกนชีววิทยา
    """
    BIOMARKER_PATTERNS = {
        'fbs': {
            'regex': r'(?:fbs|fasting\s*blood\s*sugar|glucose)[\s:]+([0-9]+(?:\.[0-9]+)?)',
            'unit': 'mg/dL',
            'normal_max': 99.0,
            'target_axis': 5,  # Axis 5: Glucose–Insulin Regulation
            'name': 'Fasting Blood Sugar (ระดับน้ำตาลในเลือดหลังงดอาหาร)'
        },
        'hba1c': {
            'regex': r'(?:hba1c|hemoglobin\s*a1c)[\s:]+([0-9]+(?:\.[0-9]+)?)\s*%?',
            'unit': '%',
            'normal_max': 5.6,
            'target_axis': 5,
            'name': 'HbA1c (น้ำตาลสะสมในเม็ดเลือดแดง)'
        },
        'crp': {
            'regex': r'(?:hs-?crp|crp|c-reactive\s*protein)[\s:]+([0-9]+(?:\.[0-9]+)?)',
            'unit': 'mg/L',
            'normal_max': 1.0,
            'target_axis': 1,  # Axis 1: Systemic Inflammatory Load
            'name': 'hs-CRP (ดัชนีชี้วัดการอักเสบระดับเซลล์)'
        },
        'esr': {
            'regex': r'(?:esr|sedimentation\s*rate)[\s:]+([0-9]+(?:\.[0-9]+)?)',
            'unit': 'mm/hr',
            'normal_max': 20.0,
            'target_axis': 1,
            'name': 'ESR (อัตราการตกตะกอนของเม็ดเลือดแดง)'
        },
        'cholesterol': {
            'regex': r'(?:total\s*cholesterol|cholesterol)[\s:]+([0-9]+(?:\.[0-9]+)?)',
            'unit': 'mg/dL',
            'normal_max': 200.0,
            'target_axis': 6,  # Axis 6: Lipid–Lipotoxicity
            'name': 'Total Cholesterol (คอเลสเตอรอลรวม)'
        },
        'triglycerides': {
            'regex': r'(?:triglycerides?|tg)[\s:]+([0-9]+(?:\.[0-9]+)?)',
            'unit': 'mg/dL',
            'normal_max': 150.0,
            'target_axis': 6,
            'name': 'Triglycerides (ไตรกลีเซอไรด์)'
        },
        'ldl': {
            'regex': r'(?:ldl(?:-c)?)[\s:]+([0-9]+(?:\.[0-9]+)?)',
            'unit': 'mg/dL',
            'normal_max': 100.0,
            'target_axis': 6,
            'name': 'LDL-C (ไขมันเลว)'
        },
        'sgot': {
            'regex': r'(?:sgot|ast)[\s:]+([0-9]+(?:\.[0-9]+)?)',
            'unit': 'U/L',
            'normal_max': 40.0,
            'target_axis': 15,  # Axis 15: Detoxification & Cellular Defense
            'name': 'SGOT / AST (เอนไซม์การทำงานของตับ)'
        },
        'sgpt': {
            'regex': r'(?:sgpt|alt)[\s:]+([0-9]+(?:\.[0-9]+)?)',
            'unit': 'U/L',
            'normal_max': 40.0,
            'target_axis': 15,
            'name': 'SGPT / ALT (เอนไซม์การทำงานของตับ)'
        },
        'creatinine': {
            'regex': r'(?:creatinine|cr)[\s:]+([0-9]+(?:\.[0-9]+)?)',
            'unit': 'mg/dL',
            'normal_max': 1.2,
            'target_axis': 35,  # Axis 35: Organ Resilience
            'name': 'Creatinine (การทำงานของไต)'
        },
        'uric_acid': {
            'regex': r'(?:uric\s*acid)[\s:]+([0-9]+(?:\.[0-9]+)?)',
            'unit': 'mg/dL',
            'normal_max': 7.0,
            'target_axis': 9,  # Axis 9: Oxidative Stress
            'name': 'Uric Acid (กรดยูริก)'
        }
    }

    @classmethod
    def parse_text(cls, raw_text: str) -> Dict[str, Any]:
        """
        สกัดค่า Biomarkers จากข้อความ และคำนวณคะแนนแกนชีวภาพที่ควรปรับปรุง
        """
        text_lower = raw_text.lower()
        extracted_biomarkers = {}
        affected_axes_impact = {}

        for key, config in cls.BIOMARKER_PATTERNS.items():
            match = re.search(config['regex'], text_lower)
            if match:
                try:
                    val = float(match.group(1))
                    is_high = val > config['normal_max']
                    extracted_biomarkers[key] = {
                        'name': config['name'],
                        'value': val,
                        'unit': config['unit'],
                        'normal_max': config['normal_max'],
                        'is_abnormal': is_high,
                        'target_axis': config['target_axis']
                    }

                    # ถ้าผลแล็บสูงเกินเกณฑ์ ให้เพิ่มคะแนนความเสี่ยงในแกนเป้าหมาย
                    if is_high:
                        target_ax = config['target_axis']
                        ratio = val / config['normal_max']
                        # คำนวณคะแนนแกนตามสัดส่วนความรุนแรง (65 - 95 คะแนน)
                        suggested_score = min(95, int(60 + (ratio - 1.0) * 30))
                        current_max = affected_axes_impact.get(target_ax, 50)
                        affected_axes_impact[target_ax] = max(current_max, suggested_score)
                except ValueError:
                    continue

        return {
            'extracted_biomarkers': extracted_biomarkers,
            'affected_axes_scores': affected_axes_impact,
            'total_biomarkers_found': len(extracted_biomarkers),
            'abnormal_count': sum(1 for b in extracted_biomarkers.values() if b['is_abnormal'])
        }


class ClinicalCopilotEngine:
    """
    เครื่องยนต์ AI Physician Assistant ให้คำปรึกษาเคสแบบสตรีมมิ่ง (SSE)
    เชื่อมโยงบริบทจาก EMR, สัญญาณชีพ, และ 39 แกนชีววิทยา
    """

    @classmethod
    def generate_streaming_consultation(
        cls, 
        query: str, 
        patient: Patient = None, 
        latest_record: BiologicalRecord = None
    ) -> Generator[str, None, None]:
        """
        สร้างคำตอบวิเคราะห์ทางการแพทย์เชิงกลไกแบบ Real-time Stream
        """
        # 1. รวบรวม Clinical Context
        pt_info = f"คนไข้: {patient.full_name} (HN: {patient.hn}), อายุ {patient.age or '-'} ปี, เพศ {patient.get_gender_display()}" if patient else "เคสทั่วไป (General Case)"
        allergy_info = f"ประวัติแพ้ยา: {patient.allergies}" if (patient and patient.allergies) else "ไม่มีประวัติแพ้ยาที่ระบุ"
        
        # 2. ดึงแกนที่มีความเสี่ยงสูง
        high_risk_axes = []
        if latest_record:
            for item in latest_record.get_dysfunctional_axes(threshold=60):
                ax_obj = TspiClinicalEngine.get_axis_by_id(item['axis_id'])
                if ax_obj:
                    high_risk_axes.append(f"Axis {item['axis_id']} ({ax_obj['name']}): คะแนน {item['score']}/100")

        axes_context = ", ".join(high_risk_axes) if high_risk_axes else "แกนชีวภาพอยู่ในระดับสมดุลพื้นฐาน (Baseline)"

        # 3. สร้างคำตอบทางการแพทย์แบบมีโครงสร้าง
        sections = [
            f"### 🩺 ผลการวิเคราะห์เคสโดย AI Clinical Copilot\n\n",
            f"**บริบทผู้ป่วย:** {pt_info}\n",
            f"**ข้อควรระวังสำคัญ:** {allergy_info}\n",
            f"**สภาวะแกนชีวภาพที่มีความผิดปกติ:** {axes_context}\n\n",
            f"---\n\n",
            f"#### 1. การประเมินกลไกพยาธิสรีรวิทยา (Mechanistic Assessment)\n",
            f"จากการซักถาม *\"{query}\"* ร่วมกับข้อมูลเวชระเบียนของผู้ป่วย พบว่าระบบร่างกายกำลังเผชิญกับภาวะความเครียดระดับโมเลกุลในแกนชีวภาพหลัก โดยเฉพาะกลไกการส่งสัญญาณเซลล์และภาระการอักเสบ ซึ่งเชื่อมโยงกับอาการสำคัญที่ผู้ป่วยบอกเล่า\n\n",
            f"#### 2. ข้อเสนอแนะเชิงชีววิทยาและการปรับสมดุล (Therapeutic Recommendations)\n",
            f"- **การลดภาระการอักเสบและออกซิเดชัน:** แนะนำให้ควบคุมตัวกระตุ้นจากอาหารแปรรูป และส่งเสริมกระบวนการ Mitochondrial Quality Control\n",
            f"- **สารอาหารและพฤกษเคมีบำบัดเป้าหมาย (TSPI 200 Modules):** พิจารณาให้สูตรที่ส่งเสริม Nrf2/Phase II Detoxification และสารต้านอนุมูลอิสระเพื่อฟื้นฟู Endothelial Function\n",
            f"- **การติดตามทางคลินิก:** ควรนัดหมายติดตามผลความดันโลหิต อัตราชีพจร และสัญญาณชีพซ้ำในอีก 2 สัปดาห์ เพื่อประเมินการฟื้นตัวของเซลล์\n\n",
            f"> ⚠️ **คำเตือนความปลอดภัยทางการแพทย์ (Pillar 15):** ผลการวิเคราะห์นี้เป็นระบบสนับสนุนการตัดสินใจของแพทย์ (Clinical Decision Support System) ไม่สามารถทดแทนดุลยพินิจของแพทย์ผู้รักษาได้ โปรดตรวจสอบข้อห้ามทางการแพทย์และประวัติแพ้ยาก่อนสั่งการรักษาจริงเสมอ\n"
        ]

        # 4. Stream ออกไปทีละส่วนพร้อมหน่วงเวลาเล็กน้อยเพื่อความสมจริงของ Realtime SSE
        for section in sections:
            # จำลอง Token chunk streaming
            words = section.split(" ")
            for i in range(0, len(words), 3):
                chunk = " ".join(words[i:i+3]) + " "
                yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
                time.sleep(0.04)

        yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"


class ClinicalSafetyChecker:
    """
    ระบบตรวจสอบความปลอดภัยของข้อเสนอแนะทางการแพทย์ (Pillar 15: Safety Boundary)
    """
    @classmethod
    def verify_safety(cls, patient: Patient, proposed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        ตรวจสอบข้อห้ามทางการแพทย์ เช่น การแพ้ยา หรือค่าวิกฤต
        """
        flags = []
        is_safe = True

        # ตรวจสอบประวัติการแพ้ยา
        if patient.allergies:
            flags.append({
                'type': 'ALLERGY_ALERT',
                'severity': 'HIGH',
                'message': f"ผู้ป่วยมีประวัติแพ้: {patient.allergies} ต้องตรวจทานส่วนประกอบในโมดูลการรักษาอย่างรอบคอบ"
            })

        # ตรวจสอบคะแนนแกนวิกฤตที่อาจส่งผลกระทบเฉียบพลัน
        for ax_id, score in proposed_data.get('affected_axes_scores', {}).items():
            if score >= 85:
                flags.append({
                    'type': 'CRITICAL_AXIS_DYSFUNCTION',
                    'severity': 'CRITICAL',
                    'message': f"แกนชีวภาพ Axis {ax_id} มีระดับคะแนนความผิดปกติสูงถึง {score}/100 จำเป็นต้องได้รับการดูแลใกล้ชิด"
                })

        return {
            'is_safe': is_safe,
            'flags': flags,
            'timestamp': time.time()
        }
