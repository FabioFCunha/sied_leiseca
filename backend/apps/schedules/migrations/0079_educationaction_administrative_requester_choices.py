from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("schedules", "0078_agenda_last_edited_by"),
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
                    ("MILITARY", "Órgão Militar"),
                    ("PUBLIC", "Órgão Público"),
                    ("OTHER", "Outros"),
                    ("ADMINISTRATIVE", "Demanda Administrativa"),
                ],
                max_length=50,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="educationaction",
            name="requester_entity_nature",
            field=models.CharField(
                blank=True,
                choices=[
                    ("PUBLIC", "Pública"),
                    ("PRIVATE", "Privada"),
                    ("NOT_APPLICABLE", "Não se aplica"),
                ],
                max_length=50,
                null=True,
            ),
        ),
    ]
