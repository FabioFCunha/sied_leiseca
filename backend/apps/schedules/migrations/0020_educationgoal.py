from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0019_educationaction_approached_actions_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="EducationGoal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("year", models.PositiveIntegerField()),
                ("key", models.CharField(max_length=80)),
                ("label", models.CharField(max_length=160)),
                ("average", models.PositiveIntegerField(default=0)),
                ("target", models.PositiveIntegerField(default=0)),
                ("order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["year", "order", "label"],
            },
        ),
        migrations.AddConstraint(
            model_name="educationgoal",
            constraint=models.UniqueConstraint(fields=("year", "key"), name="unique_education_goal_year_key"),
        ),
    ]
