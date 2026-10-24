# EP 8: Production Hardening, Docker Compose & Final Verification (การปิดผนึกความปลอดภัยระดับโปรดักชันและคอนเทนเนอร์)

## 1. ภาพรวมโมดูล (Module Overview)
โมดูลนี้ทำหน้าที่เป็นการเตรียมความพร้อมระดับโปรดักชัน (Production Hardening & Deployment Orchestration) สำหรับระบบการแพทย์แม่นยำ TSPI Monolith ทั้งระบบ เพื่อให้พร้อมสำหรับการใช้งานจริงในโรงพยาบาลและคลินิก โดยเปลี่ยนสถาปัตยกรรมจากสภาพแวดล้อมพัฒนาเข้าสู่ **Docker Compose Multi-Container Production Stack**:
1. **Container Security Isolation:** รันแอปพลิเคชันด้วยสิทธิ์ผู้ใช้ไม่ได้รับเอกสิทธิ์ (`appuser:appgroup` UID 1000) ป้องกัน Container Breakout
2. **PostgreSQL 16 Engine:** ฐานข้อมูลเชิงสัมพันธ์ที่เข้ารหัสการเชื่อมต่อ พร้อม Healthcheck และ Persistent Volume
3. **Redis 7 In-Memory Cache:** จัดการเซสชัน บันทึก Rate-Limiting และแคชการคำนวณ 39 แกน
4. **Nginx High-Performance Reverse Proxy:** ทำหน้าที่ TLS/SSL Termination, บีบอัด Gzip, ป้องกัน DoS ด้วย Rate Limiting และรองรับ SSE Streaming สำหรับ AI Copilot
5. **Automated Backup & Disaster Recovery:** สคริปต์สำรองข้อมูลอัตโนมัติพร้อมบีบอัด Gzip และหมุนเวียนลบสำเนาเก่า 7 วัน

---

## 2. Security Pillars & Iron Rules ที่ควบคุม
- **Pillar 1 (Unified Identity & Session Architecture):** รองรับ Argon2 Hasher, HttpOnly/SameSite Lax cookies และ 30-min Idle Timeout บน Gunicorn Production Workers
- **Pillar 4 (Strict CSP & Content Security):** ป้องกัน XSS ด้วยการปิดกั้น inline scripts ที่ไม่ปลอดภัย และใช้เฉพาะ Assets ภายในเครื่อง (Zero CDN Leak)
- **Pillar 5 (Relational Data Integrity):** ป้องกัน Race conditions และความไม่สมบูรณ์ของข้อมูลการแพทย์ด้วย PostgreSQL Foreign Keys และ Transactions
- **Pillar 6 (Production Environment Isolation):**
  - **ห้ามเปิด DEBUG ใน Production เด็ดขาด (`DEBUG = False`):** ระบบจะ Throw `ValueError` ทันทีหาก `DJANGO_SECRET_KEY` สั้นกว่า 50 ตัวอักษร หรือ `ALLOWED_HOSTS` มีเครื่องหมายดอกจัน `'*'`
  - **SSL/TLS Hardening:** บังคับ `SECURE_SSL_REDIRECT = True`, `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`, `SECURE_HSTS_SECONDS = 31536000` (1 ปี) และ `SECURE_HSTS_PRELOAD = True`
- **Pillar 7 (Rate Limiting & DoS Protection):**
  - Nginx Rate Limiting: กำหนดเพดาน `20 req/sec` สำหรับเส้นทางทั่วไป และ `5 req/sec` สำหรับจุดเข้าสู่ระบบ `/accounts/login/`
- **Pillar 8 (AuditLog Trail):** รวบรวม Logs ระดับ Production ในรูปแบบ `json_verbose` เพื่อส่งต่อไปยัง SIEM / CloudWatch / Datadog
- **Pillar 14 (Zero-Trust External APIs):** Webhook และ External APIs ทำงานผ่าน Reverse Proxy ที่แยกสัดส่วนชัดเจน

---

## 3. สถาปัตยกรรมระบบคอนเทนเนอร์ (Production Architecture)

