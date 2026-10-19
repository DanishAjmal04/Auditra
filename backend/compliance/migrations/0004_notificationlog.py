import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compliance', '0003_dpo_verification'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_type', models.CharField(choices=[('CRITICAL_VIOLATION', 'Critical violation'), ('BREACH_DEADLINE', 'Breach deadline'), ('DSR_DEADLINE', 'Data-subject request deadline'), ('DPO_STATUS', 'DPO status')], max_length=30)),
                ('event_key', models.CharField(max_length=255, unique=True)),
                ('recipient', models.EmailField(max_length=254)),
                ('subject', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('SENT', 'Sent'), ('FAILED', 'Failed')], default='PENDING', max_length=10)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'notification_logs',
                'ordering': ['-created_at'],
            },
        ),
    ]
