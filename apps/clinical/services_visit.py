"""
ซักประวัติที่คลินิก (หน้าแฟ้มคนไข้): สัญญาณชีพ + ช่องซักประวัติ (พิมพ์/พูด/รูป) -> Gemini สรุป SOAP -> ตรวจทาน -> เวชระเบียน

ร่างเก็บใน Box หนึ่งกล่อง (source CLINIC, contents.origin = 'visit', สถานะ DRAFT) ต่อผู้บันทึกต่อคนไข้
- รีเฟรชหน้าแล้วงานไม่หาย และเก็บร่าง AI ไว้เทียบกับฉบับที่บันทึกจริง (เหมือนแชท LINE)
- รูปเข้ารหัสด้วย media_store และอยู่ใน contents.messages (kind image) จึงเปิดดูผ่านหน้าแชทเดิมได้
- ผู้สร้างร่างเปิดร่างของตัวเองได้เสมอ คนอื่นต้องปลดล็อกกล่องตามกฎเดิม
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import AuditLog
from ai_service.sanitizer import TextDeidentifier
from clinical import media_store, services_intake
from clinical.models import Box
from intelligence import ai_budget
from patients.models import PatientHistory

logger = logging.getLogger('tspi.clinical.visit')

ORIGIN = 'visit'
PROVIDER = 'gemini'
MAX_IMAGES = 6
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_HISTORY_CHARS = 20000
IMAGE_TYPES = ('image/jpeg', 'image/png', 'image/webp')


class VisitError(ValueError):
    """ข้อผิดพลาดที่แสดงให้ผู้ใช้เห็นได้ตรง ๆ"""


def drafts_for(patient):
    return Box.objects.filter(patient=patient, source=Box.Source.CLINIC, status=Box.Status.DRAFT,
                              contents__origin=ORIGIN).select_related('opened_by')


def own_draft(patient, user) -> Optional[Box]:
    return drafts_for(patient).filter(opened_by=user).order_by('-created_at').first()


def get_draft(patient, user, box_id) -> Box:
    """ร่างของผู้ใช้คนนี้เท่านั้น (ร่างของคนอื่นต้องเปิดผ่านหน้าแชทซึ่งมีการปลดล็อก)"""
    box = drafts_for(patient).filter(pk=box_id, opened_by=user).first()
    if box is None:
        raise VisitError('ไม่พบร่างนี้ หรือร่างถูกบันทึกเข้าเวชระเบียนไปแล้ว')
    return box


def get_or_create_draft(patient, user) -> Box:
    box = own_draft(patient, user)
    if box:
        return box
    now = timezone.now()
    box = Box.objects.create(
        patient=patient, source=Box.Source.CLINIC, status=Box.Status.DRAFT,
        contents={'origin': ORIGIN, 'messages': [], 'history_text': '', 'vitals_input': {},
                  'soap': {}, 'soap_source': 'none'},
        last_activity_at=now, opened_by=user, opened_at=now,
    )
    AuditLog.objects.create(user=user, action='VISIT_DRAFT_CREATED', model='Box', object_id=str(box.id),
                            changes={'patient_hn': patient.hn})
    return box


def images(box: Box) -> List[Dict[str, Any]]:
    return [m for m in (box.contents or {}).get('messages', []) if m.get('kind') == 'image' and m.get('media')]


def save_draft(box: Box, history_text: str, vitals_input: Dict[str, str], soap: Optional[Dict[str, str]] = None) -> Box:
    """บันทึกร่างอัตโนมัติ: เก็บค่าที่พิมพ์ไว้ตามจริง (ยังไม่ตรวจช่วงค่า) เพื่อให้กลับมาทำต่อได้"""
    contents = dict(box.contents or {})
    contents['history_text'] = (history_text or '')[:MAX_HISTORY_CHARS]
    contents['vitals_input'] = {k: str(v)[:12] for k, v in (vitals_input or {}).items()}
    if soap is not None and contents.get('soap_source') in ('ai', 'manual'):
        contents['soap_edit'] = {k: (soap.get(k) or '')[:5000] for k in services_intake.SOAP_FIELDS}
    box.contents = contents
    box.last_activity_at = timezone.now()
    box.save(update_fields=['contents', 'last_activity_at', 'signature'])
    return box


def add_image(box: Box, data: bytes, content_type: str, user) -> Dict[str, Any]:
    if content_type not in IMAGE_TYPES:
        raise VisitError('รองรับเฉพาะรูป JPG, PNG หรือ WEBP')
    if not data:
        raise VisitError('ไฟล์รูปว่างเปล่า')
    if len(data) > MAX_IMAGE_BYTES:
        raise VisitError('รูปใหญ่เกิน 8 MB')
    if len(images(box)) >= MAX_IMAGES:
        raise VisitError(f'แนบรูปได้สูงสุด {MAX_IMAGES} รูป')
    meta = media_store.save_encrypted(data, content_type, 'image')
    services_intake.append_message(box, 'image', media=meta, sender='staff')
    AuditLog.objects.create(user=user, action='VISIT_IMAGE_ADDED', model='Box', object_id=str(box.id),
                            changes={'media_id': meta['media_id'], 'size': meta['size']})
    return meta


def remove_image(box: Box, media_id: str, user) -> None:
    contents = dict(box.contents or {})
    messages = list(contents.get('messages', []))
    target = next((m for m in messages if (m.get('media') or {}).get('media_id') == media_id), None)
    if target is None:
        raise VisitError('ไม่พบรูปนี้')
    # ไม่ลบไฟล์จริง (นโยบายห้ามลบข้อมูลทางการแพทย์) แค่ย้ายออกจากร่าง ไม่ส่งให้ AI และไม่แสดงในฟอร์ม
    contents['messages'] = [m for m in messages if m is not target]
    contents['removed_media'] = list(contents.get('removed_media', [])) + [target['media']]
    box.contents = contents
    box.save(update_fields=['contents', 'signature'])
    AuditLog.objects.create(user=user, action='VISIT_IMAGE_REMOVED', model='Box', object_id=str(box.id),
                            changes={'media_id': media_id})


def summarize(box: Box, vitals: Dict[str, Any], user) -> Dict[str, str]:
    """
    ส่งข้อความ (ลบข้อมูลระบุตัวตนแล้ว) + สัญญาณชีพ + รูป ให้ ai_service สรุปด้วย Gemini
    ai_service ลบ EXIF และเบลอใบหน้าในรูปอีกชั้นก่อนส่งออกนอกระบบ
    """
    contents = box.contents or {}
    history = (contents.get('history_text') or '').strip()
    pictures = images(box)
    if not history and not pictures:
        raise VisitError('กรุณาซักประวัติก่อน (พิมพ์ พูด หรือแนบรูปอย่างน้อยหนึ่งอย่าง)')

    allowed, budget_msg = ai_budget.check_budget(PROVIDER)
    if not allowed:
        raise VisitError(budget_msg)

    files = []
    for m in pictures:
        data = media_store.read_decrypted(m['media'])
        if data:
            files.append(('images', (f"{m['media']['media_id']}.img", data, m['media'].get('content_type', 'image/jpeg'))))

    try:
        resp = httpx.post(
            f"{settings.AI_SERVICE_URL}/api/ai/visit/soap",
            data={'history': TextDeidentifier.sanitize(history)['sanitized_text'], 'vitals': json.dumps(vitals)},
            files=files or None,
            headers={'X-Internal-Token': settings.INTERNAL_API_TOKEN},
            timeout=120.0,
        )
        data = resp.json() if resp.status_code == 200 else {}
    except (httpx.HTTPError, ValueError) as exc:
        logger.error(f"[Visit AI] request failed for box {box.id}: {type(exc).__name__}")
        data = {}

    if any((data.get('usage') or {}).values()):
        ai_budget.record_usage(data.get('provider') or PROVIDER, data.get('model', ''), data['usage'], 'visit_soap', user)

    soap = data.get('soap') if data.get('success') else None
    if not isinstance(soap, dict) or not any(str(soap.get(k) or '').strip() for k in services_intake.SOAP_FIELDS):
        AuditLog.objects.create(user=user, action='VISIT_AI_SUMMARY_FAILED', model='Box', object_id=str(box.id),
                                changes={'error': str(data.get('error', 'no_response'))[:100]})
        raise VisitError('AI สรุปไม่สำเร็จในขณะนี้ ลองใหม่อีกครั้ง หรือกด "กรอก SOAP เอง"')

    soap = {k: str(soap.get(k) or '') for k in services_intake.SOAP_FIELDS}
    contents = dict(box.contents or {})
    contents['soap'] = soap
    contents.pop('soap_edit', None)
    contents['soap_source'] = 'ai'
    contents['vitals'] = vitals
    contents['ai_meta'] = {
        'gateway': data.get('gateway', ''),
        'guardrail': data.get('guardrail', {}),
        'images_sent': data.get('images_sent', 0),
        'generated_at': timezone.now().isoformat(),
        'generated_by': user.username,
    }
    box.contents = contents
    box.save(update_fields=['contents', 'signature'])
    AuditLog.objects.create(user=user, action='VISIT_AI_SUMMARY_CREATED', model='Box', object_id=str(box.id),
                            changes={'gateway': data.get('gateway', ''), 'images': data.get('images_sent', 0)})
    return soap


def unlock_manual_soap(box: Box, user) -> None:
    """AI ใช้ไม่ได้: เปิดช่อง SOAP ให้กรอกเอง (บันทึกไว้ว่าไม่ได้มาจาก AI)"""
    contents = dict(box.contents or {})
    if contents.get('soap_source') != 'ai':
        contents['soap_source'] = 'manual'
    box.contents = contents
    box.save(update_fields=['contents', 'signature'])
    AuditLog.objects.create(user=user, action='VISIT_MANUAL_SOAP', model='Box', object_id=str(box.id))


def commit(box: Box, user, soap: Dict[str, str], vitals: Dict[str, Any]) -> PatientHistory:
    if (box.contents or {}).get('soap_source') not in ('ai', 'manual'):
        raise VisitError('กรุณาให้ AI สรุป SOAP (หรือกด "กรอก SOAP เอง") ก่อนบันทึก')
    history = services_intake.commit_to_emr(box, user, soap, vitals=vitals)
    with transaction.atomic():
        box.refresh_from_db()
        contents = dict(box.contents or {})
        contents['vitals'] = vitals
        contents['reviewed_confirmed'] = True
        box.contents = contents
        box.save(update_fields=['contents', 'signature'])
    return history


def discard(box: Box, user) -> None:
    """ทิ้งร่าง: Box เป็น soft delete ข้อมูลและไฟล์ยังอยู่ให้ตรวจสอบย้อนหลังได้"""
    AuditLog.objects.create(user=user, action='VISIT_DRAFT_DISCARDED', model='Box', object_id=str(box.id))
    box.delete()
