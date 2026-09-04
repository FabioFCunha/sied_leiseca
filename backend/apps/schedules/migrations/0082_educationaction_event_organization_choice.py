from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("schedules", "0081_agenda_internal_observation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="educationaction",
            name="requester_entity_kind",
            field=models.CharField(
                blank=True,
                choices=[
                    ("SCHOOL", "Instituição de Ensino"),
                    ("BUSINESS", "Empresa"),
                    ("EVENT_ORGANIZATION", "Organização de Evento"),
                    ("MILITARY", "Órgão Militar"),
                    ("PUBLIC", "Órgão Público"),
                    ("OTHER", "Outros"),
                    ("ADMINISTRATIVE", "Demanda Administrativa"),
                ],
                max_length=50,
                null=True,
            ),
        ),
    ]
