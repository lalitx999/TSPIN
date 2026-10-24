from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('patients', '0029_verified_line_binding'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [migrations.CreateModel(
        name='ArtifactReviewEvent',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('decision', models.CharField(max_length=32, choices=[(s, s) for s in (
                'REVIEWED_NOT_APPROVED', 'REQUEST_CHANGES', 'REJECT')])),
            ('reason', models.TextField()),
            ('artifact_hash', models.CharField(max_length=64)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('actor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ('artifact', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                          related_name='review_events', to='patients.agenticartifact')),
        ],
    )]
