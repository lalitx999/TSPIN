"""
รอบซักประวัติ (Intake Session) แบบเบา: ใช้ Box หนึ่งกล่องต่อหนึ่งรอบการคุย

- DRAFT  = กำลังคุย ข้อความ/รูป/เสียงใหม่ต่อเข้ากล่องเดิม
- DONE   = ผู้ป่วยกด "เสร็จแล้ว" รอบุคลากรเปิดดู
- REVIEWED = บันทึกเข้าเวชระเบียน (PatientHistory) แล้ว ล็อกไม่ให้บันทึกซ้ำ

AI สรุป SOAP ทำเมื่อบุคลากรกดปุ่มเท่านั้น (ประหยัดค่า AI และไม่สรุปกล่องที่ไม่มีใครเปิด)
"""

import logging
from datetime import timedelta
from typing import Any, Dict, Optional, Tuple

import httpx
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import AuditLog
from ai_service.sanitizer import TextDeidentifier
from clinical.models import Box
from intelligence import ai_budget
from patients.models import PatientHistory

logger = logging.getLogger('tspi.clinical.intake')

# รอบที่เงียบเกินนี้จะถูกปิดเมื่อมีข้อความใหม่เข้ามา แล้วเปิดรอบใหม่ (ไม่ต้องมีตัวจับเวลา)
SESSION_IDLE_LIMIT = timedelta(hours=24)
SOAP_FIELDS = ('subjective', 'objective', 'assessment', 'plan')
MEDIA_LABELS = {'image': 'รูปภาพ', 'audio': 'ข้อความเสียง', 'video': 'วิดีโอ', 'file': 'ไฟล์'}


def open_session(patient, source: str) -> Box:
    """คืนกล่องที่ยังคุยอยู่ของผู้ป่วยในช่องทางนี้ หรือเปิดกล่องใหม่"""
    box = Box.objects.filter(patient=patient, source=source, status=Box.Status.DRAFT).order_by('-created_at').first()
    if box and box.last_activity_at and timezone.now() - box.last_activity_at > SESSION_IDLE_LIMIT:
        close_session(box, reason='idle')
        box = None
    if box is None:
        box = Box.objects.create(
            patient=patient,
            source=source,
            status=Box.Status.DRAFT,
            contents={'messages': [], 'soap': {}, 'soap_source': 'none'},
            last_activity_at=timezone.now(),
        )
    return box


def append_message(box: Box, kind: str, text: str = '', media: Optional[Dict[str, Any]] = None,
                   sender: str = 'patient', external_id: str = '', red_flag: bool = False) -> Box:
    """ต่อข้อความ/ไฟล์เข้ากล่อง (เก็บต้นฉบับ ไม่ sanitize เพราะเป็นข้อมูลให้บุคลากรอ่าน)"""
    contents = dict(box.contents or {})
    messages = list(contents.get('messages', []))
    if external_id and any(m.get('external_id') == external_id for m in messages):
        return box  # LINE retry ส่ง event ซ้ำ
    messages.append({
        'at': timezone.now().isoformat(),
        'sender': sender,
        'kind': kind,
        'text': text,
        'media': media,
        'external_id': external_id,
    })
    contents['messages'] = messages
    if red_flag:
        contents['red_flag'] = True
    box.contents = contents
    box.last_activity_at = timezone.now()
    box.save(update_fields=['contents', 'last_activity_at', 'signature'])
    return box


def close_session(box: Box, reason: str = 'patient_done') -> Box:
    if box.status == Box.Status.DRAFT:
        contents = dict(box.contents or {})
        contents['closed_reason'] = reason
        box.contents = contents
        box.status = Box.Status.DONE
        box.processed_at = timezone.now()
        box.save(update_fields=['contents', 'status', 'processed_at', 'signature'])
    return box


def transcript_text(box: Box) -> str:
    lines = []
    for m in (box.contents or {}).get('messages', []):
        if m.get('kind') == 'text' and m.get('text'):
            lines.append(m['text'])
        elif m.get('kind') != 'text':
            lines.append(f"[ผู้ป่วยส่ง{MEDIA_LABELS.get(m.get('kind'), 'ไฟล์')}]")
    return "\n".join(lines)


