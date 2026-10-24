"""Read-only inventory for clinic review after retiring public staff registration."""
import json
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from patients.models import AuditLog


class Command(BaseCommand):
    help = 'Read-only staff provisioning inventory. Does not verify, revoke, or modify users.'

    def handle(self, *args, **options):
        public_targets = set(AuditLog.objects.filter(action='DOCTOR_REGISTRATION_SUCCESS')
                             .values_list('target_id', flat=True))
        staff = list(User.objects.filter(is_staff=True).order_by('pk')
                     .values('id', 'is_active', 'is_superuser'))
        for account in staff:
            account['public_signup_recorded'] = str(account['id']) in public_targets
            account['provisioning_verified'] = False  # No trusted verification registry yet.
            account['review_required'] = True
        self.stdout.write(json.dumps({
            'read_only': True, 'staff_count': len(staff), 'accounts': staff,
            'notice': 'No audit record does not prove trusted provisioning. Review all staff accounts. '
                      'This command changes no accounts and grants no clinical authority.',
        }, ensure_ascii=False))
