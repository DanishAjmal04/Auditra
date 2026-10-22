from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from django.db.models import Q
from django.utils import timezone

from .ml.auditra_features import common_features_from_events
from .ml.scorer import AnomalyScorer

ARTIFACT_DIR = Path(__file__).resolve().parent / 'ml' / 'artifacts' / 'anomaly_v1'
MIN_LOGS_FOR_BATCH = 10
MIN_LOGS_FOR_USER = 5
_SCORER = None


def get_scorer():
    global _SCORER
    if _SCORER is None:
        _SCORER = AnomalyScorer.load(ARTIFACT_DIR)
    return _SCORER


def _events_frame(logs):
    return pd.DataFrame({
        'user_id': [log.user_id for log in logs],
        'timestamp': [log.timestamp for log in logs],
        'action': [log.action for log in logs],
        'resource_accessed': [log.resource_accessed for log in logs],
        'ip_address': [log.ip_address for log in logs],
    })


def _day_bounds(day_str):
    start = timezone.make_aware(datetime.strptime(day_str, '%Y-%m-%d'))
    return start, start + timedelta(days=1)


def _representative_log(user_id, day_str):
    from .models import Log

    start, end = _day_bounds(day_str)
    qs = Log.objects.filter(
        user_id=user_id,
        timestamp__gte=start,
        timestamp__lt=end,
    )
    preferred = qs.filter(
        Q(action='EXPORT') | Q(resource_accessed='removable_media')
    ).order_by('timestamp').first()
    return preferred or qs.order_by('timestamp').first()


def _score_logs(logs):
    if not logs:
        return None
    frame = common_features_from_events(_events_frame(logs))
    if frame.empty:
        return None
    return get_scorer().score_frame(frame, explain=True)


def run_anomaly_detection():
    from .models import Log, Rule, Violation

    logs = list(Log.objects.order_by('-timestamp')[:5000])
    if len(logs) < MIN_LOGS_FOR_BATCH:
        return 0

    scored = _score_logs(logs)
    if scored is None:
        return 0

    rule = Rule.objects.filter(gdpr_article='ML-ANOMALY', enabled=True).first()
    if rule is None:
        return 0

    created_count = 0
    unusual = scored[scored['is_unusual']]
    for row in unusual.itertuples(index=False):
        log = _representative_log(row.user, row.day)
        if log is None:
            continue
        pct = float(row.anomaly_pct)
        reason = (
            f'Unusual activity on {row.day} ({pct:.0f}/100). {row.reason}'
        )
        _, created = Violation.objects.get_or_create(
            log=log,
            rule=rule,
            defaults={
                'reason': reason,
                'risk_score': round(pct / 100.0, 4),
                'is_anomaly': True,
                'status': 'OPEN',
            },
        )
        if created:
            created_count += 1
    return created_count


def get_user_anomaly_score(user_id):
    from .models import Log

    logs = list(
        Log.objects.filter(user_id=user_id).order_by('-timestamp')[:2000]
    )
    if len(logs) < MIN_LOGS_FOR_USER:
        return None

    scored = _score_logs(logs)
    if scored is None or scored.empty:
        return None

    scored = scored.sort_values('day')
    unusual = scored[scored['is_unusual']]
    focus = unusual.sort_values('anomaly_pct').iloc[-1] if len(unusual) else scored.iloc[-1]
    unusual_days = int(len(unusual))
    pct = float(focus['anomaly_pct'])
    return {
        'user_id': user_id,
        'anomaly_score': round(pct / 100.0, 4),
        'anomaly_pct': round(pct, 1),
        'anomaly_flags': unusual_days,
        'total_logs': len(logs),
        'is_anomalous': unusual_days > 0,
        'reason': str(focus['reason']),
        'day': str(focus['day']),
    }
