import uuid

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ('patients', '0020_expand_audit_log'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [migrations.CreateModel(
        name='ClinicalEvidenceRevision',
        fields=[
            ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
            ('payload', models.JSONField()),
            ('payload_hash', models.CharField(max_length=64, editable=False)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('patient', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                         related_name='evidence_revisions', to='patients.patient')),
            ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                            to=settings.AUTH_USER_MODEL)),
            ('supersedes', models.OneToOneField(null=True, blank=True,
                on_delete=django.db.models.deletion.PROTECT, related_name='successor',
                to='patients.clinicalevidencerevision')),
        ],
        options={'ordering': ['created_at', 'id'], 'permissions': [
            ('verify_clinicalevidence', 'Verify clinical source evidence'),
        ]},
    )]
