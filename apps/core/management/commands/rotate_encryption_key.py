"""
เข้ารหัสข้อมูลทางคลินิกใหม่ด้วย FERNET_KEY ปัจจุบัน (ข้อมูลเดิมถอดด้วย FERNET_OLD_KEYS)

ใช้ตอนย้ายข้อมูลจากเครื่องพัฒนาขึ้น VPS หรือหมุนคีย์:
  1. ตั้ง FERNET_KEY=<คีย์ใหม่> และ FERNET_OLD_KEYS=<คีย์เดิม> ใน .env
  2. manage.py rotate_encryption_key            (dry-run นับจำนวน)
  3. manage.py rotate_encryption_key --apply
  4. ลบ FERNET_OLD_KEYS ออกจาก .env

ครอบคลุม: เลขบัตร ปชช. ที่เข้ารหัสใน Patient และไฟล์ใน PRIVATE_MEDIA_ROOT ที่อ้างอิงจาก Box
"""

from pathlib import Path

from cryptography.fernet import InvalidToken
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.models import AuditLog
from clinical.models import Box
from core.models import ClinicalEncryption
from patients.models import Patient


class Command(BaseCommand):
    help = "Re-encrypt clinical data (patient ID cards, private media) with the current FERNET_KEY."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='เขียนข้อมูลจริง (ไม่ใส่ = dry-run)')

    def handle(self, *args, **options):
        if not settings.FERNET_KEY:
            raise CommandError("ต้องตั้ง FERNET_KEY ก่อน")
        cipher = ClinicalEncryption.get_cipher()
        apply = options['apply']
        root = Path(settings.PRIVATE_MEDIA_ROOT)

        patients = Patient.all_objects.exclude(id_card_encrypted__isnull=True).exclude(id_card_encrypted='')
        media_paths = {
            m['media']['path']
            for box in Box.all_objects.exclude(contents__messages=[]).only('contents')
            for m in (box.contents or {}).get('messages', [])
            if m.get('media') and m['media'].get('path')
        }

        failed = 0
        rotated_patients = rotated_media = 0
        for p in patients.iterator():
            try:
                new_token = cipher.rotate(p.id_card_encrypted.encode()).decode()
            except InvalidToken:
                failed += 1
                continue
            if apply and new_token != p.id_card_encrypted:
                Patient.all_objects.filter(pk=p.pk).update(id_card_encrypted=new_token)
            rotated_patients += 1

        for rel in sorted(media_paths):
            path = root / rel
            if not path.is_file():
                failed += 1
                continue
            try:
                new_bytes = cipher.rotate(path.read_bytes())
            except InvalidToken:
                failed += 1
                continue
            if apply:
                path.write_bytes(new_bytes)
            rotated_media += 1

        self.stdout.write(f"Patient ID cards: {rotated_patients}  |  media files: {rotated_media}  |  unreadable/missing: {failed}")
        if failed:
            self.stdout.write(self.style.WARNING("มีข้อมูลที่ถอดไม่ได้: ตรวจว่า FERNET_OLD_KEYS มีคีย์เดิมครบ"))
        if not apply:
            self.stdout.write(self.style.WARNING("[DRY-RUN] ยังไม่ได้เขียนข้อมูล ใส่ --apply เพื่อเข้ารหัสใหม่จริง"))
            return
        AuditLog.objects.create(user=None, action='ENCRYPTION_KEY_ROTATED', model='Patient/Box', object_id='bulk',
                                changes={'patients': rotated_patients, 'media': rotated_media, 'failed': failed})
        self.stdout.write(self.style.SUCCESS("เข้ารหัสใหม่เรียบร้อย ลบ FERNET_OLD_KEYS ออกจาก .env ได้"))
