from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0012_agenda_public_request_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="agenda",
            name="linked_action",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="linked_requests",
                to="schedules.agenda",
            ),
        ),
    ]
