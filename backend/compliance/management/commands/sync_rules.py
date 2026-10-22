from django.core.management.base import BaseCommand

from compliance.models import Rule
from compliance.rules_catalogue import sync_rules


class Command(BaseCommand):
    help = 'Create or update the detection rules from compliance/rules_catalogue.py.'

    def handle(self, *args, **options):
        created = sync_rules(Rule)
        self.stdout.write(self.style.SUCCESS(f'{Rule.objects.count()} rules ({created} new).'))
