from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("schedules", "0080_seed_educational_action_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="agenda",
            name="internal_observation",
            field=models.TextField(blank=True),
        ),
    ]
