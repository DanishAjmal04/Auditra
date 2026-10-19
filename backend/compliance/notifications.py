from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone


def get_alert_recipients():
    configured = getattr(settings, 'COMPLIANCE_ALERT_RECIPIENTS', [])
    if configured:
        return sorted(set(configured))

    from .models import AuditraUser

    return list(
        AuditraUser.objects
        .filter(
            is_active=True,
            role__in=['admin', 'compliance_officer'],
        )
        .exclude(email='')
        .values_list('email', flat=True)
        .distinct()
    )


def send_compliance_notification(event_type, event_key, subject, message, recipients=None):
    from .models import NotificationLog

    recipients = recipients if recipients is not None else get_alert_recipients()
    result = {'sent': 0, 'skipped': 0, 'failed': 0}

    for recipient in sorted(set(recipients)):
        recipient_key = f'{event_key}:{recipient}'
        notification, created = NotificationLog.objects.get_or_create(
            event_key=recipient_key,
            defaults={
                'event_type': event_type,
                'recipient': recipient,
                'subject': subject,
                'message': message,
            },
        )

        if not created and notification.status == 'SENT':
            result['skipped'] += 1
            continue

        notification.event_type = event_type
        notification.recipient = recipient
        notification.subject = subject
        notification.message = message
        notification.status = 'PENDING'
        notification.error_message = ''
        notification.save()

        try:
            delivered = send_mail(
                subject=f'[Auditra] {subject}',
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            if delivered != 1:
                raise RuntimeError('Email backend did not confirm delivery')
        except Exception as exc:
            notification.status = 'FAILED'
            notification.error_message = str(exc)[:2000]
            notification.save(update_fields=['status', 'error_message'])
            result['failed'] += 1
        else:
            notification.status = 'SENT'
            notification.sent_at = timezone.now()
            notification.save(update_fields=['status', 'sent_at'])
            result['sent'] += 1

    return result


def notify_critical_violation(violation):
    return send_compliance_notification(
        event_type='CRITICAL_VIOLATION',
        event_key=f'critical-violation:{violation.id}',
        subject=f'Critical GDPR violation: {violation.rule.gdpr_article}',
        message=(
            f'A critical compliance violation was detected.\n\n'
            f'Article: {violation.rule.gdpr_article}\n'
            f'User: {violation.log.user_id}\n'
            f'Resource: {violation.log.resource_accessed}\n'
            f'Reason: {violation.reason}\n'
            f'Risk score: {violation.risk_score}\n'
            f'Detected at: {violation.detected_at.isoformat()}\n'
        ),
    )


def send_pending_compliance_notifications(now=None):
    from .models import BreachRecord, DPORecord, DataSubjectRequest, Violation

    now = now or timezone.now()
    totals = {'sent': 0, 'skipped': 0, 'failed': 0}

    def add_result(result):
        for key in totals:
            totals[key] += result[key]

    critical_violations = Violation.objects.select_related('log', 'rule').filter(
        rule__severity='CRITICAL',
        status='OPEN',
        detected_at__gte=now - timedelta(hours=24),
    ).order_by('-detected_at')[:20]
    for violation in critical_violations:
        add_result(notify_critical_violation(violation))

    deadline_window = now + timedelta(hours=24)
    breaches = BreachRecord.objects.select_related('violation').filter(
        notification_sent=False,
        notification_deadline__lte=deadline_window,
    )
    for breach in breaches:
        overdue = breach.notification_deadline < now
        add_result(send_compliance_notification(
            event_type='BREACH_DEADLINE',
            event_key=f'breach-deadline:{breach.id}',
            subject=(
                'Breach notification deadline overdue'
                if overdue else 'Breach notification deadline approaching'
            ),
            message=(
                f'Breach severity: {breach.severity}\n'
                f'Notification deadline: {breach.notification_deadline.isoformat()}\n'
                f'Status: {"OVERDUE" if overdue else "DUE WITHIN 24 HOURS"}\n'
                f'Violation reference: {breach.violation_id}\n'
            ),
        ))

    request_window = now + timedelta(days=3)
    requests = DataSubjectRequest.objects.filter(
        status__in=['PENDING', 'IN_PROGRESS'],
        response_deadline__lte=request_window,
    )
    for subject_request in requests:
        overdue = subject_request.response_deadline < now
        add_result(send_compliance_notification(
            event_type='DSR_DEADLINE',
            event_key=f'dsr-deadline:{subject_request.id}',
            subject=(
                'Data-subject request overdue'
                if overdue else 'Data-subject request deadline approaching'
            ),
            message=(
                f'Subject: {subject_request.subject_id}\n'
                f'Right: {subject_request.right_type}\n'
                f'Deadline: {subject_request.response_deadline.isoformat()}\n'
                f'Status: {subject_request.status}\n'
            ),
        ))

    dpo = DPORecord.objects.order_by('-updated_at').first()
    dpo_status = dpo.compliance_status if dpo else 'MISSING'
    if dpo_status in ['MISSING', 'REVIEW_REQUIRED']:
        dpo_reference = dpo.id if dpo else 'none'
        add_result(send_compliance_notification(
            event_type='DPO_STATUS',
            event_key=f'dpo-status:{dpo_reference}:{dpo_status}',
            subject=f'DPO designation status: {dpo_status.replace("_", " ")}',
            message=(
                f'The current DPO designation status is {dpo_status}.\n'
                'Open the DPO Verification page and complete the required controls.\n'
            ),
        ))

    return totals
