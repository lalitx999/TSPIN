from django.utils.translation import gettext_lazy as _
"""
เนื้อหาคงที่ของหน้าเว็บสาธารณะ (ย้ายมาจาก HTML เดิมในเฟส 3 ของ docs/UI_REDESIGN_FASTWORK_2026-11.md)
ข้อความชุดเดิมทุกคำ ยกเว้นชื่อโดเมนภาษาไทย (th) ที่เพิ่มให้คนไข้อ่านเข้าใจ
"""

# ---- 12 โดเมน / 39 แกน (หน้า /platform/) ----
PLATFORM_DOMAINS = [
    {'n': 1, 'icon': 'fa-shield-virus', 'th': _('ภูมิคุ้มกันและการติดเชื้อ'), 'en': 'Immune–Infection Governance', 'range': _('แกนที่ 1 - 4'),
     'axes': [('1', 'Systemic Inflammatory Load (NF-κB, IL-6, TNF-α)'),
              ('2', 'Immune Homeostasis (Th1/Th2, M1/M2, Treg)'),
              ('3', 'Pathogen Defense (Host Defense & Mucosal Barrier)'),
              ('4', 'Post-Infectious Persistence (Latent Viral Reactivation)')]},
    {'n': 2, 'icon': 'fa-bolt', 'th': _('การเผาผลาญและพลังงาน'), 'en': 'Metabolic–Energy Core', 'range': _('แกนที่ 5 - 10'),
     'axes': [('5', 'Glucose–Insulin Regulation (HOMA-IR, AKT)'),
              ('6', 'Lipid–Lipotoxicity (Atherogenic Lipid, NAFLD)'),
              ('7', 'Nutrient Sensing (AMPK vs mTORC1 switch)'),
              ('8', 'Mitochondrial Network & Bioenergetics'),
              ('9', 'Oxidative Stress & Redox Signaling'),
              ('10', 'Autophagy & Proteostasis Dynamics')]},
    {'n': 3, 'icon': 'fa-dna', 'th': _('พันธุกรรมและการซ่อมแซม'), 'en': 'Genomic Programming', 'range': _('แกนที่ 11 - 14'),
     'axes': [('11', 'DNA Repair & Genomic Stability (8-OHdG)'),
              ('12', 'Telomere Dynamics & Cellular Lifespan'),
              ('13', 'Epigenetic Maintenance & Methylation'),
              ('14', 'Cellular Senescence & SASP Secretion')]},
    {'n': 4, 'icon': 'fa-filter', 'th': _('การล้างพิษและกำจัดของเสีย'), 'en': 'Detoxification & Clearance', 'range': _('แกนที่ 15'),
     'axes': [('15', 'Detoxification & Defense (Hepatic Phase 1/2)'),
              ('', 'Glutathione Conjugation & Toxin Elimination'),
              ('', 'Heavy Metal Chelation & Uric Acid Clearance')]},
    {'n': 5, 'icon': 'fa-bacteria', 'th': _('ลำไส้และจุลินทรีย์'), 'en': 'Digestive–Gut Ecosystem', 'range': _('แกนที่ 16 - 19'),
     'axes': [('16', 'Digestive–Absorptive Function (Enzyme Output)'),
              ('17', 'Microbiome Ecosystem (SCFAs, Dysbiosis)'),
              ('18', 'Bile & Liver–Gut Axis (Bile Acid Dynamics)'),
              ('19', 'Gut Barrier Integrity (Zonulin, Leaky Gut)')]},
    {'n': 6, 'icon': 'fa-heartbeat', 'th': _('หลอดเลือดและการไหลเวียน'), 'en': 'Vascular–Circulation', 'range': _('แกนที่ 20 - 23'),
     'axes': [('20', 'Endothelial Function (NO Signaling)'),
              ('21', 'Microcirculation & Tissue Perfusion'),
              ('22', 'Coagulation–Fibrinolysis Balance'),
              ('23', 'Lymphatic Flow & Tissue Drainage')]},
    {'n': 7, 'icon': 'fa-band-aid', 'th': _('การซ่อมแซมและฟื้นฟูเนื้อเยื่อ'), 'en': 'Repair–Regeneration', 'range': _('แกนที่ 24 - 27'),
     'axes': [('24', 'Wound Healing (Internal + External Epithelium)'),
              ('25', 'Extracellular Matrix (ECM Remodeling)'),
              ('26', 'Bone Remodeling & Mineral Turnover'),
              ('27', 'Cartilage & Joint Homeostasis')]},
    {'n': 8, 'icon': 'fa-bone', 'th': _('กล้ามเนื้อ กระดูก และโครงสร้าง'), 'en': 'Musculoskeletal & Structural', 'range': _('แกนที่ 28 - 30'),
     'axes': [('28', 'Muscle Protein Turnover (Anabolic Signaling)'),
              ('29', 'Fascial & Structural Integrity'),
              ('30', 'Tendon & Ligament Resilience')]},
    {'n': 9, 'icon': 'fa-balance-scale', 'th': _('ฮอร์โมนและต่อมไร้ท่อ'), 'en': 'Endocrine Network', 'range': _('แกนที่ 31 - 33'),
     'axes': [('31', 'Female Hormone Network (Estrogen / Progesterone)'),
              ('32', 'Male Androgen Network (Testosterone / DHT)'),
              ('33', 'Thyroid–Adrenal–Growth Axis (HPA Rhythm, TSH)')]},
    {'n': 10, 'icon': 'fa-brain', 'th': _('ระบบประสาท การนอน และความเครียด'), 'en': 'Neurological Regulation', 'range': _('แกนที่ 34'),
     'axes': [('34', 'Neuro–Sleep–Stress–Brain Clearance'),
              ('', 'Glymphatic Clearance & Circadian Rhythm'),
              ('', 'Neuroinflammation & Autonomic Tone')]},
    {'n': 11, 'icon': 'fa-lungs', 'th': _('ความแข็งแรงของอวัยวะ'), 'en': 'Organ Axis', 'range': _('แกนที่ 35 - 36'),
     'axes': [('35', _('Organ Resilience & Functional Reserve (ตับ, ไต, หัวใจ)')),
              ('36', _('Local Organ & Tissue Interface (ตา, ไซนัส, มดลูก)')),
              ('', 'Visceral Functional Redundancy & Organ Resilience')]},
    {'n': 12, 'icon': 'fa-microscope', 'th': _('การควบคุมเซลล์และระดับระบบ'), 'en': 'Oncology & System-Level', 'range': _('แกนที่ 37 - 39'),
     'axes': [('37', 'Oncologic Cell Fate (Apoptosis, Cell Cycle)'),
              ('38', 'Tumor Microenvironment & Metastatic Dynamics'),
              ('39', 'Genomic Regulation Homeostasis')]},
]

