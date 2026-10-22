"""Runs the workflow rules (deadlines, breaches, automated decisions) once a minute inside the Django process."""
import logging
import os
import sys
import threading
import time

from django.db import close_old_connections
from django.utils import timezone

logger = logging.getLogger(__name__)
INTERVAL_SECONDS = int(os.getenv('AUDITRA_SCHEDULER_SECONDS', '60'))
_started = False


def run_compliance_cycle(trigger='SCHEDULED'):
    from .detection import workflow_rules
    from .incidents import raise_workflow, rule_map
    from .models import ComplianceJobRun
    from .notifications import send_pending_compliance_notifications

    job = ComplianceJobRun.objects.create(trigger=trigger.upper(), status='RUNNING')
    try:
        rules = rule_map()
        created = 0
        for finding in workflow_rules.evaluate():
            if raise_workflow(finding, rules=rules):
                created += 1
        notifications = send_pending_compliance_notifications()
        job.status = 'SUCCESS'
        job.incidents_created = created
        job.notifications_sent = notifications['sent']
        job.notifications_skipped = notifications['skipped']
        job.notifications_failed = notifications['failed']
    except Exception as exc:  # the loop must survive a bad cycle
        logger.exception('Compliance cycle failed')
        job.status = 'FAILED'
        job.error_message = str(exc)[:2000]
    job.completed_at = timezone.now()
    job.save()
    return job


def _loop():
    while True:
        time.sleep(INTERVAL_SECONDS)
        close_old_connections()
        try:
            run_compliance_cycle()
        finally:
            close_old_connections()


def start():
    """Start once, in the serving process only (not in the autoreloader parent, migrate or tests)."""
    global _started
    if _started or os.getenv('AUDITRA_SCHEDULER', 'on') == 'off':
        return
    argv = ' '.join(sys.argv)
    serving = 'runserver' in argv or 'gunicorn' in argv or 'waitress' in argv
    autoreload_parent = 'runserver' in argv and '--noreload' not in argv and os.environ.get('RUN_MAIN') != 'true'
    if not serving or autoreload_parent:
        return
    _started = True
    threading.Thread(target=_loop, name='auditra-scheduler', daemon=True).start()
