import random
from datetime import datetime, timedelta, timezone
from django.core.management.base import BaseCommand
from compliance.models import Log, Rule

USERS = [
    ('u_hassan', 'analyst'),
    ('u_ayesha', 'hr'),
    ('u_tariq', 'intern'),
    ('u_zara', 'auditor'),
    ('u_bilal', 'admin'),
    ('u_nadia', 'analyst'),
    ('u_omar', 'intern'),
    ('u_sara', 'hr'),
]

RESOURCES = {
    'HIGH':   ['patient_records', 'financial_reports', 'personal_data_export', 'salary_database'],
    'MEDIUM': ['project_files', 'employee_directory', 'audit_logs'],
    'LOW':    ['public_reports', 'company_policies', 'meeting_notes'],
}

PURPOSES = [
    'routine audit', 'data analysis', 'compliance review',
    'project work', '', '', '',
]

class Command(BaseCommand):
    help = 'Seed synthetic logs and GDPR rules into the database'

    def handle(self, *args, **kwargs):
        self.seed_rules()
        self.seed_logs()
        self.stdout.write(self.style.SUCCESS('Database seeded successfully.'))

    def seed_rules(self):
        rules = [
            ('R001', 'Article 5',  'Access to HIGH sensitivity data without declared purpose', 'HIGH'),
            ('R002', 'Article 32', 'HIGH sensitivity data accessed outside business hours (9am-6pm)', 'CRITICAL'),
            ('R003', 'Article 25', 'Intern role accessed HIGH sensitivity resource', 'HIGH'),
            ('R004', 'Article 5',  'EXPORT action performed on HIGH sensitivity data', 'CRITICAL'),
            ('R005', 'Article 32', 'Excessive access: same resource accessed more than 5 times in one day', 'MEDIUM'),
            ('R006', 'Article 33', 'DELETE action on HIGH sensitivity data', 'CRITICAL'),
        ]
        for rule_id, article, desc, severity in rules:
            Rule.objects.get_or_create(
                rule_id=rule_id,
                defaults={
                    'gdpr_article': article,
                    'description': desc,
                    'severity': severity,
                }
            )
        self.stdout.write('  Rules seeded.')

    def seed_logs(self):
        if Log.objects.exists():
            self.stdout.write('  Logs already exist, skipping.')
            return

        now = datetime.now(timezone.utc)
        logs = []

        for _ in range(500):
            user_id, role = random.choice(USERS)
            sensitivity = random.choices(
                ['HIGH', 'MEDIUM', 'LOW'],
                weights=[25, 40, 35]
            )[0]
            resource = random.choice(RESOURCES[sensitivity])
            action = random.choices(
                ['READ', 'WRITE', 'EXPORT', 'DELETE', 'LOGIN'],
                weights=[50, 20, 10, 5, 15]
            )[0]
            # 30% of logs happen outside business hours
            if random.random() < 0.30:
                hour = random.choice(list(range(0, 9)) + list(range(18, 24)))
            else:
                hour = random.randint(9, 17)

            days_ago = random.randint(0, 29)
            timestamp = now - timedelta(days=days_ago, hours=random.randint(0, 23))
            timestamp = timestamp.replace(hour=hour, minute=random.randint(0, 59))

            logs.append(Log(
                user_id=user_id,
                role=role,
                timestamp=timestamp,
                resource_accessed=resource,
                action=action,
                sensitivity=sensitivity,
                ip_address=f'192.168.1.{random.randint(1, 254)}',
                declared_purpose=random.choice(PURPOSES),
            ))

        Log.objects.bulk_create(logs)
        self.stdout.write(f'  {len(logs)} logs seeded.')