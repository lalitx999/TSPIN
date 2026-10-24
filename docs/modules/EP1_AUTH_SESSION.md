# Module: EP1_AUTH_SESSION (Unified Authentication, Session & Authorization Engine)

## ทำอะไร
- สร้างระบบยืนยันตัวตนและการจัดการเซสชันรวมศูนย์ (Unified Session Auth) ภายใต้โดเมนเดียว ไร้ปัญหา CORS และ Token รั่วไหล
- พัฒนาระบบพอร์ทัลเข้าสู่ระบบแยก 2 ด้าน:
  1. **Doctor / Clinical Staff Portal (`/accounts/doctor/login/`)**: ล็อกอินสำหรับแพทย์และเจ้าหน้าที่ บังคับ Role Gate สกัดไม่ให้บัญชีคนไข้เข้ามาล็อกอินได้
  2. **Patient Portal (`/accounts/patient/login/`)**: ล็อกอินสำหรับคนไข้ด้วยเลขบัตรประชาชน 13 หลัก หรือ HN คู่กับรหัสผ่าน
- พัฒนาระบบลงทะเบียนคนไข้ใหม่ (`/accounts/patient/register/`) พร้อมระบบตรวจสอบ:
  - **Thai National ID Checksum**: ตรวจสอบสูตรคำนวณ Modulo 11 ของเลขบัตรประชาชนไทย 13 หลัก
  - **Password Strength**: บังคับความยาวขั้นต่ำ 12 ตัวอักษร
  - **PDPA Consent Gate**: บังคับเซ็นยินยอมก่อนบันทึกข้อมูล
  - **SHA-256 Hashing**: เก็บแฮชของเลขบัตรประชาชนลง `id_card_hash`
- พัฒนา **IdleSessionTimeoutMiddleware**:
  - ตัดการเชื่อมต่ออัตโนมัติเมื่อไม่มีกิจกรรม (Idle) เกิน 30 นาที
  - ตัดการเชื่อมต่อเมื่อเซสชันมีอายุเกินเพดานสูงสุด 12 ชั่วโมง (Absolute Ceiling)
- พัฒนา **Role Authorization Decorators**:
  - `@role_required(*allowed_roles)`
  - `@clinical_staff_required` (Doctor, Nurse, Admin)
  - `@doctor_only` (สำหรับแพทย์ลงนามอนุมัติรายงาน)
  - ปฏิเสธด้วย HTTP 403 Forbidden พร้อมบันทึก `AuditLog`
- ระบบป้องกันการโจมตีระดับเซสชัน:
  - **Session Fixation Prevention**: หมุนเวียนคีย์เซสชันทันทีหลังล็อกอิน (`request.session.cycle_key()`)
  - **Session Flushing**: ล้างเซสชันอย่างหมดจดเมื่อล็อกเอาต์ (`request.session.flush()`)
  - **Rate Limiting (Pillar 7)**: จำกัดการล็อกอิน 5 ครั้ง/นาที/IP และลงทะเบียน 3 ครั้ง/ชั่วโมง/IP ผ่าน `django-ratelimit`
  - **Brute-Force Lockout (Pillar 1)**: ผสาน `django-axes` ล็อกเอาต์ 15 นาทีเมื่อกรอกผิด 5 ครั้ง พร้อมหน้าแจ้งเตือน `lockout.html`
- สร้าง Custom Error Templates ป้องกันข้อมูลรั่วไหล: `403.html`, `404.html`, `500.html`
- เขียน Security Unit Tests ครอบคลุม 8/8 เคส ผ่าน 100%

## ทำไมถึงทำแบบนี้
- **ตัดขาดปัญหา JWT & LocalStorage ของ Next.js**: การเก็บ Token ใน `localStorage` เสี่ยงต่อการถูกขโมยผ่าน XSS และมีปัญหาเมื่อรันใน SSR การเปลี่ยนมาใช้ Django Session + HttpOnly Cookies ปลอดภัยกว่าตามมาตรฐานความปลอดภัยการแพทย์ระดับสากล
- **ป้องกัน Privilege Escalation (การยกระดับสิทธิ์)**: คนไข้ไม่สามารถแอบอ้างเข้าหน้าจอของแพทย์ได้แม้จะรู้รหัสผ่าน เพราะมีการตรวจ Role Gate ทั้งใน Form และ Decorator
- **Session Fixation Defense**: หากผู้โจมตีแอบส่ง Session ID ล่วงหน้ามาให้เหยื่อ เมื่อเหยื่อล็อกอินสำเร็จ ระบบจะหมุนเวียนคีย์ใหม่ทันที ทำให้ Session ID เดิมของผู้โจมตีใช้การไม่ได้

## โครงสร้างไฟล์
```text
/Users/tanchonl/Documents/tspiN/
├── apps/
│   ├── accounts/
│   │   ├── forms.py          # DoctorLoginForm, PatientLoginForm, PatientRegistrationForm
│   │   ├── decorators.py     # @role_required, @clinical_staff_required, @doctor_only
│   │   ├── middleware.py     # IdleSessionTimeoutMiddleware (30m idle / 12h absolute)
│   │   ├── views.py          # doctor_login, patient_login, patient_register, logout, lockout
│   │   ├── urls.py           # /accounts/doctor/login/, /accounts/patient/login/, etc.
│   │   ├── models.py         # User(AbstractUser) RBAC 5 ระดับ, AuditLog
│   │   └── tests.py          # 8 Comprehensive Security Tests (100% PASS)
│   ├── patients/
│   │   └── views.py          # doctor_dashboard (ป้องกันด้วย @clinical_staff_required)
│   └── portal_patient/
│       └── views.py          # patient_dashboard (ป้องกันด้วย @login_required)
├── templates/
│   ├── accounts/
│   │   ├── doctor_login.html     # หน้าเข้าสู่ระบบแพทย์ Dark Theme
│   │   ├── patient_login.html    # หน้าเข้าสู่ระบบคนไข้
│   │   ├── patient_register.html # หน้าลงทะเบียนคนไข้ + PDPA Checkbox
│   │   └── lockout.html          # หน้าแจ้งเตือนเมื่อถูกระงับ 15 นาที
│   ├── patients/dashboard.html
│   ├── portal_patient/dashboard.html
│   ├── 403.html
│   ├── 404.html
│   └── 500.html
└── docs/modules/
    └── EP1_AUTH_SESSION.md
```

## จุดที่ต้องระวัง
- ⚠️ **Axes Request Dependency**: ฟังก์ชัน `authenticate()` ภายใต้ `django-axes` ต้องได้รับ `request=request` เป็นพารามิเตอร์เสมอ มิฉะนั้น Axes จะไม่สามารถตรวจจับ IP และดักจับ Brute-force ได้
- ⚠️ **Session Inactivity Header**: ระบบบันทึก `last_activity` ใน Session ทุก Request หากมีการเปิดใช้ Ajax Polling ถี่ๆ อาจทำให้ Session ไม่หมดอายุตามเวลาที่แท้จริง (ต้องไม่นับ Request ประเภท Polling/Heartbeat เข้าสู่ last_activity)

## อ้างอิง
- OWASP Session Management Cheat Sheet
- OWASP Top 10:2021 (A01 Broken Access Control, A07 Identification and Authentication Failures)
- กรมการปกครอง กระทรวงมหาดไทย: มาตรฐานสูตรคำนวณเลขประจำตัวประชาชนไทย Modulo 11
- RFC 9106: Argon2 Password Hashing Standard
