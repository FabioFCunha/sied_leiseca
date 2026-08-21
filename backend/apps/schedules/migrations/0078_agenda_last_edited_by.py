from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0077_deactivate_palestra_escola"),
    ]

    operations = [
        migrations.AddField(
            model_name="agenda",
            name="last_edited_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="last_edited_agendas",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
