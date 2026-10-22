from django.core.management.base import BaseCommand
from django.db import transaction

from compliance.models import (
    Agent, AiDayScore, AuditEntry, AutomatedDecision, BreachRecord, CatalogueEntry, ComplianceJobRun,
    ConsentRecord, DataSubject, DataSubjectRequest, DPORecord, Employee, Event, Incident, NotificationLog,
    ProcessingActivity, Report,
)


class Command(BaseCommand):
    help = ('Delete recorded activity (events, incidents, AI scores). With --all-config also delete the '
            'organisation setup: employees, catalogue, data subjects, GDPR records, agents and the audit trail. '
            'Login accounts and rules are kept.')

    def add_arguments(self, parser):
        parser.add_argument('--all-config', action='store_true')
        parser.add_argument('--yes', action='store_true', help='Do not ask for confirmation.')

    def handle(self, *args, **options):
        scope = 'activity AND organisation configuration' if options['all_config'] else 'recorded activity'
        if not options['yes']:
            answer = input(f'This permanently deletes {scope}. Type RESET to continue: ')
            if answer.strip() != 'RESET':
                self.stdout.write('Cancelled.')
                return
        models = [BreachRecord, Incident, Event, AiDayScore, NotificationLog, ComplianceJobRun, Report]
        if options['all_config']:
            models += [AutomatedDecision, DataSubjectRequest, ConsentRecord, DataSubject, CatalogueEntry,
                       ProcessingActivity, Employee, Agent, DPORecord, AuditEntry]
        with transaction.atomic():
            for model in models:
                deleted = model.objects.all().delete()[0]
                self.stdout.write(f'{model.__name__}: {deleted} deleted')
        self.stdout.write(self.style.SUCCESS('Done.'))
