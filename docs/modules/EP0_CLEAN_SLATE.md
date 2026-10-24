# Module: EP0_CLEAN_SLATE (Clean Monolith Foundation & Security Isolation)

## ทำอะไร
- วางรากฐานโครงการใหม่แบบ **Pure Django + PostgreSQL Monolith** โดยไม่มี Node.js runtime 
- ติดตั้งและตั้งค่าเสาหลักความปลอดภัย (15 Security Pillars):
  1. **Argon2 Password Hasher** (`argon2-cffi`) แทนที่ PBKDF2
  2. **django-axes** ป้องกัน Brute-force Login (5 ครั้ง / 15 นาที -> Lockout)
  3. **Content Security Policy (CSP)** ผ่าน `django-csp`
  4. **Strict Session & Cookie Hardening**: HttpOnly, SameSite=Lax, 30 นาที Idle Expire
  5. **Custom User Model** (`accounts.User`) พร้อมระบบบทบาท (RBAC) 5 ระดับ (Admin, Doctor, Nurse, Staff, Patient)
  6. **AuditLog Model** สำหรับบันทึก Audit Trail ของระบบตามมาตรฐาน PDPA & HIPAA
  7. **Clean App Architecture**: แยกโดเมนแอปเป็น `accounts`, `patients`, `clinical`, `intelligence`, `portal_patient`, `core`
- เขียน Unit Test ตรวจสอบ Security Configuration (Argon2, RBAC, Axes) ผ่าน 100%

## ทำไมถึงทำแบบนี้
- **แก้ปัญหา Dual-Brain & Architecture Fragility**: ระบบเดิมของ Next.js มี API ซ้ำซ้อน มีการรั่วไหลของไฟล์ฐานข้อมูลใน `public/` และเสี่ยงต่อการหลุดของ Secret API Keys
- **Single Source of Truth**: รวมการทำงานทั้งหมดทั้ง UI, EMR Data, Business Logic, และ AI Orchestration เข้ามาไว้ใน Django เดียว เพื่อให้จัดการ ACID Transactions และ Permission ได้อย่างเบ็ดเสร็จ
- **เลือก Argon2**: เนื่องจากเป็นผู้ชนะเลิศ Password Hashing Competition มีคุณสมบัติ Memory-hard computational cost ป้องกันการใช้ GPU/ASIC แคร็กรหัสผ่านได้อย่างมีประสิทธิภาพสูงสุด

## โครงสร้างไฟล์
```text
/Users/tanchonl/Documents/tspiN/
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── urls.py
│   ├── wsgi.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py       # การตั้งค่าเสาหลักความปลอดภัย (Argon2, CSP, Axes, Cookies)
│       ├── dev.py        # การตั้งค่า Local Development
│       └── prod.py       # การตั้งค่า Production (HSTS 1 ปี, SSL Redirect, Strict Hosts)
├── apps/
│   ├── accounts/         # Custom User, RBAC Roles, AuditLog Model & Security Tests
│   ├── patients/         # Patient EMR & Clinical Records
│   ├── clinical/         # 39 Axes Engine & Report Release State
│   ├── intelligence/     # AI Physician & Streaming Copilot
│   ├── portal_patient/   # พอร์ทัลคนไข้และบริการตนเอง
│   └── core/             # Landing Page, Base Layout & Static Assets
├── templates/
│   ├── base.html         # โครงสร้างพื้นฐาน Dark Theme
│   └── core/
│       └── home.html     # หน้าแรกของระบบ
├── static/               # Assets และไอคอน
├── media/                # เอกสารการแพทย์ที่ปลอดภัย
├── docs/
│   └── modules/
│       └── EP0_CLEAN_SLATE.md
├── manage.py
├── requirements.txt
├── .gitignore
├── .env.example
└── .env
```

## จุดที่ต้องระวัง
- ⚠️ **AUTH_USER_MODEL Lock**: เนื่องจากกำหนด `AUTH_USER_MODEL = 'accounts.User'` ตั้งแต่เริ่มต้น ห้ามเปลี่ยนชื่อ Model หลังจากนี้เด็ดขาดเพราะจะกระทบ ForeignKey ทั้งระบบ
- ⚠️ **PostgreSQL vs SQLite ใน Dev**: หากรันเทสบนเครื่องที่ยังไม่ได้เปิด PostgreSQL Server ให้ใช้ Flag `USE_SQLITE=True` ใน Environment
- ⚠️ **Production Environment**: บน Production ต้องตั้งค่า `DEBUG=False` และ `DJANGO_SECRET_KEY` ต้องยาวเกิน 50 ตัวอักษรตามเงื่อนไขใน `prod.py`

## อ้างอิง
- OWASP Top 10:2021 (A01 Broken Access Control, A02 Cryptographic Failures, A07 Identification and Authentication Failures)
- Django Documentation: Customizing authentication in Django & Password Management
- django-axes Documentation & RFC 9106 (Argon2 Password Hashing Function)
