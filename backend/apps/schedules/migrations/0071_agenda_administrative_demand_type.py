from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0070_shiftschedulechange"),
    ]

    operations = [
        migrations.AddField(
            model_name="agenda",
            name="administrative_demand_type",
            field=models.CharField(blank=True, choices=[("TRAVEL", "Deslocamento de viagem"), ("INTERVIEW", "Entrevista"), ("MEETING", "Reuni?o")], default="", max_length=20),
        ),
    ]
