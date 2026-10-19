import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compliance', '0004_notificationlog'),
    ]

    operations = [
        migrations.CreateModel(
            name='ComplianceJobRun',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('trigger', models.CharField(choices=[('MANUAL', 'Manual'), ('SCHEDULED', 'Scheduled')], max_length=10)),
                ('status', models.CharField(choices=[('RUNNING', 'Running'), ('SUCCESS', 'Success'), ('FAILED', 'Failed'), ('SKIPPED', 'Skipped')], default='RUNNING', max_length=10)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('logs_processed', models.PositiveIntegerField(default=0)),
                ('violations_created', models.PositiveIntegerField(default=0)),
                ('anomalies_flagged', models.PositiveIntegerField(default=0)),
                ('notifications_sent', models.PositiveIntegerField(default=0)),
                ('notifications_skipped', models.PositiveIntegerField(default=0)),
                ('notifications_failed', models.PositiveIntegerField(default=0)),
                ('error_message', models.TextField(blank=True)),
            ],
            options={
                'db_table': 'compliance_job_runs',
                'ordering': ['-started_at'],
            },
        ),
    ]