# ---- แผนฟื้นฟู 9 ขั้นตอน (หน้า /protocol/) ----
PROTOCOL_PHASES = [
    {'n': 1, 'en': 'Assess & Cleanse', 'weeks': _('สัปดาห์ที่ 1 - 8'), 'duration': _('6-8 สัปดาห์'),
     'summary': _('ประเมินเชิงลึก กำจัดภาระสารพิษตับ และฟื้นฟูเกราะป้องกันลำไส้'),
     'steps': [
         {'n': '01', 'en': 'Deep Assessment', 'desc': _('วิเคราะห์ข้อมูลสุขภาพ 39 แกนชีววิทยา (12 โดเมน) ด้วย AI ประเมินชีวเคมีเลือด สัญญาณการอักเสบ และตรวจคัดกรอง Leaky Gut'),
          'modules': ['AI Intake', 'Blood Panel', 'Digital Twin']},
         {'n': '02', 'en': 'Detoxification', 'desc': _('กระตุ้นเอนไซม์ Cytochrome P450 และ Conjugation ในตับ ขับสารพิษสะสม โลหะหนัก และลดภาระตับคั่งไขมัน'),
          'modules': ['HEPA-1', 'HEPA-3', 'Glutathione Support']},
         {'n': '03', 'en': 'Gut Restoration', 'desc': _('ซ่อมแซม Tight Junctions ที่ผนังลำไส้ ลดการรั่วไหลของ Endotoxin สู่กระแสเลือด และปรับสมดุล Microbiome'),
          'modules': ['CINNARA', 'GUT-1', 'Glutamine Complex']},
     ]},
    {'n': 2, 'en': 'Rebalance Core', 'weeks': _('สัปดาห์ที่ 9 - 16'), 'duration': _('8 สัปดาห์'),
     'summary': _('ปรับสมดุลการเผาผลาญ ฟื้นฟูต่อมไร้ท่อ และควบคุมการอักเสบระดับเซลล์'),
     'steps': [
         {'n': '04', 'en': 'Metabolic Reset', 'desc': _('ปรับปรุงความไวของตัวรับอินซูลิน ลดภาวะไขมันพอกตับ และเพิ่มความยืดหยุ่นในการสลับแหล่งพลังงาน (Metabolic Flexibility)'),
          'modules': ['MET-1', 'Berberine Synergy', 'Alpha-Lipoic Acid']},
         {'n': '05', 'en': 'Hormonal Balance', 'desc': _('ปรับจังหวะการหลั่งคอร์ติซอล ฟื้นฟูต่อมหมวกไตล้า สมดุลฮอร์โมนไทรอยด์ และสร้างเสถียรภาพแก่ฮอร์โมนเพศ'),
          'modules': ['ADREN-1', 'Ashwagandha KSM-66', 'Thyroid Support']},
         {'n': '06', 'en': 'Immune Modulation', 'desc': _('กดการส่งสัญญาณ NF-κB, ปรับสัดส่วน Th1/Th2 และ M1/M2 Macrophages เพื่อหยุดวงจรการโจมตีเนื้อเยื่อตนเอง'),
          'modules': ['KERRA', 'MINOZA', 'Curcumin Phospholipid']},
     ]},
    {'n': 3, 'en': 'Repair & Longevity', 'weeks': _('สัปดาห์ที่ 17+'), 'duration': _('ต่อเนื่องระยะยาว'),
     'summary': _('กระตุ้นการซ่อมแซมดีเอ็นเอ ยืดความยาวเทโลเมียร์ และคงสภาพเซลล์อ่อนเยาว์'),
     'steps': [
         {'n': '07', 'en': 'Cellular Repair', 'desc': _('เร่งการกำจัดเซลล์ชราภาพ (Senescent Cells) ผ่านกระบวนการ Autophagy และกระตุ้นเอนไซม์ซ่อมแซมรหัสพันธุกรรม PARP'),
          'modules': ['CELL-1', 'Spermidine', 'Resveratrol Active']},
         {'n': '08', 'en': 'Neuroplasticity', 'desc': _('ส่งเสริมการสร้างเซลล์ประสาทใหม่ (BDNF) ฟื้นฟูไมอีลิน และเพิ่มประสิทธิภาพการชะล้างของเสียสมองช่วงหลับลึก'),
          'modules': ['NEURO-1', "Lion's Mane Dual-Extract", 'Phosphatidylserine']},
         {'n': '09', 'en': 'Longevity Protocol', 'desc': _('ออกแบบโปรแกรมบำรุงรักษาสุขภาพเฉพาะบุคคล เพื่อป้องกันการเกิดโรคซ้ำ และคงสภาวะความอ่อนเยาว์ในระดับโมเลกุล'),
          'modules': ['LONGEV-MAX', 'NMN Synergy', 'CoQ10 Ubiquinol']},
     ]},
]

