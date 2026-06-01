from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0007_eventreport_execution_quality_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="agent",
            name="team",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="agents",
                to="schedules.team",
            ),
        ),
    ]
