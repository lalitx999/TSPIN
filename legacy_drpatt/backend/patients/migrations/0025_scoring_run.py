import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('patients', '0024_governed_scoring'),
                    migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name='ScoringRun', fields=[
        ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
        ('manifest', models.JSONField()),
        ('result', models.JSONField()),
        ('integrity_hash', models.CharField(max_length=64, editable=False)),
        ('created_at', models.DateTimeField(auto_now_add=True)),
        ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT)),
        ('patient', models.ForeignKey(to='patients.patient', related_name='scoring_runs', on_delete=django.db.models.deletion.PROTECT)),
    ], options={'ordering': ['-created_at', '-id']})]
