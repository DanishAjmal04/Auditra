import numpy as np
from sklearn.ensemble import IsolationForest
from .models import Log, Violation

def run_anomaly_detection():
    logs = list(Log.objects.all())
    if not logs:
        return 0

    # Build feature matrix
    features = []
    for log in logs:
        hour = log.timestamp.hour
        sensitivity_map = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
        action_map = {'LOGIN': 0, 'READ': 1, 'WRITE': 2, 'EXPORT': 3, 'DELETE': 4}
        role_map = {'admin': 4, 'auditor': 3, 'analyst': 2, 'hr': 1, 'intern': 0}
        is_outside_hours = 1 if (hour < 9 or hour >= 18) else 0

        features.append([
            hour,
            sensitivity_map.get(log.sensitivity, 0),
            action_map.get(log.action, 0),
            role_map.get(log.role, 0),
            is_outside_hours,
        ])

    X = np.array(features)

    model = IsolationForest(
        n_estimators=100,
        contamination=0.08,
        random_state=42
    )
    predictions = model.fit_predict(X)
    scores = model.decision_function(X)

    # Normalize scores to 0.5–1.0 range for anomalies
    updated = 0
    for i, log in enumerate(logs):
        is_anomaly = predictions[i] == -1
        if is_anomaly:
            raw = scores[i]
            normalized = round(0.5 + 0.5 * (1 / (1 + np.exp(raw * 5))), 2)

            # Update existing violations for this log
            violations = Violation.objects.filter(log=log)
            if violations.exists():
                violations.update(is_anomaly=True, risk_score=max(
                    violations.first().risk_score, normalized
                ))
                updated += violations.count()

    return updated