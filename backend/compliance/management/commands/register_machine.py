from django.core.management.base import BaseCommand, CommandError

from compliance.agent_security import generate_secret, hash_secret
from compliance.models import Machine


class Command(BaseCommand):
    help = 'Register a machine and print its one-time enrollment key.'

    def add_arguments(self, parser):
        parser.add_argument('machine_name')
        parser.add_argument('--replace', action='store_true', help='Replace an existing enrollment.')

    def handle(self, *args, **options):
        name = options['machine_name'].strip()
        if not name:
            raise CommandError('Machine name cannot be empty.')
        machine = Machine.objects.filter(name__iexact=name).first()
        created = machine is None
        if created:
            machine = Machine(name=name)
        if not created and machine.enrolled_at and not options['replace']:
            raise CommandError('Machine is already enrolled. Use --replace to revoke and re-enroll it.')
        enrollment_key = generate_secret('auditra_enroll')
        machine.enrollment_key_hash = hash_secret(enrollment_key)
        machine.credential_hash = ''
        machine.enrolled_at = None
        machine.last_seen_at = None
        machine.last_error = ''
        machine.is_active = True
        machine.save()
        self.stdout.write(self.style.SUCCESS(f'Machine: {machine.name}'))
        self.stdout.write(f'One-time enrollment key: {enrollment_key}')
        self.stdout.write('This key will not be shown again.')
