from django.apps import AppConfig


class ComplianceConfig(AppConfig):
    name = 'compliance'

    def ready(self):
        from . import scheduler

        scheduler.start()
