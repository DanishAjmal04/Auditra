from django.core.management.base import BaseCommand
from compliance.models import AuditraUser

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if not AuditraUser.objects.filter(username='admin').exists():
            AuditraUser.objects.create_superuser(
                username='admin',
                email='admin@auditra.com',
                password='Admin@2026',
                role='admin'
            )
            self.stdout.write('Admin created.')

        if not AuditraUser.objects.filter(
            username='compliance_officer'
        ).exists():
            user = AuditraUser(
                username='compliance_officer',
                email='compliance@auditra.com',
                role='compliance_officer'
            )
            user.set_password('Auditra@2026')
            user.save()
            self.stdout.write('Compliance officer created.')