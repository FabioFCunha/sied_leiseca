import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.schedules.models import (
    ActionType,
    Agent,
    Agenda,
    AgendaMaterial,
    Chief,
    Kit,
    Material,
    Municipality,
    Neighborhood,
    Support,
    Team,
    Vehicle,
)


def main():
    models = [
        Agenda,
        Vehicle,
        Team,
        Chief,
        Agent,
        Support,
        ActionType,
        Municipality,
        Neighborhood,
        Kit,
        Material,
        AgendaMaterial,
    ]
    for model in models:
        print(f"{model.__name__}: {model.objects.count()}")

    sample = (
        Agenda.objects.select_related(
            "vehicle_ref",
            "team_ref",
            "chief_ref",
            "action_type_ref",
            "municipality_ref",
            "neighborhood_ref",
        )
        .prefetch_related("agents_ref", "materials")
        .filter(source_id__isnull=False)
        .first()
    )
    if sample:
        print(
            "Amostra:",
            sample.source_id,
            sample.date,
            sample.vehicle_ref,
            sample.team_ref,
            sample.chief_ref,
            sample.action_type_ref,
            sample.municipality_ref,
            sample.agents_ref.count(),
            sample.materials.count(),
        )


if __name__ == "__main__":
    main()
