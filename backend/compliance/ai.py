"""AI anomaly score for one employee-day.

The detector compares today's behaviour with what is normal, feature by feature, and combines the deviations:

    z_f       = (log1p(today_f) - median_f) / scale_f        (only "more than usual" counts, capped at 10)
    deviation = sqrt(sum of z_f squared)
    score     = 100 * (1 - exp(-deviation / 3.274))          (deviation 3 = score 60 = alert line)

"Normal" is learned from data:
  * a new employee is compared with the CERT r4.2 population (1,000 employees, 208,167 training days),
    exported from the trained pipeline into ml/cert_baseline.json;
  * once the employee has MIN_USER_DAYS days of their own history in Auditra, their own median and spread
    are used instead (spread floored at half the population spread), as in the pipeline's "personal" mode.

The score can only rise when a feature rises, so riskier behaviour can never score lower.
"""
import json
import math
from datetime import datetime, time, timedelta
from functools import lru_cache
from pathlib import Path
from statistics import median

from django.utils import timezone

BASELINE_PATH = Path(__file__).resolve().parent / 'ml' / 'cert_baseline.json'
ALERT_SCORE = 60.0
SCALE_K = 3.0 / -math.log(1 - ALERT_SCORE / 100)   # 3.274: deviation 3 -> 60
Z_CLIP = 10.0
EXPLAIN_MIN_Z = 2.0

FEATURE_LABELS = {
    'activity_events': 'total activity',
    'login_events': 'logons',
    'logins_after_hours': 'logons outside shift',
    'logins_weekend': 'weekend logons',
    'distinct_hosts': 'machines used',
    'after_hours_events': 'activity outside shift',
    'exfil_events': 'files copied to USB',
    'removable_media_events': 'USB connections',
}
# Logon count alone is too weak to raise an AI alert (several unlocks a day are normal).
RISK_FEATURES = [f for f in FEATURE_LABELS if f != 'login_events']


@lru_cache(maxsize=1)
def baseline():
    return json.loads(BASELINE_PATH.read_text(encoding='utf-8'))


def day_bounds(day):
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)
    return start, start + timedelta(days=1)


def features_from_events(events, employee=None):
    """The 8 COMMON features of the trained pipeline, computed from Auditra events of one day."""
    counts = {f: 0 for f in FEATURE_LABELS}
    hosts = set()
    for event in events:
        counts['activity_events'] += 1
        local = timezone.localtime(event.occurred_at)
        outside = (not employee.is_on_shift(event.occurred_at)) if employee else not (8 <= local.hour < 18)
        weekend = local.weekday() >= 5
        if outside:
            counts['after_hours_events'] += 1
        if event.event_type in ('LOGON', 'UNLOCK'):
            counts['login_events'] += 1
            hosts.add(event.machine.lower())
            if outside:
                counts['logins_after_hours'] += 1
            if weekend:
                counts['logins_weekend'] += 1
        if event.event_type == 'FILE_COPY_TO_USB':
            counts['exfil_events'] += 1
        if event.event_type == 'USB_CONNECTED':
            counts['removable_media_events'] += 1
    counts['distinct_hosts'] = len(hosts)
    return counts


def _personal_baseline(history_rows):
    """Median and MAD of the employee's own past days, in log1p space."""
    spec = baseline()
    out_median, out_scale = {}, {}
    for f in spec['features']:
        values = [math.log1p(row[f]) for row in history_rows]
        med = median(values)
        mad = median(abs(v - med) for v in values)
        out_median[f] = med
        out_scale[f] = max(1.4826 * mad, 0.5 * spec['global_scale'][f])
    return out_median, out_scale


def score_features(features, history_rows=None):
    spec = baseline()
    history_rows = history_rows or []
    if len(history_rows) >= spec['min_user_days']:
        med, scale = _personal_baseline(history_rows)
        basis = 'personal'
    else:
        med, scale = spec['global_median'], spec['global_scale']
        basis = 'cert_population'

    contributions = []
    for f in spec['features']:
        value = features.get(f, 0)
        z = (math.log1p(value) - med[f]) / scale[f]
        z = max(0.0, min(Z_CLIP, z))
        contributions.append({
            'feature': f,
            'label': FEATURE_LABELS[f],
            'value': value,
            'typical': round(math.expm1(med[f]), 1),
            'z': round(z, 2),
        })

    deviation = math.sqrt(sum(c['z'] ** 2 for c in contributions))
    risk_deviation = math.sqrt(sum(c['z'] ** 2 for c in contributions if c['feature'] in RISK_FEATURES))
    score = round(100 * (1 - math.exp(-deviation / SCALE_K)), 1)
    contributions.sort(key=lambda c: -c['z'])
    reasons = [
        f"{c['label']}: {c['value']:g} (typical {c['typical']:g})"
        for c in contributions[:3] if c['z'] >= EXPLAIN_MIN_Z
    ]
    return {
        'score': score,
        'deviation': round(deviation, 3),
        'risk_deviation': round(risk_deviation, 3),
        'basis': basis,
        'contributions': contributions,
        'reason': '; '.join(reasons) if reasons else 'No single feature stands out',
        'alert': score >= ALERT_SCORE and risk_deviation >= 2.0,
    }


def subject_key_for(employee, account):
    return f'employee:{employee.pk}' if employee else f'account:{account}'


def score_day(employee, account, day):
    """Recompute and store the AI score for one employee (or unlinked account) and local day."""
    from .models import AiDayScore, Event

    start, end = day_bounds(day)
    qs = Event.objects.filter(occurred_at__gte=start, occurred_at__lt=end)
    qs = qs.filter(employee=employee) if employee else qs.filter(account=account, employee__isnull=True)
    events = list(qs.only('event_type', 'occurred_at', 'machine'))
    features = features_from_events(events, employee)

    key = subject_key_for(employee, account)
    history = list(
        AiDayScore.objects.filter(subject_key=key, day__lt=day).order_by('-day').values_list('features', flat=True)[:30]
    )
    result = score_features(features, history)
    AiDayScore.objects.update_or_create(
        subject_key=key,
        day=day,
        defaults={
            'employee': employee,
            'score': result['score'],
            'deviation': result['deviation'],
            'features': features,
            'contributions': result['contributions'],
            'baseline': result['basis'],
            'reason': result['reason'],
        },
    )
    return result
