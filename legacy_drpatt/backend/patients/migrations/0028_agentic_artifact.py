import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('patients', '0027_safety_assessment'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name='AgenticArtifact', fields=[
        ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
        ('kind', models.CharField(max_length=24, choices=[('WORKFLOW', 'Workflow'), ('EVIDENCE_DRAFT', 'Evidence draft')])),
        ('payload', models.JSONField()), ('integrity_hash', models.CharField(max_length=64, editable=False)),
        ('created_at', models.DateTimeField(auto_now_add=True)),
        ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT)),
        ('patient', models.ForeignKey(to='patients.patient', related_name='agentic_artifacts', on_delete=django.db.models.deletion.PROTECT)),
    ], options={'ordering': ['-created_at', '-id']})]
