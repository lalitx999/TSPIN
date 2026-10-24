# Module: EP2_BASE_LAYOUT (Modern Monolith Layout & Design System)

## ทำอะไร
- สร้างโครงสร้าง Base Layout และ Design System ระดับมืออาชีพ 3 โซนหลัก:
  1. **`layouts/doctor_base.html` (Doctor Portal)**:
     - ใช้ **AdminLTE 4 (Dark Mode)** คมชัด เรียบหรู
     - แถบเมนูด้านข้าง (Sidebar) ครบถ้วน 4 หมวดหมู่ (เวชระเบียน, กลไก 39 แกน, AI การแพทย์, รายงานและการกำกับดูแล)
     - แถบบน (Navbar) แสดงชื่อแพทย์, ป้าย Role Badge, และเมนูออกจากระบบ
  2. **`layouts/patient_base.html` (Patient Portal)**:
     - ออกแบบรองรับ **Mobile-First Responsive Shell**
     - แถบเมนูด้านล่าง (Bottom Navigation Bar) สำหรับเปิดบนสมาร์ทโฟน
     - สไตล์สีเขียวมรกต (Emerald Healthcare Tone) สบายตา เป็นมิตรกับผู้รับบริการ
  3. **`layouts/public_base.html` (Public Landing & Legal)**:
     - หน้าแรกแนะนำคลินิก (`/`), เกี่ยวกับคลินิก (`/about/`), นโยบายคุ้มครองข้อมูลส่วนบุคคล (`/legal/privacy/`), และข้อตกลงการใช้บริการ (`/legal/terms/`)
- ติดตั้งและตั้งค่า Asset ภายในระบบแบบ **Zero CDN Dependency**:
  - **HTMX 2.0.4** ติดตั้งในเครื่อง (`static/vendor/htmx/htmx.min.js`)
  - **Alpine.js 3.14** ติดตั้งในเครื่อง (`static/vendor/alpine/alpine.min.js`)
  - **Offline Thai Fonts (Sarabun)** สำหรับ UI และระบบ WeasyPrint PDF
  - **FontAwesome Free & AdminLTE 4 Plugins** (Bootstrap, OverlayScrollbars, Chart.js)
- ติดตั้งระบบส่ง **CSRF Token อัตโนมัติในทุกคำขอ HTMX (`X-CSRFToken`)** ตาม Pillar 4
- เขียนชุดทดสอบ Layout & Template Rendering ใน `apps/core/tests.py` ผ่าน 100%

## ทำไมถึงทำแบบนี้
- **Zero External CDN Dependencies (Pillar 4 & 11)**: การโหลด JavaScript จาก CDN ภายนอก เสี่ยงต่อการถูกโจมตีแบบ Supply Chain Attack และขัดต่อนโยบาย Content Security Policy (CSP) ที่เข้มงวด การเก็บไฟล์แบบ Local Vendor ทำให้ระบบรัน Offline ได้และปลอดภัยสูงสุด
- **หน้าตาเดิม 100% (No UI Downgrade)**: นำเข้า AdminLTE 4 และชุดไอคอนชุดเดิมจาก Next.js เดิมมาใช้บน Django Template ทำให้ผู้ใช้งาน (แพทย์และคนไข้) ได้หน้าจอที่คุ้นเคย สวยงาม คมชัด และโหลดได้เร็วกว่าเดิม

## โครงสร้างไฟล์
```text
/Users/tanchonl/Documents/tspiN/
├── templates/
│   ├── base.html                     # Master HTML Shell (Local Fonts, HTMX, CSRF Config)
│   ├── layouts/
│   │   ├── doctor_base.html          # โครงหน้าจอแพทย์ AdminLTE 4 Dark Mode
│   │   ├── patient_base.html         # โครงหน้าจอคนไข้ Mobile-First
│   │   └── public_base.html          # โครงหน้าจอสาธารณะ
│   ├── core/
│   │   ├── home.html                 # หน้าแรก Landing Page
│   │   ├── about.html                # เกี่ยวกับคลินิก TSPI
│   │   ├── privacy.html              # นโยบาย PDPA
│   │   └── terms.html                # ข้อตกลงการใช้งาน
│   ├── patients/
│   │   └── dashboard.html            # Doctor Dashboard (สวม Doctor Base Layout)
│   └── portal_patient/
│       └── dashboard.html            # Patient Dashboard (สวม Patient Base Layout)
├── static/
│   ├── fonts/                        # Sarabun TTF Fonts
│   ├── vendor/
│   │   ├── htmx/htmx.min.js          # Local HTMX 2.0.4
│   │   ├── alpine/alpine.min.js      # Local Alpine.js 3.14
│   │   └── adminlte/                 # AdminLTE 4 CSS/JS/Plugins
├── apps/
│   └── core/
│       ├── views.py, urls.py
│       └── tests.py                  # 6 Layout & Template Rendering Tests (100% PASS)
└── docs/modules/
    └── EP2_BASE_LAYOUT.md
```

## จุดที่ต้องระวัง
- ⚠️ **HTMX CSRF Injection**: เมื่อเรียกใช้งาน HTMX กับ Endpoint แบบ POST/PUT/DELETE ต้องแน่ใจว่า Event Listener `htmx:configRequest` ถูกผูกไว้ที่ `document.body` เสมอ มิฉะนั้น Django CsrfViewMiddleware จะปฏิเสธคำขอด้วย HTTP 403 Forbidden
- ⚠️ **Static Files Caching**: ในขั้นตอน Production การอัปเดตไฟล์ CSS/JS ควรกำหนด Versioning หรือเปิดใช้ `ManifestStaticFilesStorage` เพื่อป้องกันปัญหา Browser Cache ค้าง

## อ้างอิง
- Content Security Policy (CSP) Level 3 Specification (W3C)
- HTMX Security & Best Practices Documentation
- AdminLTE 4 Architecture & Bootstrap 5 Guidelines
