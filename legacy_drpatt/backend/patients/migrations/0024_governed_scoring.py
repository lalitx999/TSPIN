from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('patients', '0023_governed_registry')]
    operations = [
        migrations.AlterField(model_name='governedregistry', name='kind',
            field=models.CharField(max_length=16, choices=[(s, s) for s in (
                'ONTOLOGY', 'NETWORK', 'MODULE', 'RESEARCH', 'CASE', 'SCORING')])),
        migrations.AlterModelOptions(name='governedregistry', options={'permissions': [
            ('approve_governedregistry', 'Review governed registry lifecycle'),
            ('execute_governedscoring', 'Execute approved deterministic scoring rules'),
        ]}),
    ]
