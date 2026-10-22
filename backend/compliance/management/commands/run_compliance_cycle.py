from django.core.management.base import BaseCommand

from compliance.scheduler import run_compliance_cycle


class Command(BaseCommand):
    help = 'Run the GDPR workflow rules (deadlines, breaches, automated decisions) and notifications once.'

    def handle(self, *args, **options):
        job = run_compliance_cycle(trigger='MANUAL')
        summary = (f'{job.status}: {job.incidents_created} incidents created, '
                   f'{job.notifications_sent} notifications sent, {job.notifications_failed} failed.')
        style = self.style.SUCCESS if job.status == 'SUCCESS' else self.style.ERROR
        self.stdout.write(style(summary))
