from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random


class Command(BaseCommand):
    help = 'Seed database with rules and sample data'

    def handle(self, *args, **kwargs):
        self.seed_rules()
        self.seed_users()
        self.seed_consent_records()
        self.seed_subject_requests()
        self.seed_processing_activities()
        self.seed_dpo_record()
        self.seed_logs()
        self.seed_breach_samples()
        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))

    def seed_rules(self):
        from compliance.models import Rule
        Rule.objects.all().delete()

        rules = [
            ('Art. 5', 'Bulk export of personal records without declared purpose', 'action=EXPORT AND sensitivity=HIGH AND purpose=NULL', 'CRITICAL'),
            ('Art. 6', 'Processing personal data without valid lawful basis', 'sensitivity=HIGH AND purpose=NULL', 'HIGH'),
            ('Art. 7', 'Processing continues after consent withdrawal', 'consent_withdrawn=TRUE AND active_processing=TRUE', 'CRITICAL'),
            ('Art. 9', 'Unauthorized access to special category data', 'resource IN special_category AND purpose=NULL', 'CRITICAL'),
            ('Art. 10', 'Unauthorized access to criminal offence data', 'resource IN criminal_data', 'CRITICAL'),
            ('Art. 15', 'Subject access request not fulfilled within 30 days', 'right_type=ACCESS AND overdue=TRUE', 'HIGH'),
            ('Art. 16', 'Rectification request not fulfilled within 30 days', 'right_type=RECTIFICATION AND overdue=TRUE', 'MEDIUM'),
            ('Art. 17', 'Erasure request not fulfilled within 30 days', 'right_type=ERASURE AND overdue=TRUE', 'HIGH'),
            ('Art. 18', 'Restriction of processing not applied', 'right_type=RESTRICTION AND overdue=TRUE', 'MEDIUM'),
            ('Art. 20', 'Data portability request denied', 'right_type=PORTABILITY AND overdue=TRUE', 'MEDIUM'),
            ('Art. 21', 'Objection to processing not respected', 'right_type=OBJECTION AND overdue=TRUE', 'HIGH'),
            ('Art. 22', 'Automated decision without human review', 'resource IN automated AND purpose NOT CONTAINS human', 'HIGH'),
            ('Art. 25', 'Access beyond role scope — data minimisation violation', 'role_sensitivity_mismatch=TRUE', 'HIGH'),
            ('Art. 29', 'Processor acting beyond controller instructions', 'action=EXPORT AND purpose CONTAINS processor', 'HIGH'),
            ('Art. 30', 'Processing activity not in Records of Processing Activities', 'ropa_exists=FALSE AND sensitivity=HIGH', 'MEDIUM'),
            ('Art. 32', 'After-hours access to sensitive data', 'outside_hours=TRUE AND sensitivity=HIGH', 'HIGH'),
            ('Art. 33', 'Data breach not reported within 72 hours', 'breach_unreported=TRUE AND deadline_passed=TRUE', 'CRITICAL'),
            ('Art. 34', 'Data subjects not notified of high risk breach', 'breach_high_risk=TRUE AND subjects_notified=FALSE', 'HIGH'),
            ('Art. 37', 'No DPO designated for high-risk processing', 'dpo_exists=FALSE AND sensitivity=HIGH', 'HIGH'),
            ('Art. 83', 'High penalty risk — repeated violations by same user', 'violations_last_7_days >= 5', 'CRITICAL'),
            ('ML-ANOMALY', 'Unusual user-day scored by the CERT-trained One-Class SVM', 'anomaly_pct > 60', 'HIGH'),
            ('Art. 87', 'National ID data processed without safeguards', 'resource IN national_id AND purpose=NULL', 'HIGH'),
            ('Art. 88', 'Employee data processed without legal basis', 'resource IN employee_data AND purpose=NULL AND action IN [EXPORT,DELETE]', 'HIGH'),
        ]

        for article, desc, logic, severity in rules:
            Rule.objects.create(
                gdpr_article=article,
                description=desc,
                logic_definition=logic,
                severity=severity,
                enabled=True
            )

        self.stdout.write(f'  OK {len(rules)} rules created')

    def seed_users(self):
        from compliance.models import AuditraUser

        users = [
            ('admin', 'Admin User', 'admin@auditra.com', 'Auditra@2026', 'admin'),
            ('compliance_officer', 'Compliance Officer', 'compliance@auditra.com', 'Auditra@2026', 'compliance_officer'),
            ('sara', 'Sara Ahmed', 'sara@auditra.com', 'Sara@2026', 'compliance_officer'),
            ('ali', 'Ali Raza', 'ali@auditra.com', 'Ali@2026', 'compliance_officer'),
        ]

        for username, name, email, password, role in users:
            name_parts = name.split(maxsplit=1)
            user, _ = AuditraUser.objects.update_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': name_parts[0],
                    'last_name': name_parts[1] if len(name_parts) > 1 else '',
                    'role': role,
                    'is_active': True,
                    'is_staff': role == 'admin',
                }
            )
            user.set_password(password)
            user.save(update_fields=['password'])

        self.stdout.write(f'  OK {len(users)} Auditra users created or updated')

    def seed_consent_records(self):
        from compliance.models import ConsentRecord
        ConsentRecord.objects.all().delete()

        records = [
            ('u_hassan', 'Marketing emails', 'CONSENT', False, True),
            ('u_ayesha', 'Analytics tracking', 'CONSENT', False, True),
            ('u_tariq', 'Payroll processing', 'CONTRACT', True, True),
            ('u_zara', 'Third party sharing', 'CONSENT', False, False),
            ('u_bilal', 'Product recommendations', 'LEGITIMATE_INTEREST', True, True),
            ('u_nadia', 'Customer support logs', 'CONTRACT', True, True),
            ('u_omar', 'Newsletter subscription', 'CONSENT', False, True),
            ('u_sara', 'HR data processing', 'LEGAL_OBLIGATION', True, True),
        ]

        for user_id, purpose, basis, is_valid, active in records:
            ConsentRecord.objects.create(
                user_id=user_id,
                purpose=purpose,
                lawful_basis=basis,
                declared_at=timezone.now() - timedelta(days=random.randint(30, 365)),
                is_valid=is_valid,
                active_processing=active
            )

        self.stdout.write(f'  OK {len(records)} consent records created')

    def seed_subject_requests(self):
        from compliance.models import DataSubjectRequest
        DataSubjectRequest.objects.all().delete()

        now = timezone.now()

        requests = [
            ('user_1042', 'ACCESS', now - timedelta(days=35), now - timedelta(days=5)),
            ('user_0893', 'RECTIFICATION', now - timedelta(days=28), now - timedelta(days=2)),
            ('user_1187', 'PORTABILITY', now - timedelta(days=15), now + timedelta(days=15)),
            ('user_0654', 'RESTRICTION', now - timedelta(days=10), now + timedelta(days=20)),
            ('user_1301', 'OBJECTION', now - timedelta(days=40), now - timedelta(days=10)),
            ('user_0421', 'ERASURE', now - timedelta(days=5), now + timedelta(days=25)),
            ('user_0992', 'ACCESS', now - timedelta(days=20), now + timedelta(days=10)),
            ('u_hassan', 'ERASURE', now - timedelta(days=40), now - timedelta(days=10)),
        ]

        statuses = [
            'PENDING', 'IN_PROGRESS', 'COMPLETED', 'PENDING',
            'PENDING', 'IN_PROGRESS', 'PENDING', 'PENDING',
        ]

        for i, (subject, right, received, deadline) in enumerate(requests):
            DataSubjectRequest.objects.create(
                subject_id=subject,
                right_type=right,
                received_at=received,
                response_deadline=deadline,
                status=statuses[i]
            )

        self.stdout.write(f'  OK {len(requests)} subject requests created')

    def seed_processing_activities(self):
        from compliance.models import ProcessingActivity
        ProcessingActivity.objects.all().delete()

        activities = [
            ('Payroll Processing', 'Payroll', 'CONTRACT', 'financial data, employee records', '7 years', 'Encryption, access control'),
            ('Customer Analytics', 'Analytics', 'LEGITIMATE_INTEREST', 'usage data, behavioral data', '2 years', 'Anonymization, pseudonymization'),
            ('HR Management', 'HR', 'LEGAL_OBLIGATION', 'employee records, performance data', '5 years', 'Role-based access, audit logs'),
            ('Marketing Emails', 'Marketing', 'CONSENT', 'email addresses, preferences', '1 year', 'Opt-out mechanism, encryption'),
        ]

        for name, purpose, basis, categories, retention, measures in activities:
            ProcessingActivity.objects.create(
                activity_name=name,
                purpose=purpose,
                legal_basis=basis,
                data_categories=categories,
                retention_period=retention,
                security_measures=measures
            )

        self.stdout.write(f'  OK {len(activities)} processing activities created')

    def seed_dpo_record(self):
        from compliance.models import DPORecord
        from datetime import date
        DPORecord.objects.all().delete()

        DPORecord.objects.create(
            organization_name='Auditra',
            dpo_required=True,
            name='Dr. Hina Iqbal',
            contact='dpo@auditra.com',
            designated_at=date(2024, 1, 1),
            scope='All personal data processing activities across the organization',
            independent=True,
            direct_access_to_management=True,
            conflict_free=True,
            published_contact_details=True,
        )

        self.stdout.write('  OK DPO record created')

    def seed_logs(self):
        from compliance.log_generator import generate_bulk_logs
        from compliance.rule_engine import check_all_rules

        logs = generate_bulk_logs(200)

        violation_count = 0
        for log in logs:
            violations = check_all_rules(log)
            violation_count += len(violations)

        self.stdout.write(f'  OK 200 logs generated')
        self.stdout.write(f'  OK {violation_count} violations detected')

    def seed_breach_samples(self):
        from compliance.models import BreachRecord, Log, Violation
        from compliance.rule_engine import check_all_rules, check_overdue_breaches

        access_log = Log.objects.create(
            user_id='user_1042',
            timestamp=timezone.now(),
            resource_accessed='customer_data',
            action='READ',
            resource_sensitivity='LOW',
            ip_address='192.168.1.10',
            purpose='Subject follow-up',
            is_outside_hours=False,
        )
        check_all_rules(access_log)

        violation = (
            Violation.objects
            .filter(rule__severity='CRITICAL')
            .order_by('-detected_at')
            .first()
        ) or Violation.objects.order_by('-detected_at').first()
        if violation is None:
            self.stdout.write('  ! No violation available for breach samples')
            return

        BreachRecord.objects.all().delete()
        BreachRecord.objects.create(
            violation=violation,
            notification_deadline=timezone.now() - timedelta(hours=6),
            notification_sent=False,
            severity='CRITICAL',
        )
        other = Violation.objects.exclude(pk=violation.pk).first()
        if other is not None:
            BreachRecord.objects.create(
                violation=other,
                notification_deadline=timezone.now() + timedelta(hours=20),
                notification_sent=False,
                severity='HIGH',
            )
        created = check_overdue_breaches()
        self.stdout.write(f'  OK Breach samples created ({len(created)} deadline violations)')
