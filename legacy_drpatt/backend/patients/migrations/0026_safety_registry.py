from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('patients', '0025_scoring_run')]
    operations = [migrations.AlterField(model_name='governedregistry', name='kind',
        field=models.CharField(max_length=16, choices=[(s, s) for s in (
            'ONTOLOGY', 'NETWORK', 'MODULE', 'RESEARCH', 'CASE', 'SCORING', 'SAFETY')]))]
