"""Rules over the GDPR records kept inside Auditra ("R" in the mapping workbook). Run by the scheduler."""
from datetime import timedelta

from django.utils import timezone

from ..models import AutomatedDecision, BreachRecord, DataSubjectRequest
from . import Finding

DECISION_REVIEW_WINDOW = timedelta(hours=1)
OVERDUE_SEVERITY = {
    'ACCESS': 'HIGH', 'RECTIFICATION': 'MEDIUM', 'ERASURE': 'HIGH', 'RESTRICTION': 'MEDIUM', 'OBJECTION': 'HIGH',
}


def overdue_requests(now):
    findings = []
    qs = DataSubjectRequest.objects.filter(
        status__in=DataSubjectRequest.OPEN_STATUSES, response_deadline__lt=now,
    ).exclude(right_type='PORTABILITY').select_related('data_subject')
    for req in qs:
        days = (now - req.response_deadline).days
        findings.append(Finding(
            'dsr_overdue',
            f'{req.get_right_type_display()} request from {req.data_subject.name} ({req.data_subject.reference}) '
            f'received {req.received_at:%d %b %Y} is {days} day(s) past its deadline of '
            f'{req.response_deadline:%d %b %Y}.',
            severity=OVERDUE_SEVERITY.get(req.right_type, 'HIGH'),
            articles=[DataSubjectRequest.RIGHT_ARTICLE[req.right_type]],
            dedupe_key=f'dsr_overdue:{req.pk}',
        ))
    return findings


def portability_denied(now):
    findings = []
    qs = DataSubjectRequest.objects.filter(right_type='PORTABILITY', status='DENIED', exemption_note='')
    for req in qs.select_related('data_subject'):
        findings.append(Finding(
            'portability_denied',
            f'Portability request from {req.data_subject.name} was denied with no documented exemption.',
            dedupe_key=f'portability_denied:{req.pk}',
        ))
    for req in DataSubjectRequest.objects.filter(
        right_type='PORTABILITY', status__in=DataSubjectRequest.OPEN_STATUSES, response_deadline__lt=now,
    ).select_related('data_subject'):
        findings.append(Finding(
            'portability_denied',
            f'Portability request from {req.data_subject.name} is past its deadline of '
            f'{req.response_deadline:%d %b %Y}.',
            dedupe_key=f'portability_overdue:{req.pk}',
        ))
    return findings


def breaches(now):
    findings = []
    for breach in BreachRecord.objects.filter(notification_deadline__lt=now):
        hours = int((now - breach.detected_at).total_seconds() // 3600)
        if not breach.authority_notified_at:
            findings.append(Finding(
                'breach_not_reported',
                f'Breach "{breach.title}" was detected {hours} hours ago and the supervisory authority has not '
                f'been notified (72-hour limit).',
                dedupe_key=f'breach_not_reported:{breach.pk}',
            ))
        if breach.high_risk and not breach.subjects_notified_at:
            findings.append(Finding(
                'subjects_not_notified',
                f'High-risk breach "{breach.title}": affected data subjects have not been notified after '
                f'{hours} hours.',
                dedupe_key=f'subjects_not_notified:{breach.pk}',
            ))
    return findings


def automated_decisions(now):
    findings = []
    qs = AutomatedDecision.objects.filter(
        significant_effect=True, reviewed_at__isnull=True, made_at__lt=now - DECISION_REVIEW_WINDOW,
    )
    for decision in qs:
        findings.append(Finding(
            'automated_decision',
            f'{decision.system} decided "{decision.decision}" for {decision.subject_reference} at '
            f'{timezone.localtime(decision.made_at):%d %b %H:%M} with no human review recorded.',
            dedupe_key=f'automated_decision:{decision.pk}',
        ))
    return findings


def evaluate(now=None):
    now = now or timezone.now()
    return overdue_requests(now) + portability_denied(now) + breaches(now) + automated_decisions(now)
