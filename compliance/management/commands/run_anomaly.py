from django.core.management.base import BaseCommand
from compliance.anomaly import run_anomaly_detection

class Command(BaseCommand):
    help = 'Run Isolation Forest anomaly detection on logs'

    def handle(self, *args, **kwargs):
        count = run_anomaly_detection()
        self.stdout.write(self.style.SUCCESS(f'{count} violations flagged as anomalies.'))