import unicodedata

from django.db import migrations


CANONICAL_TEAMS = ["Alfa", "Bravo", "Charlie", "Delta", "Echo", "Fox", "Golf", "Hotel"]


def simplify(value):
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    return text.upper()


def closest_team(name):
    text = simplify(name)
    if "ALFA" in text:
        return "Alfa"
    if "BRAVO" in text:
        return "Bravo"
    if "CHARLIE" in text:
        return "Charlie"
    if "DELTA" in text:
        return "Delta"
    if "ECHO" in text or "ECO" in text:
        return "Echo"
    if "FOX" in text or "FOXTROT" in text:
        return "Fox"
    if "GOLF" in text or "GOLFE" in text:
        return "Golf"
    if "HOTEL" in text:
        return "Hotel"
    return None


def normalize_military_teams(apps, schema_editor):
    Team = apps.get_model("schedules", "Team")
    Agent = apps.get_model("schedules", "Agent")
    Agenda = apps.get_model("schedules", "Agenda")

    canonical = {}
    for name in CANONICAL_TEAMS:
        team, _ = Team.objects.get_or_create(name=name, defaults={"is_active": True})
        canonical[name] = team

    for team in list(Team.objects.all().order_by("id")):
        target_name = closest_team(team.name)
        if not target_name:
            continue

        target = canonical[target_name]
        if team.id != target.id:
            Agent.objects.filter(team_id=team.id).update(team=target)
            Agenda.objects.filter(team_ref_id=team.id).update(team_ref=target, team_name=target.name)
            team.delete()
        else:
            Agenda.objects.filter(team_ref_id=team.id).update(team_name=target.name)

    for agenda in Agenda.objects.exclude(team_name=""):
        target_name = closest_team(agenda.team_name)
        if target_name and agenda.team_name != target_name:
            agenda.team_name = target_name
            agenda.save(update_fields=["team_name"])


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0010_seed_military_teams"),
    ]

    operations = [
        migrations.RunPython(normalize_military_teams, migrations.RunPython.noop),
    ]
