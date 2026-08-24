from django.db import migrations


def seed_educational_action_type(apps, schema_editor):
    ActionType = apps.get_model("schedules", "ActionType")
    canonical = ActionType.objects.filter(name="Ação Educativa").first()
    if not canonical:
        canonical = ActionType.objects.filter(name__iexact="Ação Educativa").order_by("id").first()

    if canonical:
        canonical.name = "Ação Educativa"
        canonical.is_active = True
        canonical.category = "EDUCATIONAL_ACTION"
        canonical.save(update_fields=["name", "is_active", "category"])
    else:
        ActionType.objects.create(
            name="Ação Educativa",
            is_active=True,
            category="EDUCATIONAL_ACTION",
        )


class Migration(migrations.Migration):
    dependencies = [
        ("schedules", "0079_educationaction_administrative_requester_choices"),
    ]

    operations = [
        migrations.RunPython(seed_educational_action_type, migrations.RunPython.noop),
    ]
