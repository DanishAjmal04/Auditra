import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from django.utils import timezone


def extract_features(logs):
    data = []
    for log in logs:
        hour = log.timestamp.hour
        is_outside = 1 if log.is_outside_hours else 0
        sensitivity = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}.get(log.resource_sensitivity, 0)
        action = {'LOGIN': 0, 'LOGOUT': 1, 'READ': 2, 'WRITE': 3, 'DELETE': 4, 'EXPORT': 5}.get(log.action, 0)
        has_purpose = 0 if not log.purpose else 1
        is_special = 1 if log.resource_accessed in SPECIAL_CATEGORY else 0
        is_criminal = 1 if log.resource_accessed in CRIMINAL else 0

        data.append([
            hour,
            is_outside,
            sensitivity,
            action,
            has_purpose,
            is_special,
            is_criminal
        ])

    return np.array(data)


SPECIAL_CATEGORY = [
    'health_records', 'biometric_data', 'genetic_data',
    'patient_records', 'mental_health_records', 'racial_data',
    'ethnic_data', 'religious_data', 'political_data'
]

CRIMINAL = [
    'criminal_records', 'offence_data', 'conviction_records'
]


def run_anomaly_detection():
    from .models import Log, Violation, Rule

    logs = list(Log.objects.all().order_by('-timestamp')[:500])

    if len(logs) < 10:
        return 0

    features = extract_features(logs)

    model = IsolationForest(
        n_estimators=100,
        contamination=0.1,
        random_state=42
    )
    model.fit(features)

    predictions = model.predict(features)
    scores = model.decision_function(features)

    try:
        anomaly_rule = Rule.objects.get(gdpr_article='Art. 5', enabled=True)
    except Rule.DoesNotExist:
        anomaly_rule = None

    anomaly_count = 0

    for i, log in enumerate(logs):
        if predictions[i] == -1:
            raw_score = scores[i]
            normalized = round(1 - (raw_score + 0.5), 2)
            normalized = max(0.0, min(1.0, normalized))

            already_flagged = Violation.objects.filter(
                log=log,
                is_anomaly=True
            ).exists()

            if not already_flagged and anomaly_rule:
                Violation.objects.create(
                    log=log,
                    rule=anomaly_rule,
                    reason=f"AI anomaly detected — unusual access pattern for {log.user_id} on {log.resource_accessed}",
                    risk_score=normalized,
                    is_anomaly=True,
                    status='OPEN'
                )
                anomaly_count += 1

    return anomaly_count


def get_user_anomaly_score(user_id):
    from .models import Log

    logs = list(Log.objects.filter(user_id=user_id).order_by('-timestamp')[:100])

    if len(logs) < 5:
        return None

    features = extract_features(logs)

    model = IsolationForest(
        n_estimators=100,
        contamination=0.1,
        random_state=42
    )
    model.fit(features)

    scores = model.decision_function(features)
    avg_score = float(np.mean(scores))
    normalized = round(1 - (avg_score + 0.5), 2)
    normalized = max(0.0, min(1.0, normalized))

    predictions = model.predict(features)
    anomaly_flags = int(np.sum(predictions == -1))

    return {
        'user_id': user_id,
        'anomaly_score': normalized,
        'anomaly_flags': anomaly_flags,
        'total_logs': len(logs),
        'is_anomalous': normalized > 0.6
    }