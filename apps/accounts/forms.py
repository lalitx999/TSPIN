"""
Forms for Authentication & Registration (Pillars 1, 2, 3).
Enforces Strict Input Validation, Role Filtering, and Clean Methods.
"""

import re
from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

def validate_thai_id_card(id_card_str: str) -> bool:
    """
    ตรวจสอบความถูกต้องของเลขบัตรประชาชนไทย 13 หลักด้วย Modulo 11 Checksum
    """
    id_card = id_card_str.strip().replace('-', '').replace(' ', '')
    if len(id_card) != 13 or not id_card.isdigit():
        return False
    
    # คำนวณ Checksum ตามมาตรฐานกรมการปกครอง
    total = sum(int(id_card[i]) * (13 - i) for i in range(12))
    check_digit = (11 - (total % 11)) % 10
    return check_digit == int(id_card[12])


class DoctorLoginForm(forms.Form):
    """
    ฟอร์มเข้าสู่ระบบสำหรับแพทย์และบุคลากรทางการแพทย์ (Staff Portal)
    """
    email_or_username = forms.CharField(
        label="อีเมลหรือชื่อผู้ใช้",
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'doctor@tspi.clinic หรือ Username',
            'autocomplete': 'username',
            'required': True,
        })
    )
    password = forms.CharField(
        label="รหัสผ่าน",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'กรอกรหัสผ่านของคุณ',
            'autocomplete': 'current-password',
            'required': True,
        })
    )

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get('email_or_username', '').strip()
        password = cleaned_data.get('password', '')

        if not identifier or not password:
            return cleaned_data

        # รองรับการระบุทั้ง Email และ Username
        user = None
        if '@' in identifier:
            matched_user = User.objects.filter(email__iexact=identifier).first()
            if matched_user:
                user = authenticate(request=self.request, username=matched_user.username, password=password)
        else:
            user = authenticate(request=self.request, username=identifier, password=password)

        if not user:
            raise ValidationError("อีเมล/ชื่อผู้ใช้ หรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง")

        if not user.is_active:
            raise ValidationError("บัญชีนี้ถูกระงับการใช้งานชั่วคราว กรุณาติดต่อผู้ดูแลระบบ")

        # ⚠️ Role Gate: คนไข้ไม่สามารถล็อกอินผ่านช่องทางบุคลากรทางการแพทย์ได้
        if not user.is_clinical_staff:
            raise ValidationError("คุณไม่มีสิทธิ์เข้าถึงพอร์ทัลบุคลากรทางการแพทย์ (กรุณาใช้พอร์ทัลคนไข้)")

        cleaned_data['user'] = user
        return cleaned_data


class PatientLoginForm(forms.Form):
    """
    ฟอร์มเข้าสู่ระบบสำหรับคนไข้ (Patient Portal)
    """
    identifier = forms.CharField(
        label="เลขบัตรประชาชน 13 หลัก หรือ HN",
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ระบุเลขบัตรประชาชน 13 หลัก หรือ หมายเลข HN',
            'autocomplete': 'username',
            'required': True,
        })
    )
    password = forms.CharField(
        label="รหัสผ่าน",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'รหัสผ่านของคุณ',
            'autocomplete': 'current-password',
            'required': True,
        })
    )

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get('identifier', '').strip().replace('-', '').replace(' ', '')
        password = cleaned_data.get('password', '')

        if not identifier or not password:
            return cleaned_data

        user = authenticate(request=self.request, username=identifier, password=password)
        if not user:
            raise ValidationError("ข้อมูลประจำตัวหรือรหัสผ่านไม่ถูกต้อง")

        if not user.is_active:
            raise ValidationError("บัญชีผู้ป่วยถูกปิดการใช้งาน กรุณาติดต่อคลินิก")

        # บังคับว่าต้องเป็น Role Patient
        if user.role != User.Role.PATIENT:
            raise ValidationError("บัญชีเจ้าหน้าที่กรุณาเข้าสู่ระบบผ่านช่องทางแพทย์")

        cleaned_data['user'] = user
        return cleaned_data


class PatientRegistrationForm(forms.ModelForm):
    """
    ฟอร์มลงทะเบียนคนไข้ใหม่ พร้อมตรวจสอบความถูกต้องของข้อมูล (Input Validation - Pillar 3)
    """
    id_card = forms.CharField(
        label="เลขประจำตัวประชาชน 13 หลัก",
        max_length=17,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'X-XXXX-XXXXX-XX-X',
            'required': True,
        })
    )
    phone = forms.CharField(
        label="เบอร์โทรศัพท์มือถือ",
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0812345678',
            'required': True,
        })
    )
    password = forms.CharField(
        label="กำหนดรหัสผ่าน (ขั้นต่ำ 12 ตัวอักษร)",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'ความยาวอย่างน้อย 12 ตัวอักษร',
            'autocomplete': 'new-password',
            'required': True,
        })
    )
    confirm_password = forms.CharField(
        label="ยืนยันรหัสผ่านอีกครั้ง",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'ยืนยันรหัสผ่านเดิม',
            'autocomplete': 'new-password',
            'required': True,
        })
    )
    pdpa_accepted = forms.BooleanField(
        label="ข้าพเจ้ายินยอมให้นำข้อมูลสุขภาพไปใช้ในการวิเคราะห์ทางการแพทย์ตามนโยบาย PDPA",
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'required': True}),
        }

    def clean_id_card(self):
        raw_id = self.cleaned_data.get('id_card', '').strip().replace('-', '').replace(' ', '')
        if not validate_thai_id_card(raw_id):
            raise ValidationError("เลขประจำตัวประชาชน 13 หลักไม่ถูกต้องตามสูตรคำนวณมาตรฐาน")
        
        # ตรวจสอบว่ามีผู้ใช้นี้อยู่แล้วหรือไม่
        if User.objects.filter(username=raw_id).exists():
            raise ValidationError("เลขบัตรประชาชนนี้ได้ลงทะเบียนไว้ในระบบแล้ว กรุณาเข้าสู่ระบบ")
            
        return raw_id

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip().replace('-', '').replace(' ', '')
        if not re.match(r'^0[689]\d{8}$', phone):
            raise ValidationError("กรุณาระบุหมายเลขโทรศัพท์มือถือไทยที่ถูกต้อง (เช่น 0812345678)")
        return phone

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 12:
            raise ValidationError("รหัสผ่านต้องมีความยาวอย่างน้อย 12 ตัวอักษรตามมาตรฐานความปลอดภัย")
        return password

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "รหัสผ่านทั้งสองช่องไม่ตรงกัน")
        return cleaned_data
