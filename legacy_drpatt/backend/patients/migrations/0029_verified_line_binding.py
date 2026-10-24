from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('patients', '0028_agentic_artifact'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name='VerifiedLineBinding', fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('line_user_id', models.CharField(max_length=150, unique=True)),
        ('created_at', models.DateTimeField(auto_now_add=True)),
        ('linked_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
        ('patient', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,
            related_name='verified_line_binding', to='patients.patient')),
    ])]
