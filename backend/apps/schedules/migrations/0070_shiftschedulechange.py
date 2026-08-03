from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('schedules', '0069_agenda_geocoding'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ShiftScheduleChange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('EXTRA', 'Inclusao de extra'), ('REMOVED', 'Retirada')], max_length=16)),
                ('member_type', models.CharField(choices=[('CHIEF', 'Chefe'), ('AGENT', 'Agente'), ('SUPPORT', 'Apoio')], max_length=16)),
                ('member_id', models.PositiveIntegerField()),
                ('member_name', models.CharField(max_length=180)),
                ('reason', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_shift_schedule_changes', to=settings.AUTH_USER_MODEL)),
                ('schedule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='member_changes', to='schedules.shiftschedule')),
            ],
            options={
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='shiftschedulechange',
            index=models.Index(fields=['schedule', 'created_at'], name='shift_ch_sched_created_idx'),
        ),
        migrations.AddIndex(
            model_name='shiftschedulechange',
            index=models.Index(fields=['schedule', 'action', 'member_type'], name='shift_ch_sched_action_type_idx'),
        ),
    ]
