#!/bin/bash
# ==============================================================================
# ขอใบรับรอง HTTPS (Let's Encrypt) ครั้งแรกบน VPS
# ต้องตั้ง DNS ของ DOMAIN ให้ชี้มาที่ IP ของ VPS ก่อน และเปิดพอร์ต 80/443
#
#   ./scripts/init_tls.sh            # ใบจริง
#   STAGING=1 ./scripts/init_tls.sh  # ทดลองกับเซิร์ฟเวอร์ทดสอบของ Let's Encrypt (ไม่ติด rate limit)
#
# หลังจากนี้ service certbot ใน docker-compose จะต่ออายุให้อัตโนมัติ
# ==============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

DOMAIN=$(grep -E '^DOMAIN=' .env | cut -d= -f2-)
EMAIL=$(grep -E '^LETSENCRYPT_EMAIL=' .env | cut -d= -f2-)
if [ -z "${DOMAIN}" ] || [ -z "${EMAIL}" ]; then
    echo "ต้องตั้ง DOMAIN และ LETSENCRYPT_EMAIL ใน .env ก่อน" >&2
    exit 1
fi
LIVE="/etc/letsencrypt/live/${DOMAIN}"

echo "[TLS] 1/5 สร้างใบรับรองชั่วคราว เพื่อให้ nginx เปิดได้"
docker compose run --rm --entrypoint sh certbot -c "
  apk add --no-cache openssl >/dev/null 2>&1;
  mkdir -p ${LIVE} &&
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout ${LIVE}/privkey.pem -out ${LIVE}/fullchain.pem -subj '/CN=localhost' >/dev/null 2>&1"

echo "[TLS] 2/5 เปิด nginx"
docker compose up -d nginx

echo "[TLS] 3/5 ลบใบชั่วคราว"
docker compose run --rm --entrypoint sh certbot -c "
  rm -rf /etc/letsencrypt/live/${DOMAIN} /etc/letsencrypt/archive/${DOMAIN} /etc/letsencrypt/renewal/${DOMAIN}.conf"

echo "[TLS] 4/5 ขอใบจริงจาก Let's Encrypt สำหรับ ${DOMAIN}"
STAGING_ARG=""
if [ "${STAGING:-0}" = "1" ]; then STAGING_ARG="--staging"; fi
docker compose run --rm --entrypoint certbot certbot certonly --webroot -w /var/www/certbot \
    ${STAGING_ARG} -d "${DOMAIN}" --email "${EMAIL}" --agree-tos --no-eff-email --non-interactive

echo "[TLS] 5/5 โหลดใบใหม่เข้า nginx"
docker compose exec nginx nginx -s reload

echo "[TLS] เสร็จแล้ว: https://${DOMAIN}"