# ---- กรณีศึกษาในหน้า /research/ ----
# ซ่อนไว้ก่อน (ผู้ใช้สั่ง 18 พ.ย. 2026): ยังไม่ได้ยืนยันว่าเคส "คุณนิคม" เป็นเคสจริงและได้รับความยินยอมให้เผยแพร่ตาม PDPA
# เปิดกลับด้วย True เมื่อคลินิกยืนยันแล้วเท่านั้น
RESEARCH_SHOW_CASE_STUDY = False

# ---- ตัวชี้วัดชีวภาพหลัก (หน้า /research/) ----
RESEARCH_BIOMARKERS = [
    ('hs-CRP', 'Systemic Inflammation'),
    ('Zonulin', 'Gut Barrier Integrity'),
    ('Fasting Insulin', 'Insulin Resistance'),
    ('8-OHdG', 'DNA Oxidative Damage'),
    ('IL-6 / TNF-α', 'Cytokine Cascade'),
    ('Cortisol Rhythm', 'HPA Axis Function'),
]

# ---- ขั้นตอนรับบริการ (หน้า /guide/) ----
GUIDE_STEPS = [
    (_('ลงทะเบียนเข้าสู่ระบบคนไข้'),
     _('สมัครสมาชิกด้วยเลขบัตรประชาชน ชื่อ-นามสกุล และเบอร์โทรศัพท์ ระบบจะออกหมายเลขประจำตัวผู้ป่วย (HN) อัตโนมัติ')),
    (_('ซักประวัติอาการล่วงหน้ากับ AI'),
     _('ตอบคำถามอาการที่รู้สึก อาหารการกิน และอัปโหลดผลตรวจเลือดที่มี AI จะประมวลผลจัดกลุ่มเข้าสู่ 39 แกนชีววิทยา (12 โดเมน)')),
    (_('รับผลวิเคราะห์ 39 แกนชีววิทยา (12 โดเมน)'),
     _('ดูภาพรวมสุขภาพผ่านกราฟ Digital Twin จุดใดที่ร่างกายกำลังส่งสัญญาณเตือน พร้อมคำอธิบายภาษาไทยที่เข้าใจง่าย')),
    (_('เข้าพบแพทย์และรับแผนบำบัดฟื้นฟู 9 ขั้นตอน'),
     _('ปรึกษาแพทย์เฉพาะทาง ออกแบบการบำบัดด้วยสูตรสารสกัดไฟโตเคมีคอล 200 โมดูล พร้อมติดตามผลทุก 4 สัปดาห์')),
]

