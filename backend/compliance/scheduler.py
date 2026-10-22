import threading
from contextlib import contextmanager

from django.db import connection
from django.utils import timezone

from .anomaly_detector import run_anomaly_detection
from .models import ComplianceJobRun, Log, Violation
from .notifications import send_pending_compliance_notifications
from .rule_engine import check_all_rules, check_overdue_breaches


ADVISORY_LOCK_ID = 412_803_701
_local_lock = threading.Lock()


@contextmanager
def compliance_cycle_lock():
    """Prevent overlapping cycles across scheduler and manual invocations."""
    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_try_advisory_lock(%s)', [ADVISORY_LOCK_ID])
            acquired = cursor.fetchone()[0]
            try:
                yield acquired
            finally:
                if acquired:
                    cursor.execute('SELECT pg_advisory_unlock(%s)', [ADVISORY_LOCK_ID])
        return

    acquired = _local_lock.acquire(blocking=False)
    try:
        yield acquired
    finally:
        if acquired:
            _local_lock.release()


def run_compliance_cycle(trigger='SCHEDULED'):
    trigger = trigger.upper()
    valid_triggers = {choice[0] for choice in ComplianceJobRun.TRIGGER_CHOICES}
    if trigger not in valid_triggers:
        raise ValueError(f'Unsupported compliance-cycle trigger: {trigger}')

    with compliance_cycle_lock() as acquired:
        if not acquired:
            now = timezone.now()
            return ComplianceJobRun.objects.create(
                trigger=trigger,
                status='SKIPPED',
                completed_at=now,
                error_message='Another compliance cycle is already running.',
            )

        previous_run = (
            ComplianceJobRun.objects
            .filter(status='SUCCESS', completed_at__isnull=False)
            .order_by('-completed_at')
            .first()
        )
        job = ComplianceJobRun.objects.create(trigger=trigger, status='RUNNING')

        try:
            logs = Log.objects.all().order_by('created_at')
            if previous_run:
                logs = logs.filter(created_at__gt=previous_run.completed_at)

            violations_before = Violation.objects.count()
            logs_processed = 0
            for log in logs.iterator(chunk_size=500):
                check_all_rules(log)
                logs_processed += 1

            check_overdue_breaches()
            anomalies_flagged = run_anomaly_detection()
            notifications = send_pending_compliance_notifications()

            job.status = 'SUCCESS'
            job.completed_at = timezone.now()
            job.logs_processed = logs_processed
            job.violations_created = Violation.objects.count() - violations_before
            job.anomalies_flagged = anomalies_flagged
            job.notifications_sent = notifications['sent']
            job.notifications_skipped = notifications['skipped']
            job.notifications_failed = notifications['failed']
            job.save(update_fields=[
                'status', 'completed_at', 'logs_processed', 'violations_created',
                'anomalies_flagged', 'notifications_sent',
                'notifications_skipped', 'notifications_failed',
            ])
        except Exception as exc:
            job.status = 'FAILED'
            job.completed_at = timezone.now()
            job.error_message = str(exc)[:2000]
            job.save(update_fields=['status', 'completed_at', 'error_message'])
            raise

        return job
