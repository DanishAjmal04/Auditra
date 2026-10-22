from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from compliance.anomaly_detector import run_anomaly_detection
from compliance.models import BreachRecord, Log, Rule
from compliance.rule_engine import check_all_rules

SARA = 'HR-LAPTOP\\sara.ahmed'
ALI = 'FINANCE-PC\\ali.raza'


class Command(BaseCommand):
    help = 'Load normal weekday activity so the dashboard starts quiet.'

    def handle(self, *args, **options):
        Rule.objects.get_or_create(
            gdpr_article='ML-ANOMALY',
            defaults={
                'description': 'Unusual user-day scored by the CERT-trained One-Class SVM',
                'logic_definition': 'anomaly_pct > 60',
                'severity': 'HIGH',
                'enabled': True,
            },
        )

        events = []
        events.extend(self._normal_days(SARA, '10.4.1.20', 'employee_records'))
        events.extend(self._normal_days(ALI, '10.4.2.15', 'customer_data'))

        BreachRecord.objects.all().delete()
        Log.objects.all().delete()

        rule_hits = 0
        for entry in events:
            log = Log.objects.create(**entry)
            rule_hits += len(check_all_rules(log))

        anomalies = run_anomaly_detection()
        self.stdout.write(self.style.SUCCESS(
            f'Quiet baseline loaded: {len(events)} normal logs, '
            f'{rule_hits} rule hits, {anomalies} anomaly rows.'
        ))
        self.stdout.write('Leave the dashboard open, then run:')
        self.stdout.write('  python manage.py stream_incident')

    def incident_night(self):
        night = timezone.now().replace(hour=21, minute=15, second=0, microsecond=0)
        if night > timezone.now():
            night = night - timedelta(days=1)
        return night

    def incident_events(self):
        return self._incident(self.incident_night())

    def _normal_days(self, user_id, ip, resource):
        rows = []
        day = timezone.now().replace(hour=10, minute=5, second=0, microsecond=0)
        picked = []
        while len(picked) < 3:
            day = day - timedelta(days=1)
            if day.weekday() < 5:
                picked.append(day)
        for start in picked:
            rows.append(self._event(user_id, start, 'LOGIN', 'workstation', 'LOW', ip, 'Shift start'))
            for step in range(4):
                rows.append(self._event(
                    user_id,
                    start + timedelta(minutes=15 + step * 10),
                    'READ',
                    resource,
                    'MEDIUM',
                    ip,
                    'Payroll',
                ))
            rows.append(self._event(
                user_id,
                start + timedelta(hours=7),
                'LOGOUT',
                'workstation',
                'LOW',
                ip,
                'Shift end',
            ))
        return rows

    def _incident(self, night):
        hosts = [f'10.9.4.{index}' for index in range(1, 7)]
        rows = []
        for index in range(12):
            rows.append(self._event(
                SARA,
                night + timedelta(minutes=index * 2),
                'LOGIN',
                'workstation',
                'LOW',
                hosts[index % 6],
                'Windows event log',
            ))
        for index in range(8):
            rows.append(self._event(
                SARA,
                night + timedelta(minutes=30 + index),
                'EXPORT',
                'patient_records',
                'HIGH',
                hosts[index % 6],
                None,
            ))
        for index in range(4):
            rows.append(self._event(
                SARA,
                night + timedelta(minutes=45 + index),
                'WRITE',
                'removable_media',
                'HIGH',
                hosts[index % 6],
                None,
            ))
        return rows

    def _event(self, user_id, timestamp, action, resource, sensitivity, ip, purpose):
        return {
            'user_id': user_id,
            'timestamp': timestamp,
            'resource_accessed': resource,
            'action': action,
            'resource_sensitivity': sensitivity,
            'ip_address': ip,
            'purpose': purpose,
            'is_outside_hours': timestamp.hour < 8 or timestamp.hour > 18,
        }
