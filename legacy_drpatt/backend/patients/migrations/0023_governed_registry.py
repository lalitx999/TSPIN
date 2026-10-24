import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('patients', '0022_canonical_unit_registry'),
                    migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='GovernedRegistry', fields=[
            ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
            ('kind', models.CharField(max_length=16, choices=[(s, s) for s in ('ONTOLOGY', 'NETWORK', 'MODULE', 'RESEARCH', 'CASE')])),
            ('version', models.CharField(max_length=80)),
            ('content', models.JSONField()),
            ('content_hash', models.CharField(max_length=64, editable=False)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT)),
        ], options={'constraints': [models.UniqueConstraint(fields=('kind', 'version'), name='unique_governed_registry_version')],
                    'permissions': [('approve_governedregistry', 'Review governed registry lifecycle')]}),
        migrations.CreateModel(name='GovernedRegistryDecision', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('state', models.CharField(max_length=16)),
            ('reason', models.TextField()),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('registry', models.ForeignKey(to='patients.governedregistry', related_name='decisions', on_delete=django.db.models.deletion.PROTECT)),
            ('actor', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT)),
        ], options={'ordering': ['-id']}),
    ]