# ---- ขั้นตอนติดตั้งแอปบนมือถือ (หน้า /install/) — {host} แทนที่ด้วยโดเมนที่เปิดอยู่จริง ----
INSTALL_STEPS = {
    'ios': [
        (_('เปิดเว็บไซต์ด้วย Safari'), _('เข้าสู่เว็บไซต์ {host} ด้วยเบราว์เซอร์ Safari บน iPhone หรือ iPad ของท่าน')),
        (_('กดปุ่มแชร์ (Share Icon)'), _('กดที่ปุ่มแชร์รูปสี่เหลี่ยมที่มีลูกศรชี้ขึ้น ที่แถบด้านล่างของหน้าจอ Safari')),
        (_('เลือก "เพิ่มไปยังหน้าจอโฮม" (Add to Home Screen)'), _('เลื่อนลงมาในเมนูแชร์ และกดเลือก "เพิ่มไปยังหน้าจอโฮม" แล้วกดปุ่ม "เพิ่ม" (Add)')),
    ],
    'android': [
        (_('เปิดเว็บไซต์ด้วย Google Chrome'), _('เข้าสู่เว็บไซต์ {host} ด้วยเบราว์เซอร์ Chrome บนสมาร์ตโฟน Android ของท่าน')),
        (_('กดปุ่มเมนู 3 จุด'), _('กดที่จุด 3 จุดมุมบนขวาของเบราว์เซอร์ Chrome')),
        (_('เลือก "ติดตั้งแอป" (Install App)'), _('กดเลือก "ติดตั้งแอป" หรือ "เพิ่มลงในหน้าจอหลัก" แล้วกดยืนยันการติดตั้ง')),
    ],
}
