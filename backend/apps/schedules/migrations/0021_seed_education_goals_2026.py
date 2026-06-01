from django.db import migrations


GOALS_2026 = [
    ("approach", "1 - ABORDADOS", 149478, 160000, 1),
    ("approached_lectures", "1.1 - ABORDADOS PALESTRAS", 29483, 40000, 2),
    ("approached_actions", "1.2 - ABORDADOS AÇÕES", 120491, 120000, 3),
    ("lectures", "2 - PALESTRAS", 305, 320, 4),
    ("schools", "2.1 - ESCOLAS", 176, 220, 5),
    ("universities", "2.2 - UNIVERSIDADES", 5, 5, 6),
    ("companies", "2.3 - EMPRESAS", 124, 95, 7),
    ("educational_actions", "3 - AÇÕES", 1062, 1000, 8),
    ("bars", "3.1 - BAR/RESTAURANTE", 126, 100, 9),
    ("tolls", "3.2 - PEDÁGIO", 6, 10, 10),
    ("sports", "3.3 - PRAÇA ESPORTIVA", 23, 20, 11),
    ("beach", "3.4 - PRAIA", 34, 50, 12),
    ("events", "3.5 - EVENTO", 127, 120, 13),
    ("shopping", "3.6 - SHOPPING", 15, 20, 14),
    ("social_actions", "3.7 - AÇÃO SOCIAL", 56, 50, 15),
    ("other_actions", "3.8 - OUTROS", 675, 630, 16),
    ("publicity_materials", "4 - MATERIAIS DE DIVULGAÇÃO", 1199652, 200000, 17),
    ("distributed_certificates", "4.1 - CERTIFICADOS ENTREGUES", 3107, 5000, 18),
    ("gibis", '4.2 - KIT "Escolinha Nota 10"', 11539, 25000, 19),
]


def seed_goals(apps, schema_editor):
    EducationGoal = apps.get_model("schedules", "EducationGoal")
    for key, label, average, target, order in GOALS_2026:
        EducationGoal.objects.update_or_create(
            year=2026,
            key=key,
            defaults={
                "label": label,
                "average": average,
                "target": target,
                "order": order,
                "is_active": True,
            },
        )


def remove_goals(apps, schema_editor):
    EducationGoal = apps.get_model("schedules", "EducationGoal")
    EducationGoal.objects.filter(year=2026, key__in=[goal[0] for goal in GOALS_2026]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0020_educationgoal"),
    ]

    operations = [
        migrations.RunPython(seed_goals, remove_goals),
    ]
