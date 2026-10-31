# คู่มือนำ TSPI Clinical EMR ขึ้น VPS

## 0. สิ่งที่ต้องมี

| รายการ | ขั้นต่ำที่แนะนำ |
|---|---|
| VPS | Ubuntu 24.04 LTS, 2 vCPU, RAM 4 GB, ดิสก์ 40 GB ขึ้นไป (WeasyPrint + Postgres + AI service) |
| โดเมน | เช่น `emr.your-clinic.com` ตั้ง DNS แบบ **A record** ชี้ไปที่ IP ของ VPS |
| พอร์ตที่เปิด | 22 (SSH), 80, 443 เท่านั้น |
| อีเมล | สำหรับแจ้งเตือนใบรับรอง Let's Encrypt |

> ⚠️ ระบบนี้เก็บข้อมูลสุขภาพ (PDPA) — เลือกผู้ให้บริการ VPS ที่ตั้งเซิร์ฟเวอร์ในไทยหรือมีสัญญาประมวลผลข้อมูล (DPA) และเปิดการเข้ารหัสดิสก์ถ้ามี

---

## 1. เตรียมเครื่อง (ครั้งแรก)

```bash
ssh root@<IP ของ VPS>
apt update && apt upgrade -y
apt install -y git curl ufw
curl -fsSL https://get.docker.com | sh
ufw allow 22 && ufw allow 80 && ufw allow 443 && ufw --force enable
adduser tspi && usermod -aG docker tspi
```

ล็อกอินใหม่เป็นผู้ใช้ `tspi` แล้วดึงโค้ด:

```bash
git clone https://github.com/lalitx999/TSPIN.git ~/tspi
cd ~/tspi
```

---

## 2. ตั้งค่า `.env` บน VPS

```bash
cp .env.example .env
python3 -m pip install --user cryptography   # ถ้ายังไม่มี (ใช้แค่สร้างคีย์)
python3 scripts/generate_secrets.py
```

คัดลอกค่าที่พิมพ์ออกมาใส่ `.env` แล้วแก้ค่าต่อไปนี้:

```
DJANGO_ENV=production
DEBUG=False
DOMAIN=emr.your-clinic.com
ALLOWED_HOSTS=emr.your-clinic.com
LETSENCRYPT_EMAIL=you@your-clinic.com
DB_NAME=tspi
DB_USER=tspi
# DB_PASSWORD, DJANGO_SECRET_KEY, INTERNAL_API_TOKEN, FERNET_KEY มาจาก generate_secrets.py
LINE_CHANNEL_SECRET=...      LINE_CHANNEL_ACCESS_TOKEN=...      LINE_LIFF_ID=...
EMAIL_HOST_USER=...          EMAIL_HOST_PASSWORD=...           (Hostinger SMTP)
GROQ_API_KEY=... (และ AI key อื่นตามที่ใช้)
AI_PRICE_THB_PER_1M_INPUT_GROQ=...  AI_PRICE_THB_PER_1M_OUTPUT_GROQ=...  (ราคาตามประกาศผู้ให้บริการ)
```

```bash
chmod 600 .env
```

> ห้าม commit `.env` และห้ามส่งค่าในแชท ไฟล์ `.dockerignore` กันไม่ให้ `.env` ติดไปใน image แล้ว

---

## 3. เปิดระบบ + ขอ HTTPS

```bash
docker compose build
docker compose up -d db redis ai web
./scripts/init_tls.sh
docker compose up -d
```

