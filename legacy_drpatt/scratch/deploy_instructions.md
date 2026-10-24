# 🚀 คู่มือการนำ Backend ขึ้น Home Server และ Vercel Frontend (Updated URL & Ingress)

### 📍 1. Cloudflare Ingress Config (`~/.cloudflared/config.yml`)

ไฟล์ `config.yml` ฉบับแก้ไขสมบูรณ์บน Home Server:

```yaml
tunnel: tanchonserver
credentials-file: /home/ttstudio-service/.cloudflared/d0cc84bc-dc07-4a50-88b3-849b05e9eb55.json

ingress:
  # ---- Core Services ----
  - hostname: tanchonhomserverxxx.online
    service: http://localhost:9000
  - hostname: home.tanchonhomserverxxx.online
    service: http://localhost:8000

  # ---- Backend APIs ----
  - hostname: app1.tanchonhomserverxxx.online
    service: http://localhost:8005
  - hostname: app2.tanchonhomserverxxx.online
    service: http://localhost:8006
  - hostname: app9.tanchonhomserverxxx.online
    service: http://localhost:3000
  - hostname: tspi-backend.tanchonhomserverxxx.online
    service: http://localhost:8012

  # ---- Web Apps ----
  - hostname: app3.tanchonhomserverxxx.online
    service: http://localhost:8080
  - hostname: app4.tanchonhomserverxxx.online
    service: http://localhost:8082
  - hostname: app5.tanchonhomserverxxx.online
    service: http://localhost:8084
  - hostname: app6.tanchonhomserverxxx.online
    service: http://localhost:9000
  - hostname: app7.tanchonhomserverxxx.online
    service: https://localhost:9443

  # ---- Database ----
  - hostname: db.tanchonhomserverxxx.online
    service: http://localhost:5432
  - hostname: mysql.tanchonhomserverxxx.online
    service: http://localhost:3306

  # ---- SSH ----
  - hostname: ssh.tanchonhomserverxxx.online
    service: ssh://localhost:22

  # ---- Default ----
  - service: http_status:404
```

---

### 📍 2. LINE Webhook Configuration

นำ URL ใหม่ไปกรอกใน **LINE Developer Console**:
- **Webhook URL:** `https://tspi-backend.tanchonhomserverxxx.online/api/line/webhook/`
- กด **Verify** และสับสวิตช์ **Use Webhook** เป็น **ON**

---

### 📍 3. Vercel Frontend Configuration

นำ Frontend ขึ้น Vercel และตั้งค่า Environment Variables:
```env
NEXT_PUBLIC_API_URL=https://tspi-backend.tanchonhomserverxxx.online
```
