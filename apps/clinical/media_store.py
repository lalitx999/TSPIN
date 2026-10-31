"""
ที่เก็บไฟล์ทางคลินิกแบบเข้ารหัส (รูป/เสียง/วิดีโอจาก LINE และเว็บ)

- เก็บใต้ PRIVATE_MEDIA_ROOT ซึ่งอยู่นอก MEDIA_ROOT และ nginx ไม่ serve
- เข้ารหัสทั้งไฟล์ด้วย Fernet (คีย์เดียวกับ ClinicalEncryption)
- คืน metadata (path, sha256, ขนาด, ชนิดไฟล์) ให้ผูกไว้กับ Box; การเปิดดูต้องผ่าน Django view ที่ตรวจสิทธิ์และบันทึก AuditLog
"""

import hashlib
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from django.conf import settings
from django.utils import timezone

from core.models import ClinicalEncryption

EXTENSIONS = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
    'audio/m4a': '.m4a',
    'audio/x-m4a': '.m4a',
    'audio/aac': '.aac',
    'audio/mpeg': '.mp3',
    'video/mp4': '.mp4',
    'application/pdf': '.pdf',
}


def _root() -> Path:
    return Path(settings.PRIVATE_MEDIA_ROOT)


def save_encrypted(data: bytes, content_type: str, kind: str) -> Dict[str, Any]:
    """เข้ารหัสและบันทึกไฟล์ คืน metadata สำหรับเก็บใน Box.contents"""
    now = timezone.now()
    media_id = uuid.uuid4().hex
    relative = Path(kind) / f"{now:%Y}" / f"{now:%m}" / f"{media_id}{EXTENSIONS.get(content_type, '.bin')}.enc"
    target = _root() / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(ClinicalEncryption.get_cipher().encrypt(data))
    return {
        'media_id': media_id,
        'path': str(relative),
        'content_type': content_type,
        'size': len(data),
        'sha256': hashlib.sha256(data).hexdigest(),
        'stored_at': now.isoformat(),
    }


def read_decrypted(meta: Dict[str, Any]) -> Optional[bytes]:
    """อ่านไฟล์และตรวจ sha256 ว่าไม่ถูกแก้ไขตั้งแต่บันทึก คืน None ถ้าไม่พบหรือไม่ตรง"""
    target = (_root() / meta.get('path', '')).resolve()
    if _root().resolve() not in target.parents or not target.is_file():
        return None
    data = ClinicalEncryption.get_cipher().decrypt(target.read_bytes())
    if hashlib.sha256(data).hexdigest() != meta.get('sha256'):
        return None
    return data
