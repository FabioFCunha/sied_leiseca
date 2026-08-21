from django.db import migrations


ACTION_TYPE_CATEGORY_BY_NAME = {
    "Escola Nota 10": "PROGRAM_INDICATOR",
    "Escolinha Nota 10": "PROGRAM_INDICATOR",
    "Palestra Empresa": "LECTURE",
    "Palestra Universidade": "LECTURE",
    "Palestra Escola Privada": "LECTURE",
    "Palestra Escola Pública": "LECTURE",
    "Palestra Escola": "LECTURE",
}


def categorize_and_deactivate_actions(apps, schema_editor):
    ActionType = apps.get_model("schedules", "ActionType")

    for name, category in ACTION_TYPE_CATEGORY_BY_NAME.items():
        update_kwargs = {"category": category}
        if name == "Palestra Escola":
            update_kwargs["is_active"] = False
        ActionType.objects.filter(name=name).update(**update_kwargs)


def reverse_categorize_and_deactivate_actions(apps, schema_editor):
    ActionType = apps.get_model("schedules", "ActionType")

    for name in ACTION_TYPE_CATEGORY_BY_NAME:
        update_kwargs = {"category": None}
        if name == "Palestra Escola":
            update_kwargs["is_active"] = True
        ActionType.objects.filter(name=name).update(**update_kwargs)


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0076_actiontype_category_and_educationaction_fields"),
    ]

    operations = [
        migrations.RunPython(
            categorize_and_deactivate_actions,
            reverse_categorize_and_deactivate_actions,
        ),
    ]
