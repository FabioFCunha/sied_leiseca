from django.db import migrations


def seed_educational_action_type(apps, schema_editor):
    ActionType = apps.get_model("schedules", "ActionType")
    ActionType.objects.update_or_create(
        name="Ação Educativa",
        defaults={
            "is_active": True,
            "category": "EDUCATIONAL_ACTION",
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("schedules", "0079_educationaction_administrative_requester_choices"),
    ]

    operations = [
        migrations.RunPython(seed_educational_action_type, migrations.RunPython.noop),
    ]
