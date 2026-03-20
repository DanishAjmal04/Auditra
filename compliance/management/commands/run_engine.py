from django.core.management.base import BaseCommand
from compliance.engine import run_rule_engine

class Command(BaseCommand):
    help = 'Run the GDPR compliance rule engine on all logs'

    def handle(self, *args, **kwargs):
        count = run_rule_engine()
        self.stdout.write(self.style.SUCCESS(f'{count} new violations detected.'))