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
            'allergies', 'chief_complaint', 'medical_history'
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
            'medical_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'โรคประจำตัว การผ่าตัด ยาที่ใช้อยู่'}),
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
