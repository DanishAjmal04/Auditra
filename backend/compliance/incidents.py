"""Turns findings into incidents: merging, de-duplication, scoring and the AI anomaly incident."""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from . import scoring
from .ai import ALERT_SCORE
from .detection.context import who
from .models import Incident, IncidentAction, Rule, SEVERITY_RANK

ORG_LEVEL_CODES = {'dpo_missing', 'retention_exceeded', 'dsr_overdue', 'portability_denied', 'breach_not_reported',
                   'subjects_not_notified', 'automated_decision'}
WINDOW_MERGE_MINUTES = 30


def rule_map():
    return {rule.code: rule for rule in Rule.objects.all()}


def _articles(findings, rules):
    """Union of articles, the primary (most severe) finding's articles first."""
    seen = []
    primary = _primary(findings, rules)
    for finding in [primary] + [f for f in findings if f is not primary]:
        for article in finding.articles or rules[finding.code].articles:
            if article not in seen:
                seen.append(article)
    return seen


def _kind(findings, rules):
    kinds = [f.kind or rules[f.code].kind for f in findings]
    if 'VIOLATION' in kinds:
        return 'VIOLATION'
    return kinds[0]


def _primary(findings, rules):
    return max(findings, key=lambda f: SEVERITY_RANK[f.severity or rules[f.code].severity])


def _apply_score(incident, findings, rules, event, ai):
    primary = _primary(findings, rules)
    rule_severity = primary.severity or rules[primary.code].severity
    articles = _articles(findings, rules)
    score, breakdown, level = scoring.build(
        rule_severity, articles,
        primary_event=event,
        shift_reason=any(f.shift_reason for f in findings),
        category_reason=any(f.category_reason for f in findings),
        ai=ai,
        employee=None if primary.code in ORG_LEVEL_CODES else incident.employee,
        account=incident.account,
        kind=incident.kind,
        incident=incident,
    )
    incident.rule = rules[primary.code]
    incident.rule_codes = [f.code for f in findings]
    incident.title = rules[primary.code].title
    incident.reasons = [primary.reason] + [f.reason for f in findings if f is not primary]
    incident.summary = primary.reason
    incident.articles = articles
    incident.rule_severity = rule_severity
    incident.score = score
    incident.score_breakdown = breakdown
    # The displayed level never falls below what the rule itself says.
    incident.severity = scoring.max_severity([level, rule_severity])
    if ai:
        incident.ai_score = ai['score']
        incident.ai_reason = ai['reason'][:400]


def _create(dedupe_key, findings, rules, event, ai, extra_events=()):
    primary = _primary(findings, rules)
    org_level = primary.code in ORG_LEVEL_CODES
    incident = Incident(
        dedupe_key=dedupe_key[:200],
        kind=_kind(findings, rules),
        employee=None if org_level or event is None else event.employee,
        account='' if org_level or event is None else event.account,
        machine='' if event is None else event.machine,
        detected_at=timezone.now(),
    )
    _apply_score(incident, findings, rules, event, ai)
    try:
        with transaction.atomic():
            incident.save()
    except IntegrityError:
        return None
    evidence = [e for e in [event, *extra_events] if e is not None]
    if evidence:
        incident.events.add(*evidence)
    return incident


def _recent_window_incident(code, account):
    since = timezone.now() - timedelta(minutes=WINDOW_MERGE_MINUTES)
    return (
        Incident.objects.filter(rule__code=code, account=account, detected_at__gte=since)
        .exclude(status__in=Incident.CLOSED_STATUSES)
        .order_by('-detected_at')
        .first()
    )


