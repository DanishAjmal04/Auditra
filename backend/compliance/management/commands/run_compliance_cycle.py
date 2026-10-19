from django.core.management.base import BaseCommand

from compliance.scheduler import run_compliance_cycle


class Command(BaseCommand):
    help = 'Run GDPR rules, anomaly detection, and pending notifications once.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--trigger',
            choices=['manual', 'scheduled'],
            default='manual',
            help='Label the source of this run in compliance job history.',
        )

    def handle(self, *args, **options):
        job = run_compliance_cycle(trigger=options['trigger'])
        summary = (
            f'{job.status}: {job.logs_processed} logs processed, '
            f'{job.violations_created} violations created, '
            f'{job.anomalies_flagged} anomalies flagged, '
            f'{job.notifications_sent} notifications sent, '
            f'{job.notifications_failed} notifications failed.'
        )

        if job.status == 'SUCCESS':
            self.stdout.write(self.style.SUCCESS(summary))
        elif job.status == 'SKIPPED':
            self.stdout.write(self.style.WARNING(f'{summary} {job.error_message}'))
        else:
            self.stdout.write(self.style.ERROR(summary))
