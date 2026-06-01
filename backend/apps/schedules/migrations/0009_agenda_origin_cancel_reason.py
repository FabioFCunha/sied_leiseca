from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0008_agent_team"),
    ]

    operations = [
        migrations.AddField(
            model_name="agenda",
            name="origin",
            field=models.CharField(
                choices=[
                    ("INTERNAL", "Interna"),
                    ("PUBLIC_FORM", "Formulario publico"),
                    ("WHATSAPP", "WhatsApp"),
                    ("PHONE", "Telefone"),
                    ("EMAIL", "E-mail"),
                    ("DOCUMENT", "Oficio"),
                    ("OTHER", "Outra"),
                ],
                default="INTERNAL",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="agenda",
            name="cancel_reason",
            field=models.TextField(blank=True),
        ),
    ]
