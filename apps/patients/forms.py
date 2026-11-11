"""
Forms for Patient EMR Management (Pillars 2, 3).
Enforces Strict Input Validation and Doctor SOAP Entry.
"""

from django import forms
from django.core.exceptions import ValidationError
from patients.models import Patient, PatientHistory

class PatientForm(forms.ModelForm):
    """
    ฟอร์มบันทึก/แก้ไขข้อมูลเวชระเบียนผู้ป่วย
    """
    class Meta:
        model = Patient
        fields = [
            'hn', 'first_name', 'last_name', 'nickname',
            'gender', 'birth_date', 'blood_type',
            'phone', 'email', 'status',
            'allergies', 'chief_complaint', 'medical_history', 'current_medications'
        ]
        widgets = {
            'hn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น HN-2026-0001', 'required': True}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'nickname': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'blood_type': forms.Select(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0812345678', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'allergies': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'ระบุการแพ้ยา สารเคมี อาหาร'}),
            'chief_complaint': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'อาการสำคัญที่มารับการรักษา'}),
            'medical_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'โรคประจำตัว การผ่าตัด'}),
            'current_medications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'ยาประจำตัว อาหารเสริม หรือสมุนไพรที่ใช้อยู่ในปัจจุบัน'}),
        }

    def clean_hn(self):
        hn = self.cleaned_data.get('hn', '').strip()
        if not hn:
            raise ValidationError("กรุณาระบุหมายเลข HN")
        # ตรวจสอบซ้ำซ้อนยกเว้นกรณีแก้ไขข้อมูลคนเดิม
        qs = Patient.objects.filter(hn__iexact=hn)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(f"หมายเลข HN: {hn} มีอยู่ในระบบแล้ว")
        return hn


class PatientHistorySOAPForm(forms.ModelForm):
    """
    ฟอร์มบันทึกการตรวจรักษาของแพทย์ตามกรอบมาตรฐาน SOAP Framework
    """
    # สัญญาณชีพ (Vitals)
    bp_systolic = forms.IntegerField(
        label="ความดันบน (Systolic)", 
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '120'})
    )
    bp_diastolic = forms.IntegerField(
        label="ความดันล่าง (Diastolic)", 
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '80'})
    )
    pulse = forms.IntegerField(
        label="ชีพจร (Pulse bpm)", 
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '72'})
    )
    temperature = forms.FloatField(
        label="อุณหภูมิ (°C)", 
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.1', 'placeholder': '36.5'})
    )
    weight_kg = forms.FloatField(
        label="น้ำหนัก (กก.)", 
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.1', 'placeholder': '65'})
    )
    height_cm = forms.FloatField(
        label="ส่วนสูง (ซม.)", 
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.5', 'placeholder': '170'})
    )
    spo2 = forms.IntegerField(
        label="ออกซิเจนปลายนิ้ว (% SpO2)", 
        required=False, 
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '98'})
    )

    class Meta:
        model = PatientHistory
        fields = ['subjective', 'objective', 'assessment', 'plan']
        widgets = {
            'subjective': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3, 
                'placeholder': 'S (Subjective): อาการที่คนไข้บอกเล่า, อาการปวด, ความผิดปกติที่รู้สึก'
            }),
            'objective': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3, 
                'placeholder': 'O (Objective): ข้อมูลที่แพทย์ตรวจพบทางกายภาพ, ผลแล็บสำคัญ'
            }),
            'assessment': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3, 
                'placeholder': 'A (Assessment): การวินิจฉัย/การประเมินสภาวะชีวภาพและแกนที่มีปัญหา'
            }),
            'plan': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3, 
                'placeholder': 'P (Plan): แผนการบำบัดฟื้นฟู, สารอาหารเสริม, ยา, นัดหมายติดตาม'
            }),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        # รวบรวม Vitals เป็น JSON
        vitals_data = {}
        for field in ['bp_systolic', 'bp_diastolic', 'pulse', 'temperature', 'weight_kg', 'height_cm', 'spo2']:
            val = self.cleaned_data.get(field)
            if val is not None:
                vitals_data[field] = val

        # คำนวณ BMI อัตโนมัติถ้ามีทั้ง น้ำหนัก และ ส่วนสูง
        w = self.cleaned_data.get('weight_kg')
        h = self.cleaned_data.get('height_cm')
        if w and h and h > 0:
            h_m = h / 100.0
            vitals_data['bmi'] = round(w / (h_m * h_m), 1)

        instance.vitals = vitals_data
        if commit:
            instance.save()
        return instance