def raise_for_event(event, event_findings, window_findings, ai=None, rules=None):
    """Create or update incidents for one stored event. Returns the incidents that are new."""
    rules = rules or rule_map()
    enabled = lambda f: f.code in rules and rules[f.code].enabled  # noqa: E731
    created = []

    merged = [f for f in event_findings if enabled(f) and not f.dedupe_key]
    if merged:
        incident = _create(f'event:{event.pk}', merged, rules, event, ai)
        if incident:
            created.append(incident)

    for finding in [f for f in event_findings if enabled(f) and f.dedupe_key] + \
                   [f for f in window_findings if enabled(f)]:
        existing = None
        if finding.code not in ORG_LEVEL_CODES:
            existing = _recent_window_incident(finding.code, event.account)
        if existing is None:
            existing = Incident.objects.filter(dedupe_key=finding.dedupe_key[:200]).first()
        if existing:
            existing.events.add(event, *finding.evidence)
            if finding.code not in ORG_LEVEL_CODES:
                previous = existing.score
                _apply_score(existing, [finding], rules, event, ai)
                existing.save()
                if existing.score != previous:
                    IncidentAction.objects.create(
                        incident=existing, action='SCORE_UPDATED',
                        note=f'Score {previous} -> {existing.score}: {finding.reason}',
                    )
            continue
        incident = _create(finding.dedupe_key, [finding], rules, event, ai, extra_events=finding.evidence)
        if incident:
            created.append(incident)
    return created


def raise_workflow(finding, rules=None):
    rules = rules or rule_map()
    if finding.code not in rules or not rules[finding.code].enabled:
        return None
    if Incident.objects.filter(dedupe_key=finding.dedupe_key[:200]).exists():
        return None
    return _create(finding.dedupe_key, [finding], rules, None, None)


def raise_ai_anomaly(employee, account, day, ai, latest_event, rules=None):
    """One ANOMALY incident per employee-day when the AI crosses the line and no rule explains it."""
    rules = rules or rule_map()
    rule = rules.get('ai_anomaly')
    if not rule or not rule.enabled or not ai.get('alert'):
        return None

    key = f'ai:{employee.pk if employee else account}:{day.isoformat()}'
    breakdown = [{'label': f'AI anomaly score for {day:%d %b} ({ai["basis"].replace("_", " ")} baseline)',
                  'points': round(ai['score'])}]
    existing = Incident.objects.filter(dedupe_key=key).first()
    if existing:
        if ai['score'] > (existing.ai_score or 0) + 0.5:
            previous = existing.score
            existing.ai_score = ai['score']
            existing.ai_reason = ai['reason'][:400]
            existing.score = round(ai['score'])
            existing.severity = scoring.level_for(existing.score)
            existing.score_breakdown = breakdown
            existing.summary = _ai_summary(employee, latest_event, ai)
            existing.save()
            existing.events.add(latest_event)
            if existing.score != previous:
                IncidentAction.objects.create(incident=existing, action='SCORE_UPDATED',
                                              note=f'AI score {previous} -> {existing.score}')
        return None

    since = timezone.now() - timedelta(minutes=30)
    explained = Incident.objects.filter(kind='VIOLATION', detected_at__gte=since)
    explained = explained.filter(employee=employee) if employee else explained.filter(account=account)
    if explained.exists():
        return None

    incident = Incident(
        dedupe_key=key,
        kind='ANOMALY',
        rule=rule,
        rule_codes=['ai_anomaly'],
        employee=employee,
        account=account,
        machine=latest_event.machine,
        title=rule.title,
        summary=_ai_summary(employee, latest_event, ai),
        reasons=[c for c in ai['reason'].split('; ')],
        articles=list(rule.articles),
        rule_severity=rule.severity,
        score=round(ai['score']),
        score_breakdown=breakdown,
        severity=scoring.level_for(round(ai['score'])),
        ai_score=ai['score'],
        ai_reason=ai['reason'][:400],
    )
    try:
        with transaction.atomic():
            incident.save()
    except IntegrityError:
        return None
    incident.events.add(latest_event)
    return incident


def _ai_summary(employee, event, ai):
    return (f'{who(event)}: behaviour today is far from normal (AI {ai["score"]:.0f}/100). '
            f'{ai["reason"]}. No rule covers this pattern.')
