#!/usr/bin/env python3
"""
สร้างค่าลับชุดใหม่สำหรับ .env บน VPS (พิมพ์ออกหน้าจอ ไม่เขียนไฟล์)

  python3 scripts/generate_secrets.py
  python3 scripts/generate_secrets.py --old-secret-key '<SECRET_KEY ของเครื่องที่ย้ายข้อมูลมา>'

--old-secret-key: ถ้าย้ายฐานข้อมูลจากเครื่องที่ไม่เคยตั้ง FERNET_KEY ข้อมูลที่เข้ารหัสไว้ใช้คีย์ที่ได้จาก SECRET_KEY เดิม
สคริปต์จะพิมพ์ FERNET_OLD_KEYS ให้ เพื่อให้ VPS ถอดข้อมูลเก่าได้ แล้วค่อยรัน manage.py rotate_encryption_key --apply
(ถ้าเครื่องเดิมไม่ได้ตั้ง DJANGO_SECRET_KEY ให้ใช้ค่าเริ่มต้นใน config/settings/dev.py)
"""

import argparse
import base64
import hashlib
import secrets

from cryptography.fernet import Fernet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-secret-key', default='')
    args = parser.parse_args()

    print("# --- วางค่าเหล่านี้ใน .env บน VPS (อย่า commit, อย่าส่งในแชท) ---")
    print(f"DJANGO_SECRET_KEY={secrets.token_urlsafe(64)}")
    print(f"INTERNAL_API_TOKEN={secrets.token_urlsafe(48)}")
    print(f"DB_PASSWORD={secrets.token_urlsafe(32)}")
    print(f"FERNET_KEY={Fernet.generate_key().decode()}")
    if args.old_secret_key:
        old = base64.urlsafe_b64encode(hashlib.sha256(args.old_secret_key.encode('utf-8')).digest()).decode()
        print(f"FERNET_OLD_KEYS={old}")


if __name__ == '__main__':
    main()
