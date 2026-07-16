from django.db import migrations, models


def sync_education_goals(apps, schema_editor):
    EducationGoal = apps.get_model("schedules", "EducationGoal")

    years = list(EducationGoal.objects.values_list("year", flat=True).distinct())
    for year in years:
        other_goal = EducationGoal.objects.filter(year=year, key="other_actions").first()
        if not other_goal:
            continue

        EducationGoal.objects.filter(year=year, order__gte=other_goal.order).update(order=models.F("order") + 1)
        EducationGoal.objects.update_or_create(
            year=year,
            key="joint_inspections",
            defaults={
                "label": "3.8 - A\u00c7\u00c3O CONJUNTA COM A FISCALIZA\u00c7\u00c3O",
                "average": 0,
                "target": 0,
                "order": other_goal.order,
                "is_active": True,
            },
        )
        EducationGoal.objects.filter(year=year, key="other_actions").update(
            label="3.9 - OUTROS",
            order=other_goal.order + 1,
        )


def revert_education_goals(apps, schema_editor):
    EducationGoal = apps.get_model("schedules", "EducationGoal")

    years = list(EducationGoal.objects.values_list("year", flat=True).distinct())
    for year in years:
        joint_goal = EducationGoal.objects.filter(year=year, key="joint_inspections").first()
        if not joint_goal:
            continue

        old_order = joint_goal.order
        joint_goal.delete()
        EducationGoal.objects.filter(year=year, key="other_actions").update(
            label="3.8 - OUTROS",
            order=old_order,
        )
        EducationGoal.objects.filter(year=year, order__gt=old_order).update(order=models.F("order") - 1)


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0063_alter_educationreport_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="educationaction",
            name="joint_inspections",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(sync_education_goals, revert_education_goals),
    ]
