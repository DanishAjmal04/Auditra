from django.core.management.base import BaseCommand

from compliance.notifications import send_pending_compliance_notifications


class Command(BaseCommand):
    help = 'Send pending compliance email notifications without duplicates'

    def handle(self, *args, **options):
        result = send_pending_compliance_notifications()
        self.stdout.write(self.style.SUCCESS(
            'Compliance notifications processed: '
            f"{result['sent']} sent, "
            f"{result['skipped']} skipped, "
            f"{result['failed']} failed."
        ))
