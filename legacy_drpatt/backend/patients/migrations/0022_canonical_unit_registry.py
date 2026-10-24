import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('patients', '0021_clinical_evidence_revision'),
                    migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='CanonicalUnitRegistry', fields=[
            ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
            ('version', models.CharField(max_length=80, unique=True)),
            ('units', models.JSONField()),
            ('content_hash', models.CharField(max_length=64, editable=False)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT)),
        ], options={'permissions': [('approve_unitregistry', 'Approve or retire unit registry versions')]}),
        migrations.CreateModel(name='UnitRegistryDecision', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('state', models.CharField(max_length=16, choices=[(s, s) for s in ('DRAFT', 'PROVISIONAL', 'APPROVED', 'RETIRED')])),
            ('reason', models.TextField()),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('actor', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT)),
            ('registry', models.ForeignKey(to='patients.canonicalunitregistry', related_name='decisions', on_delete=django.db.models.deletion.PROTECT)),
        ], options={'ordering': ['-id']}),
        migrations.AddField(model_name='clinicalevidencerevision', name='unit_registry',
            field=models.ForeignKey(to='patients.canonicalunitregistry', null=True, blank=True,
                                    on_delete=django.db.models.deletion.PROTECT)),
    ]