class VisitVitalsForm(forms.Form):
    """
    สัญญาณชีพในการซักประวัติที่คลินิก: บังคับกรอกทุกช่อง และกันพิมพ์ผิดด้วยช่วงค่าที่เป็นไปได้
    ช่วงกว้างพอสำหรับผู้ป่วยจริง แต่ตัดค่าที่เป็นไปไม่ได้ (เช่น ใส่น้ำหนักในช่องความดัน)
    """
    RANGES = {
        'bp_systolic': (50, 260), 'bp_diastolic': (30, 160), 'pulse': (25, 230), 'temperature': (32, 43),
        'weight_kg': (1, 300), 'height_cm': (30, 250), 'spo2': (50, 100),
    }
    LABELS = {
        'bp_systolic': 'ความดันบน', 'bp_diastolic': 'ความดันล่าง', 'pulse': 'ชีพจร', 'temperature': 'อุณหภูมิ',
        'weight_kg': 'น้ำหนัก', 'height_cm': 'ส่วนสูง', 'spo2': 'ออกซิเจนปลายนิ้ว (SpO2)',
    }
    INTEGER_FIELDS = ('bp_systolic', 'bp_diastolic', 'pulse', 'spo2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, (low, high) in self.RANGES.items():
            field_class = forms.IntegerField if name in self.INTEGER_FIELDS else forms.FloatField
            self.fields[name] = field_class(
                label=self.LABELS[name], required=True, min_value=low, max_value=high,
                error_messages={
                    'required': f'กรุณากรอก{self.LABELS[name]}',
                    'invalid': f'{self.LABELS[name]}ต้องเป็นตัวเลข',
                    'min_value': f'{self.LABELS[name]}ต้องไม่ต่ำกว่า {low}',
                    'max_value': f'{self.LABELS[name]}ต้องไม่เกิน {high}',
                },
            )

    def clean(self):
        data = super().clean()
        sys_bp, dia_bp = data.get('bp_systolic'), data.get('bp_diastolic')
        if sys_bp is not None and dia_bp is not None and dia_bp >= sys_bp:
            self.add_error('bp_diastolic', 'ความดันล่างต้องน้อยกว่าความดันบน')
        return data

    def vitals(self) -> dict:
        """ค่าสำหรับ PatientHistory.vitals พร้อม BMI (เรียกหลัง is_valid)"""
        data = {name: self.cleaned_data[name] for name in self.RANGES}
        height_m = data['height_cm'] / 100.0
        data['bmi'] = round(data['weight_kg'] / (height_m * height_m), 1)
        return data

    def error_list(self) -> list:
        return [msg for errors in self.errors.values() for msg in errors]


class AppointmentForm(forms.Form):
    """
    สร้างนัดหมายจากหน้าปฏิทิน
    - ต้องเลือกแพทย์ผู้ตรวจ (เดิมระบบใส่ชื่อผู้กดสร้าง พยาบาลสร้างนัดเลยกลายเป็น "นพ./พญ. พยาบาล")
    - ห้ามนัดย้อนหลัง และห้ามชนคิวแพทย์คนเดียวกันในเวลาเดียวกัน / คนไข้คนเดิมเวลาเดิม
    """
    patient_id = forms.IntegerField(error_messages={'required': 'กรุณาเลือกคนไข้', 'invalid': 'กรุณาเลือกคนไข้จากรายการ'})
    doctor_id = forms.IntegerField(error_messages={'required': 'กรุณาเลือกแพทย์ผู้ตรวจ', 'invalid': 'กรุณาเลือกแพทย์ผู้ตรวจ'})
    appointment_date = forms.DateField(error_messages={'required': 'กรุณาเลือกวันที่นัด', 'invalid': 'วันที่นัดไม่ถูกต้อง'})
    appointment_time = forms.TimeField(error_messages={'required': 'กรุณาเลือกเวลานัด', 'invalid': 'เวลานัดไม่ถูกต้อง'})
    notes = forms.CharField(required=False, max_length=500,
                            error_messages={'max_length': 'จุดประสงค์การนัดยาวเกิน 500 ตัวอักษร'})

    def clean_patient_id(self):
        pk = self.cleaned_data['patient_id']
        self.patient = Patient.objects.filter(pk=pk).first()
        if self.patient is None:
            raise forms.ValidationError('ไม่พบคนไข้ที่เลือก')
        return pk

    def clean_doctor_id(self):
        from accounts.models import User
        pk = self.cleaned_data['doctor_id']
        self.doctor = User.objects.filter(pk=pk, role=User.Role.DOCTOR, is_active=True).first()
        if self.doctor is None:
            raise forms.ValidationError('ไม่พบแพทย์ที่เลือก')
        return pk

    def clean(self):
        from django.utils import timezone
        from patients.models import Appointment
        data = super().clean()
        day, at = data.get('appointment_date'), data.get('appointment_time')
        if day is None or at is None:
            return data
        now = timezone.localtime()
        if day < now.date() or (day == now.date() and at < now.time().replace(second=0, microsecond=0)):
            raise forms.ValidationError('ไม่สามารถนัดย้อนหลังได้ กรุณาเลือกวันและเวลาที่ยังไม่ผ่านมา')
        active = Appointment.objects.filter(appointment_date=day, appointment_time=at).exclude(status='cancelled')
        if getattr(self, 'doctor', None) and active.filter(doctor=self.doctor).exists():
            raise forms.ValidationError(f'แพทย์{self.doctor.get_full_name() or self.doctor.username} มีนัดเวลานี้แล้ว กรุณาเลือกเวลาอื่น')
        if getattr(self, 'patient', None) and active.filter(patient=self.patient).exists():
            raise forms.ValidationError('คนไข้รายนี้มีนัดวันและเวลานี้อยู่แล้ว')
        return data

    def error_list(self) -> list:
        return [msg for errors in self.errors.values() for msg in errors]
