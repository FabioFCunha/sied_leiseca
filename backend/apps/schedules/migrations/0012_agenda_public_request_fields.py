from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0011_normalize_military_teams"),
    ]

    operations = [
        migrations.AddField("agenda", "actions_count", models.PositiveSmallIntegerField(blank=True, null=True)),
        migrations.AddField("agenda", "time_2", models.TimeField(blank=True, null=True)),
        migrations.AddField("agenda", "time_3", models.TimeField(blank=True, null=True)),
        migrations.AddField("agenda", "state", models.CharField(blank=True, max_length=40)),
        migrations.AddField("agenda", "contact_email", models.EmailField(blank=True, max_length=254)),
        migrations.AddField("agenda", "requester_cpf", models.CharField(blank=True, max_length=20)),
        migrations.AddField("agenda", "requester_role", models.CharField(blank=True, max_length=160)),
        migrations.AddField("agenda", "requester_entity_type", models.CharField(blank=True, max_length=160)),
        migrations.AddField("agenda", "age_ranges", models.CharField(blank=True, max_length=220)),
        migrations.AddField("agenda", "has_ramps", models.CharField(blank=True, max_length=3)),
        migrations.AddField("agenda", "has_elevators", models.CharField(blank=True, max_length=3)),
        migrations.AddField("agenda", "has_accessible_bathrooms", models.CharField(blank=True, max_length=3)),
        migrations.AddField("agenda", "media_equipment", models.TextField(blank=True)),
        migrations.AddField("agenda", "image_authorization", models.TextField(blank=True)),
    ]
