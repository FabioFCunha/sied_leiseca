from django.db import migrations, models

import apps.accounts.models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0015_user_lgpd_consent_at")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="access_areas",
            field=models.JSONField(
                blank=True,
                default=apps.accounts.models.default_user_access_areas,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="is_read_only",
            field=models.BooleanField(default=False),
        ),
    ]
