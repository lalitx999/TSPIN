"""
Management command to populate rich clinical demo data for local testing.
Creates Doctor, Nurse, Patient accounts, 39 Axes biological records,
appointments, and approved precision reports.
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import User
from patients.models import Patient, PatientHistory, Appointment
from clinical.models import BiologicalRecord, AnalysisRecord
from intelligence.models import AIConsultationSession, AIConsultationMessage, AgenticArtifact


class Command(BaseCommand):
    help = 'Seeds realistic clinical demo data for local testing'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("🌱 Starting TSPI Clinical Demo Data Seeding..."))

        # 1. Create Doctor / Admin User
        doctor, created = User.objects.get_or_create(
            username='drpatt',
            defaults={
                'email': 'dr.patt@tspi.com',
                'first_name': 'พัทธ์',
                'last_name': 'สุวรรณเวช',
                'role': User.Role.DOCTOR,
                'phone': '0819998888',
                'email_verified': True,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            doctor.set_password('Password12345!')
            doctor.save()
            self.stdout.write(self.style.SUCCESS("  [+] Created Doctor: drpatt / Password12345!"))
        else:
            self.stdout.write("  [*] Doctor drpatt already exists")

        # 2. Create Nurse User
        nurse, created = User.objects.get_or_create(
            username='nurse_lin',
            defaults={
                'email': 'nurse.lin@tspi.com',
                'first_name': 'รินรดา',
                'last_name': 'ใจดี',
                'role': User.Role.NURSE,
                'phone': '0821112233',
                'email_verified': True,
                'is_staff': True,
            }
        )
        if created:
            nurse.set_password('Password12345!')
            nurse.save()
            self.stdout.write(self.style.SUCCESS("  [+] Created Nurse: nurse_lin / Password12345!"))

        # 3. Create Patient 1 (Siriporn - Active Case with approved report)
        patient_user, _ = User.objects.get_or_create(
            username='siriporn',
            defaults={
                'email': 'siriporn@example.com',
                'first_name': 'ศิริพร',
                'last_name': 'บุญรักษา',
                'role': User.Role.PATIENT,
                'phone': '0812345678',
                'email_verified': True,
            }
        )
        patient_user.set_password('Password12345!')
        patient_user.save()

        p1, _ = Patient.objects.get_or_create(
            hn='HN-2026-0001',
            defaults={
                'user': patient_user,
                'first_name': 'ศิริพร',
                'last_name': 'บุญรักษา',
                'nickname': 'หนิง',
                'gender': 'F',
                'birth_date': date(1988, 6, 12),
                'blood_type': 'O+',
                'phone': '0812345678',
                'status': 'medicine',
                'allergies': 'Penicillin (ผื่นคันรุนแรง), กุ้ง/อาหารทะเล',
                'chief_complaint': 'อ่อนเพลียเรื้อรัง นอนไม่หลับ แน่นท้อง ท้องอืดง่าย มีผื่นคันขึ้นบ่อย',
                'medical_history': 'ผ่าตัดไส้ติ่งอักเสบ (2018), ภาวะลำไส้แปรปรวน (IBS)',
            }
        )
        p1.user = patient_user
        p1.save()

        # Create 39 Axes Record for Patient 1
        scores_1 = {
            'axis_1': 78,   # High Inflammation
            'axis_2': 65,   # Immune Dysregulation
            'axis_9': 72,   # Oxidative Stress
            'axis_16': 68,  # Liver Detoxification
            'axis_17': 82,  # Digestive Function Dysfunction
            'axis_18': 85,  # Gut Microbiome Ecology Dysbiosis
            'axis_19': 75,  # Gut Barrier Integrity (Leaky Gut)
            'axis_21': 45,
            'axis_25': 60,
            'axis_27': 55,
        }
        bio1, _ = BiologicalRecord.objects.get_or_create(
            patient=p1,
            defaults=scores_1
        )

        # Create SOAP History for Patient 1
        PatientHistory.objects.get_or_create(
            patient=p1,
            doctor=doctor,
            subjective="คนไข้มาตรวจติดตามผลหลังรับประทานสารอาหารบำบัดสูตรเฉพาะทาง 2 สัปดาห์ อาการท้องอืดลดลง แต่ยังมีอาการเพลียช่วงบ่าย",
            objective="BP: 118/76 mmHg, PR: 72 bpm, Wt: 54.5 kg, Ht: 162 cm, BMI: 20.8 (Normal). Abdomen soft, non-tender. Lab: hs-CRP 3.8 mg/L (ลดลงจาก 6.2).",
            assessment="1. Chronic Low-grade Systemic Inflammation (Axis 1)\n2. Gut Microbiome Dysbiosis & Permeability (Axes 17, 18, 19)\n3. Improved inflammatory trajectory",
            plan="1. ปรับเพิ่มสูตร PhytoCore TSPI-CURCUMA-01 ขนาด 500mg วันละ 2 เวลา ก่อนอาหาร\n2. เสริม Probiotic Complex โดส 50 พันล้าน CFU ก่อนนอน\n3. หลีกเลี่ยงกลูเตนและน้ำตาลแปรรูป\n4. นัดตรวจติดตามเลือดซ้ำในอีก 4 สัปดาห์",
            vitals={
                'bp_sys': 118,
                'bp_dia': 76,
                'pulse': 72,
                'weight': 54.5,
                'height': 162,
            }
        )

        # Create Approved Analysis Record & Precision Report
        rep1, _ = AnalysisRecord.objects.get_or_create(
            patient=p1,
            physician=doctor,
            status='approved',
            defaults={
                'biological_record': bio1,
                'snapshot_scores': bio1.to_scores_dict(),
                'key_findings': 'ความผิดปกติหลักอยู่ที่กลุ่มทางเดินอาหารและจุลชีพในลำไส้ (Axis 17, 18, 19) ส่งผลให้เกิดภาวะการอักเสบเรื้อรังระดับเซลล์ (Axis 1)',
                'doctor_summary': 'คนไข้มีแนวโน้มการฟื้นตัวที่ดีขึ้น การบำบัดด้วยโภชนเภสัชเฉพาะบุคคลช่วยลดระดับความเสียหายของผนังลำไส้ได้อย่างมีนัยสำคัญ',
                'therapeutic_plan': 'Targeted Botanical Protocol: TSPI-CURCUMA-01 + Microbiome Restoration',
                'approved_at': timezone.now() - timedelta(days=2),
                'released_at': timezone.now() - timedelta(days=2),
            }
        )

        # Create Appointment for Patient 1
        Appointment.objects.get_or_create(
            patient=p1,
            doctor=doctor,
            appointment_date=date.today() + timedelta(days=7),
            appointment_time='10:30:00',
            status='confirmed',
            notes='ตรวจติดตามผลระบบทางเดินอาหารและระดับการอักเสบ (Follow-up visit)'
        )

        # 4. Create Patient 2 (Thanawat - Pending AI Consult & Artifact)
        p2, _ = Patient.objects.get_or_create(
            hn='HN-2026-0002',
            defaults={
                'first_name': 'ธนวัฒน์',
                'last_name': 'เจริญผล',
                'nickname': 'วัฒน์',
                'gender': 'M',
                'birth_date': date(1975, 11, 24),
                'blood_type': 'B+',
                'phone': '0898765432',
                'status': 'pending',
                'allergies': 'Aspirin (หายใจติดขัด)',
                'chief_complaint': 'ไขมันพอกตับ คอเลสเตอรอลสูง ตรวจเลือดพบเอนไซม์ตับ ALT/AST สูงขึ้น',
            }
        )

        bio2, _ = BiologicalRecord.objects.get_or_create(
            patient=p2,
            defaults={
                'axis_1': 62,
                'axis_16': 88, # Liver Detox Dysfunction
                'axis_27': 74, # Metabolic Syndrome
                'axis_28': 80, # Insulin Sensitivity
            }
        )

        # AI Session with pending artifact
        ai_session, _ = AIConsultationSession.objects.get_or_create(
            patient=p2,
            doctor=doctor,
            title="วิเคราะห์ผลแล็บเอนไซม์ตับและภาวะดื้ออินซูลิน"
        )

        AgenticArtifact.objects.get_or_create(
            patient=p2,
            doctor=doctor,
            artifact_type='lab_extraction',
            status='pending',
            defaults={
                'title': 'ผลตรวจแล็บตับและเมแทบอลิซึม (รอแพทย์ลงนามอนุมัติเข้า EMR)',
                'proposed_data': {
                    'ALT': {'value': 78, 'unit': 'U/L', 'status': 'HIGH', 'target_axes': [16]},
                    'AST': {'value': 52, 'unit': 'U/L', 'status': 'HIGH', 'target_axes': [16]},
                    'Triglycerides': {'value': 220, 'unit': 'mg/dL', 'status': 'HIGH', 'target_axes': [27, 28]},
                    'HbA1c': {'value': 6.2, 'unit': '%', 'status': 'PREDIABETIC', 'target_axes': [28]},
                },
                'safety_checks': {'flags': ['ELEVATED_LIVER_ENZYMES_AXIS_16']},
            }
        )

        # 5. Create Patient 3 (Kamolporn - Urgent case)
        p3, _ = Patient.objects.get_or_create(
            hn='HN-2026-0003',
            defaults={
                'first_name': 'กมลพร',
                'last_name': 'จิตสงบ',
                'gender': 'F',
                'birth_date': date(1963, 2, 5),
                'blood_type': 'A+',
                'phone': '0865554321',
                'status': 'urgent',
                'allergies': 'NSAIDs, Sulfa',
                'chief_complaint': 'ข้ออักเสบรูมาตอยด์กำเริบรุนแรง ปวดตามข้อนิ้วมือและเข่า',
            }
        )

        self.stdout.write(self.style.SUCCESS("✨ Successfully seeded TSPI Clinical Demo Data!"))
        self.stdout.write(self.style.NOTICE("""
======================================================================
🏥 TSPI CLINICAL EMR - LOCAL TEST ACCOUNTS READY:
======================================================================
1. แพทย์ผู้รักษา (Doctor Portal & AI Copilot):
   - URL:      http://localhost:8000/accounts/login/
   - Username: drpatt
   - Password: Password12345!

2. พยาบาล/เจ้าหน้าที่ (Clinical Staff):
   - Username: nurse_lin
   - Password: Password12345!

3. คนไข้ (Patient Portal & Precision Report):
   - URL:      http://localhost:8000/patient/login/
   - Login 1:  HN: HN-2026-0001  / Phone: 0812345678
   - Login 2:  Username: siriporn / Password: Password12345!

4. หน้าตรวจสอบสถานะระบบ (Healthcheck):
   - URL:      http://localhost:8000/health/
======================================================================
        """))
