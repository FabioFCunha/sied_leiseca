from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0068_educationreport_statistics_processed_and_more"),
    ]

    operations = [
        migrations.AddField(model_name="agenda", name="geocoding_address", field=models.CharField(blank=True, max_length=500, null=True)),
        migrations.AddField(model_name="agenda", name="geocoding_attempted_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(
            model_name="agenda",
            name="geocoding_status",
            field=models.CharField(
                choices=[("PENDING", "Pendente"), ("FOUND", "Localizado"), ("NOT_FOUND", "Não localizado")],
                default="PENDING",
                max_length=20,
                blank=True,
                null=True,            ),
        ),
        migrations.AddField(
            model_name="agenda",
            name="latitude",
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="agenda",
            name="longitude",
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=12, null=True),
        ),
    ]

