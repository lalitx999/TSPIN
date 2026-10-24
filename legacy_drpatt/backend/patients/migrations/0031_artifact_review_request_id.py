from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('patients', '0030_artifact_review_event')]
    operations = [
        migrations.AddField(model_name='artifactreviewevent', name='request_id',
                            field=models.UUIDField(null=True, blank=True, editable=False)),
        migrations.AddConstraint(model_name='artifactreviewevent', constraint=models.UniqueConstraint(
            fields=('artifact', 'actor', 'request_id'), name='unique_artifact_review_request')),
    ]