- ทดลองก่อนได้ด้วย `STAGING=1 ./scripts/init_tls.sh` (ใบทดสอบ ไม่ติด rate limit ของ Let's Encrypt) แล้วค่อยรันแบบปกติ
- ใบรับรองต่ออายุเองทุก 12 ชม. (service `certbot`) และ nginx โหลดใบใหม่ทุก 6 ชม.

ตรวจ: เปิด `https://<DOMAIN>/health/` ต้องได้ `{"status": "healthy", ...}`

สร้างบัญชีเจ้าของระบบ (owner):

```bash
docker compose exec web python manage.py createsuperuser
```

---

## 4. ย้ายข้อมูลจากเครื่องพัฒนา (ถ้าต้องการ)

**บนเครื่องเดิม (Mac):**

```bash
pg_dump -Fc -h 127.0.0.1 -U postgres drpatrcl_sys > tspi.dump
tar -czf private_media.tgz private_media
scp tspi.dump private_media.tgz tspi@<IP>:~/tspi/
```

**บน VPS:**

```bash
docker compose cp tspi.dump db:/tmp/tspi.dump
docker compose exec db pg_restore -U tspi -d tspi --no-owner --clean --if-exists /tmp/tspi.dump
docker run --rm -v tspi_private_media:/data -v "$PWD":/src alpine sh -c "tar -xzf /src/private_media.tgz -C /data --strip-components=1"
docker compose exec web python manage.py migrate
rm tspi.dump private_media.tgz
```

> ชื่อ volume จริงดูได้จาก `docker volume ls` (มักขึ้นต้นด้วยชื่อโฟลเดอร์ เช่น `tspi_private_media`)

**ข้อมูลที่เข้ารหัส (เลขบัตร ปชช., ไฟล์ LINE)** บนเครื่องเดิมเข้ารหัสด้วยคีย์ที่ได้จาก `SECRET_KEY` เดิม ต้องให้ VPS อ่านได้แล้วหมุนเป็นคีย์ใหม่:

```bash
python3 scripts/generate_secrets.py --old-secret-key '<SECRET_KEY ของเครื่องเดิม>'
```

นำบรรทัด `FERNET_OLD_KEYS=...` ใส่ `.env` บน VPS แล้ว:

```bash
docker compose up -d web
docker compose exec web python manage.py rotate_encryption_key           # dry-run
docker compose exec web python manage.py rotate_encryption_key --apply
```

ลบ `FERNET_OLD_KEYS` ออกจาก `.env` แล้ว `docker compose up -d web`

> เครื่องพัฒนาที่ไม่ได้ตั้ง `DJANGO_SECRET_KEY` ใช้ค่าเริ่มต้นใน `config/settings/dev.py`

---

## 5. ตั้ง LINE OA

ใน LINE Developers Console ของ channel ที่จะใช้:
- **Webhook URL:** `https://<DOMAIN>/line/webhook/` → กด Verify → เปิด Use webhook
- **LIFF (ใน channel แบบ LINE Login):** Endpoint URL `https://<DOMAIN>/liff/bind/`, Scope `openid profile`, Size Full → คัดลอก LIFF ID ใส่ `LINE_LIFF_ID`

> ⚠️ บอท Doctorpatt ตัวจริงยังชี้ webhook ไปที่ระบบเดิม เปลี่ยนเมื่อพร้อมย้ายจริงเท่านั้น (ข้อความผู้ป่วยจะไหลมาระบบใหม่ทันที)

---

## 6. งานประจำ

| งาน | คำสั่ง |
|---|---|
| อัปเดตเวอร์ชัน | `./scripts/deploy.sh` (สำรอง DB → pull → build → up → ตรวจ /health/) |
| สำรองข้อมูล | `./scripts/backup_db.sh` (DB + ไฟล์ทางคลินิก, เก็บ 7 วัน) |
| ตั้ง backup อัตโนมัติ | `crontab -e` → `0 2 * * * cd ~/tspi && ./scripts/backup_db.sh >> logs/backup.log 2>&1` |
| ดู log | `docker compose logs -f --tail=100 web` |
| เข้า shell Django | `docker compose exec web python manage.py shell` |

> ⚠️ ไฟล์ backup อยู่บน VPS เครื่องเดียวกัน ควรคัดลอกออกไปเก็บที่อื่น (เช่น object storage ที่เข้ารหัส) อย่างน้อยวันละครั้ง และต้องเก็บ `FERNET_KEY` ไว้ด้วย ไม่งั้นกู้ข้อมูลที่เข้ารหัสไม่ได้
