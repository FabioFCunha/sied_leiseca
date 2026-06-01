from django.db import migrations


MILITARY_TEAMS = ["Alfa", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel"]


def seed_military_teams(apps, schema_editor):
    Team = apps.get_model("schedules", "Team")
    for name in MILITARY_TEAMS:
        Team.objects.get_or_create(name=name, defaults={"is_active": True})


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0009_agenda_origin_cancel_reason"),
    ]

    operations = [
        migrations.RunPython(seed_military_teams, migrations.RunPython.noop),
    ]
