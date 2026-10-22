"""Risk score 0-100 for an incident. Every point is stored with its reason, so the console can show how the
number was built."""
from datetime import timedelta

from django.utils import timezone

from .ai import ALERT_SCORE
from .models import SEVERITY_RANK, SPECIAL_CATEGORIES

SEVERITY_BASE = {'CRITICAL': 70, 'HIGH': 55, 'MEDIUM': 35, 'LOW': 15}
EXTRA_ARTICLE_POINTS = 5
EXTRA_ARTICLE_CAP = 10
OUTSIDE_SHIFT_POINTS = 10
SENSITIVE_CATEGORY_POINTS = 10
SENSITIVE_CATEGORIES = SPECIAL_CATEGORIES | {'CRIMINAL', 'NATIONAL_ID'}
AI_MAX_POINTS = 15
REPEAT_POINTS = 10
REPEAT_THRESHOLD = 3
REPEAT_DAYS = 7


def level_for(score):
    if score >= 85:
        return 'CRITICAL'
    if score >= 65:
        return 'HIGH'
    if score >= 40:
        return 'MEDIUM'
    return 'LOW'


def article_label(article):
    return article if article == 'Policy' else f'Art. {article}'


def repeat_count(employee, account, exclude_incident=None):
    from .models import Incident

    since = timezone.now() - timedelta(days=REPEAT_DAYS)
    qs = Incident.objects.filter(kind='VIOLATION', detected_at__gte=since).exclude(status='FALSE_POSITIVE')
    qs = qs.filter(employee=employee) if employee else qs.filter(account=account, employee__isnull=True)
    if exclude_incident is not None and exclude_incident.pk:
        qs = qs.exclude(pk=exclude_incident.pk)
    return qs.count()


def build(rule_severity, articles, primary_event=None, shift_reason=False, category_reason=False,
          ai=None, employee=None, account='', kind='VIOLATION', incident=None):
    breakdown = [{
        'label': f'Rule severity {rule_severity} ({", ".join(article_label(a) for a in articles[:1])})',
        'points': SEVERITY_BASE[rule_severity],
    }]

    extra = max(0, len(articles) - 1)
    if extra:
        breakdown.append({
            'label': f'{extra} more GDPR article(s): {", ".join(article_label(a) for a in articles[1:])}',
            'points': min(EXTRA_ARTICLE_CAP, extra * EXTRA_ARTICLE_POINTS),
        })

    if primary_event is not None and primary_event.outside_shift and not shift_reason:
        breakdown.append({'label': 'Happened outside the employee\'s shift', 'points': OUTSIDE_SHIFT_POINTS})

    category = getattr(primary_event, 'category', '') if primary_event is not None else ''
    if category in SENSITIVE_CATEGORIES and not category_reason:
        breakdown.append({'label': f'{category} data involved', 'points': SENSITIVE_CATEGORY_POINTS})

    if ai and ai.get('score', 0) >= ALERT_SCORE and kind != 'INDICATOR':
        points = round((ai['score'] - ALERT_SCORE) / (100 - ALERT_SCORE) * AI_MAX_POINTS)
        if points:
            breakdown.append({'label': f'AI anomaly {ai["score"]:.0f}/100: {ai["reason"]}', 'points': points})

    if kind == 'VIOLATION' and (employee or account):
        previous = repeat_count(employee, account, exclude_incident=incident)
        if previous + 1 >= REPEAT_THRESHOLD:
            breakdown.append({
                'label': f'Art. 83 escalation: {previous + 1} violations in {REPEAT_DAYS} days',
                'points': REPEAT_POINTS,
            })

    total = min(100, sum(item['points'] for item in breakdown))
    return total, breakdown, level_for(total)


def max_severity(severities):
    return max(severities, key=lambda s: SEVERITY_RANK[s])
