"""
Management Command: ยกเลิกข้อมูลคลินิกที่ sync_real_patients สร้างขึ้นเอง (ไม่ใช่ผลประเมินจริง)

1. BiologicalRecord baseline ที่ระบบเดาคะแนน 39 แกนจากคำในประวัติโรค
   -> soft delete (ซ่อนจากทุกหน้าจอ แต่ไม่ลบจริง) พร้อมบันทึก invalidation_reason
2. สถานะ 'urgent' ที่ได้จากการจับคำ เช่น "ไต" / "ตับ" ในข้อความโรค (ติดแม้แต่ "ไตรกลีเซอไรด์")
   -> คืนเป็น 'pending' ให้แพทย์เป็นผู้ประเมินเอง
   แตะเฉพาะผู้ป่วยที่นำเข้าจากระบบเดิม (มี extra_data.legacy_id) และไม่เคยถูกแก้ไขหลังนำเข้า

ค่าเริ่มต้นเป็น dry-run ต้องใส่ --apply เพื่อบันทึกจริง ทุกการเปลี่ยนแปลงถูกบันทึกใน AuditLog
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounts.models import AuditLog
from clinical.models import BiologicalRecord
from patients.models import Patient

SYNC_BASELINE_NOTE = "การประเมินสภาวะชีววิทยา 39 แกนแรกรับ (Initial 39-Axes Baseline Assessment)"
INVALIDATION_REASON = (
    "ยกเลิกโดยระบบ: คะแนนถูกสร้างอัตโนมัติจากคำในประวัติโรคตอนนำเข้า (sync_real_patients) "
    "ไม่ใช่ผลประเมินจริงของแพทย์"
)
# ผู้ป่วยที่ updated_at ห่างจาก created_at ไม่เกินนี้ ถือว่ายังไม่เคยถูกแก้ไขหลังนำเข้า
UNTOUCHED_WINDOW = timedelta(minutes=5)


class Command(BaseCommand):
    help = "Invalidate synthetic 39-axis baselines and keyword-derived urgent status created by sync_real_patients."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='บันทึกการเปลี่ยนแปลงจริง (ไม่ใส่ = dry-run)')

    def handle(self, *args, **options):
        apply = options['apply']

        baselines = BiologicalRecord.objects.filter(is_baseline=True, notes=SYNC_BASELINE_NOTE)
        urgent = Patient.objects.filter(
            status='urgent',
            extra_data__has_key='legacy_id',
            updated_at__lte=F('created_at') + UNTOUCHED_WINDOW,
        )

        baseline_ids = list(baselines.values_list('pk', flat=True))
        urgent_ids = list(urgent.values_list('pk', flat=True))

        self.stdout.write(f"Synthetic baseline records to invalidate: {len(baseline_ids)}")
        self.stdout.write(f"Keyword-derived 'urgent' patients to reset to 'pending': {len(urgent_ids)}")

        if not apply:
            self.stdout.write(self.style.WARNING("[DRY-RUN] No changes made. Re-run with --apply to commit."))
            return

        now = timezone.now()
        with transaction.atomic():
            BiologicalRecord.objects.filter(pk__in=baseline_ids).update(
                is_deleted=True, deleted_at=now, invalidation_reason=INVALIDATION_REASON,
            )
            # update() ไม่แตะ auto_now ของ updated_at จึงยังระบุได้ว่าแพทย์ยังไม่เคยแก้ไข
            Patient.objects.filter(pk__in=urgent_ids).update(status='pending')
            AuditLog.objects.create(
                user=None,
                action="SYNC_ARTIFACTS_INVALIDATED",
                model="BiologicalRecord/Patient",
                object_id="bulk",
                changes={
                    "invalidated_baseline_ids": baseline_ids,
                    "urgent_reset_patient_ids": urgent_ids,
                    "reason": INVALIDATION_REASON,
                },
            )

        self.stdout.write(self.style.SUCCESS(
            f"Invalidated {len(baseline_ids)} baselines and reset {len(urgent_ids)} patients to 'pending'."
        ))
