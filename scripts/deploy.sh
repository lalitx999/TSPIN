#!/bin/bash
# ==============================================================================
# อัปเดตระบบบน VPS: ดึงโค้ดล่าสุด -> build -> เปิดใหม่ (entrypoint รัน migrate + collectstatic ให้)
#   ./scripts/deploy.sh
# ==============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

echo "[Deploy] 1/5 สำรองฐานข้อมูลก่อนอัปเดต"
./scripts/backup_db.sh

echo "[Deploy] 2/5 ดึงโค้ดล่าสุด"
git pull --ff-only

echo "[Deploy] 3/5 build image"
docker compose build web ai

echo "[Deploy] 4/5 เปิด service ใหม่"
docker compose up -d

echo "[Deploy] 5/5 ตรวจสุขภาพระบบ"
DOMAIN=$(grep -E '^DOMAIN=' .env | cut -d= -f2-)
for i in $(seq 1 30); do
    if curl -fsS "https://${DOMAIN}/health/" >/dev/null 2>&1; then
        echo "[Deploy] เรียบร้อย: https://${DOMAIN}"
        docker compose ps
        exit 0
    fi
    sleep 2
done
echo "[Deploy] ระบบยังไม่ตอบ /health/ ดู log: docker compose logs --tail=100 web" >&2
exit 1
