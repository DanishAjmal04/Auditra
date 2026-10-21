import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from compliance.anomaly_detector import run_anomaly_detection
from compliance.models import Log, Rule, Violation
from compliance.rule_engine import check_all_rules

FIXTURE = Path(__file__).resolve().parents[2] / 'demo' / 'anomaly_demo_events.json'
DEMO_USERS = ('demo_insider', 'demo_colleague')


class Command(BaseCommand):
    help = 'Load the committed anomaly demo and score it with the One-Class SVM.'

    def handle(self, *args, **options):
        if not FIXTURE.is_file():
            self.stderr.write(self.style.ERROR(f'Missing fixture: {FIXTURE}'))
            return

        Rule.objects.get_or_create(
            gdpr_article='ML-ANOMALY',
            defaults={
                'description': 'Unusual user-day scored by the CERT-trained One-Class SVM',
                'logic_definition': 'anomaly_pct > 60',
                'severity': 'HIGH',
                'enabled': True,
            },
        )

        events = json.loads(FIXTURE.read_text(encoding='utf-8'))
        Log.objects.filter(user_id__in=DEMO_USERS).delete()

        created_logs = 0
        rule_hits = 0
        for entry in events:
            timestamp = parse_datetime(entry['timestamp'])
            if timestamp is None:
                timestamp = timezone.now()
            if timezone.is_naive(timestamp):
                timestamp = timezone.make_aware(timestamp)
            outside = timestamp.hour < 8 or timestamp.hour > 18
            log = Log.objects.create(
                user_id=entry.get('user_id', 'demo_insider'),
                timestamp=timestamp,
                resource_accessed=entry.get('resource_accessed', 'workstation'),
                action=entry.get('action', 'READ'),
                resource_sensitivity=entry.get('resource_sensitivity', 'MEDIUM'),
                ip_address=entry.get('ip_address', '127.0.0.1'),
                purpose=entry.get('purpose') or 'Recorded activity',
                is_outside_hours=outside,
            )
            rule_hits += len(check_all_rules(log))
            created_logs += 1

        anomalies = run_anomaly_detection()
        flagged = Violation.objects.filter(
            is_anomaly=True,
            log__user_id__in=DEMO_USERS,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Loaded {created_logs} demo logs, {rule_hits} rule hits, '
            f'{anomalies} new anomaly rows.'
        ))
        for violation in flagged.order_by('-risk_score')[:5]:
            self.stdout.write(
                f'  {violation.log.user_id} {violation.risk_score:.2f} — {violation.reason}'
            )