```
[Clients / Doctor / Patients / LINE Webhook]
                     │
                     ▼
             [Nginx: Ports 80, 443]
             - Rate Limiting (20r/s general, 5r/s auth)
             - SSL/TLS Termination
             - Static (/static/) & Media (/media/) Caching
             - SSE Streaming (proxy_buffering off)
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
  [Static/Media Files]   [Django Gunicorn Web: Port 8000]
                         - appuser (Non-root UID 1000)
                         - Python 3.12 + WeasyPrint 70.0
                         - Gunicorn 3 Workers x 2 Threads
                         - Production Settings (DEBUG=False)
                         - Health Endpoint (/health/)
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       [PostgreSQL 16 Engine]             [Redis 7 Cache]
       - db:5432                          - redis:6379
       - Persistent Volume: postgres_data - Cache / Rate Limiting
       - Encrypted Connections            - Persistent Volume: redis_data
```

---

## 4. โครงสร้างไฟล์ที่สร้างและพัฒนา

| ตำแหน่งไฟล์ | คำอธิบายหน้าที่ |
|---|---|
| `Dockerfile` | Multi-stage Docker build รันด้วย Python 3.12-slim, ติดตั้งไลบรารี WeasyPrint C-libs, สร้าง user `appuser` (Non-root) |
| `entrypoint.sh` | สคริปต์เริ่มการทำงานของ Container: รอ PostgreSQL พร้อม, สั่ง migrate, collectstatic, และรัน Gunicorn |
| `docker-compose.yml` | แฟ้มคอมโพสโปรดักชัน ประกอบด้วย 4 เซอร์วิส: `db`, `redis`, `web`, `nginx` พร้อม Healthchecks และ Volumes |
| `nginx/nginx.conf` | คอนฟิกูเรชัน Nginx Reverse Proxy ป้องกัน DoS, แปะ Security Headers, แคช Static, และปิดบัฟเฟอร์สำหรับ SSE |
| `config/settings/prod.py` | การตั้งค่าระดับโปรดักชัน: บังคับ `DEBUG=False`, ตรวจความยาว Secret Key, บังคับ HTTPS/HSTS/Cookies |
| `requirements.txt` | อัปเดตแพ็กเกจระดับโปรดักชัน: เพิ่ม `gunicorn>=22.0.0` และ `redis>=5.0.0` |
| `apps/core/views.py` | เพิ่ม `health_check_view` ตอบกลับสถานะ `/health/` ตรวจสอบความสมบูรณ์ของฐานข้อมูล |
| `apps/core/urls.py` | ลงทะเบียนเส้นทาง `/health/` และ `/healthz/` สำหรับ Load Balancer และ Docker Healthcheck |
| `scripts/backup_db.sh` | สคริปต์อัตโนมัติสำรองฐานข้อมูล PostgreSQL ด้วย `pg_dump` บีบอัด `gzip -9` พร้อมหมุนเวียนลบ 7 วัน |
| `scripts/restore_db.sh` | สคริปต์กู้คืนฐานข้อมูลจากไฟล์สำรอง (Disaster Recovery Pipeline) |
| `apps/core/tests.py` | ชุดทดสอบตรวจสอบความถูกต้องของ `/health/` และข้อบังคับความปลอดภัยระดับ Production |

---

## 5. ผลการทดสอบ (Verification Checklist)
- [x] Dockerfile ผ่านการคอมไพล์แบบ Multi-stage ไม่มี Build Tools ส่วนเกินตกค้างใน Runtime
- [x] ผู้ใช้ในคอนเทนเนอร์เป็น `appuser` (Non-root UID 1000) 100%
- [x] คอนฟิกูเรชัน Nginx รองรับ HTTP/2, Static Cache 30 วัน, และปิด Buffer สำหรับ SSE Streaming
- [x] จุดตรวจสุขภาพ `/health/` คืนค่า HTTP 200 พร้อมสถานะ `healthy` และ `database: connected`
- [x] การตั้งค่า Production บังคับ `DEBUG = False` และตรวจสอบความยาว `DJANGO_SECRET_KEY` &ge; 50 ตัวอักษร
- [x] สคริปต์สำรองข้อมูลและกู้คืนข้อมูลทดสอบสิทธิ์รันและทำงานได้สมบูรณ์
- [x] ชุดทดสอบทั้งหมด 54/54 tests ผ่าน 100% (Pass Rate 100%)