def summarize_with_ai(box: Box, user) -> Tuple[bool, str]:
    """
    ส่งบทสนทนา (ลบข้อมูลระบุตัวตนแล้ว) ให้ FastAPI ร่าง SOAP
    ถ้า AI ไม่ตอบจริง (fallback) จะไม่บันทึกร่าง เพื่อไม่ให้แม่แบบถูกมองว่าเป็นผล AI
    """
    raw = transcript_text(box)
    if not raw.strip():
        return False, 'ยังไม่มีข้อความในกล่องนี้'

    provider = settings.AI_SOAP_PROVIDER
    allowed, budget_msg = ai_budget.check_budget(provider)
    if not allowed:
        return False, budget_msg

    sanitized = TextDeidentifier.sanitize(raw)['sanitized_text']
    try:
        resp = httpx.post(
            f"{settings.AI_SERVICE_URL}/api/ai/soap",
            json={'complaint': sanitized},
            headers={'X-Internal-Token': settings.INTERNAL_API_TOKEN},
            timeout=60.0,
        )
        data = resp.json() if resp.status_code == 200 else {}
    except (httpx.HTTPError, ValueError) as exc:
        logger.error(f"[Intake AI] SOAP request failed for box {box.id}: {exc}")
        data = {}

    # บันทึกการใช้ทุกครั้งที่มี token ถูกใช้จริง (รวมกรณี AI ตอบแต่ parse ไม่ได้)
    if any((data.get('usage') or {}).values()):
        ai_budget.record_usage(data.get('provider') or provider, data.get('model', ''), data['usage'], 'intake_soap', user)

    if not data.get('success') or data.get('is_fallback') or not isinstance(data.get('soap'), dict):
        AuditLog.objects.create(user=user, action='INTAKE_AI_SUMMARY_FAILED', model='Box', object_id=str(box.id),
                                changes={'gateway': data.get('gateway', ''), 'is_fallback': data.get('is_fallback')})
        return False, 'AI สรุปไม่สำเร็จในขณะนี้ กรุณาอ่านจากบทสนทนาต้นฉบับ หรือลองใหม่ภายหลัง'

    contents = dict(box.contents or {})
    contents['soap'] = {k: str(data['soap'].get(k, '')) for k in SOAP_FIELDS}
    contents['soap_source'] = 'ai'
    contents['ai_meta'] = {
        'gateway': data.get('gateway', ''),
        'guardrail': data.get('guardrail', {}),
        'generated_at': timezone.now().isoformat(),
        'generated_by': user.username,
    }
    contents['relevant_axes'] = data.get('relevant_axes', [])
    box.contents = contents
    box.save(update_fields=['contents', 'signature'])
    AuditLog.objects.create(user=user, action='INTAKE_AI_SUMMARY_CREATED', model='Box', object_id=str(box.id),
                            changes={'gateway': data.get('gateway', '')})
    return True, ''


def commit_to_emr(box: Box, user, soap: Dict[str, str]) -> PatientHistory:
    """
    บันทึก SOAP ที่บุคลากรตรวจ/แก้แล้วเข้าเวชระเบียน ในชื่อผู้กดบันทึก
    เก็บร่าง AI เดิมไว้ในกล่องเพื่อเทียบได้ว่าแก้อะไรไป
    """
    with transaction.atomic():
        locked = Box.objects.select_for_update().get(pk=box.pk)
        if locked.emr_history_id:
            raise ValueError('กล่องนี้บันทึกเข้าเวชระเบียนแล้ว')
        if not locked.patient_id:
            raise ValueError('กล่องนี้ยังไม่ผูกกับเวชระเบียนผู้ป่วย')

        final_soap = {k: (soap.get(k) or '').strip() for k in SOAP_FIELDS}
        if not any(final_soap.values()):
            raise ValueError('กรุณากรอก SOAP อย่างน้อยหนึ่งช่อง')

        history = PatientHistory.objects.create(
            patient=locked.patient,
            doctor=user,
            **final_soap,
        )
        ai_soap = (locked.contents or {}).get('soap', {})
        contents = dict(locked.contents or {})
        contents['committed_soap'] = final_soap
        contents['committed_by'] = user.username
        contents['committed_at'] = timezone.now().isoformat()
        locked.contents = contents
        locked.emr_history = history
        locked.status = Box.Status.REVIEWED
        locked.decision = Box.Decision.MODIFY if ai_soap and ai_soap != final_soap else Box.Decision.APPROVE
        locked.save(update_fields=['contents', 'emr_history', 'status', 'decision', 'signature'])

        AuditLog.objects.create(
            user=user, action='INTAKE_COMMITTED_TO_EMR', model='PatientHistory', object_id=str(history.pk),
            changes={'box_id': str(locked.id), 'source': locked.source, 'role': user.role,
                     'edited_from_ai_draft': bool(ai_soap) and ai_soap != final_soap},
        )
    return history
