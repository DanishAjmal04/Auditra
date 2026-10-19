import re

from django.contrib.auth.hashers import make_password
from django.db import migrations


def migrate_system_users(apps, schema_editor):
    SystemUser = apps.get_model('compliance', 'SystemUser')
    AuditraUser = apps.get_model('compliance', 'AuditraUser')

    for old_user in SystemUser.objects.all().iterator():
        existing = AuditraUser.objects.filter(email__iexact=old_user.email).first()
        if existing:
            continue

        base_username = re.sub(
            r'[^\w.@+-]',
            '_',
            old_user.email.split('@')[0]
        ) or 'user'
        username = base_username
        suffix = 1
        while AuditraUser.objects.filter(username=username).exists():
            suffix += 1
            username = f'{base_username}{suffix}'

        name_parts = old_user.name.split(maxsplit=1)
        role = (
            'admin'
            if old_user.role == 'ADMIN'
            else 'compliance_officer'
        )

        old_password = old_user.password or ''
        is_legacy_sha256 = bool(re.fullmatch(r'[0-9a-fA-F]{64}', old_password))
        password = (
            make_password(None)
            if is_legacy_sha256
            else make_password(old_password)
        )

        AuditraUser.objects.create(
            username=username,
            email=old_user.email,
            first_name=name_parts[0] if name_parts else '',
            last_name=name_parts[1] if len(name_parts) > 1 else '',
            role=role,
            is_active=old_user.status == 'ACTIVE',
            is_staff=role == 'admin',
            password=password,
            date_joined=old_user.created_at,
        )


class Migration(migrations.Migration):
    dependencies = [
        ('compliance', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            migrate_system_users,
            migrations.RunPython.noop,
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(
                    name='SystemUser',
                ),
            ],
        ),
    ]
