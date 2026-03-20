from .models import Log, Rule, Violation
from collections import defaultdict

def run_rule_engine():
    logs = Log.objects.all()
    rules = {r.rule_id: r for r in Rule.objects.all()}
    violations_to_create = []
    existing = set(Violation.objects.values_list('log_id', 'rule_id'))

    # For R005 — count daily access per user+resource
    access_counts = defaultdict(int)
    for log in logs:
        key = (log.user_id, log.resource_accessed, log.timestamp.date())
        access_counts[key] += 1

    for log in logs:
        triggered = []

        # R001 — HIGH sensitivity, no declared purpose
        if log.sensitivity == 'HIGH' and not log.declared_purpose.strip():
            triggered.append(('R001', 'HIGH sensitivity access with no declared purpose', 0.6))

        # R002 — HIGH sensitivity outside business hours
        hour = log.timestamp.hour
        if log.sensitivity == 'HIGH' and (hour < 9 or hour >= 18):
            triggered.append(('R002', f'HIGH sensitivity access at {hour}:00 — outside business hours', 0.85))

        # R003 — Intern accessing HIGH sensitivity
        if log.role == 'intern' and log.sensitivity == 'HIGH':
            triggered.append(('R003', f'Intern ({log.user_id}) accessed HIGH sensitivity resource', 0.75))

        # R004 — EXPORT on HIGH sensitivity
        if log.action == 'EXPORT' and log.sensitivity == 'HIGH':
            triggered.append(('R004', f'Unauthorized bulk export of HIGH sensitivity data by {log.user_id}', 0.95))

        # R005 — Excessive access (same resource, same day, same user, >5 times)
        key = (log.user_id, log.resource_accessed, log.timestamp.date())
        if access_counts[key] > 5:
            triggered.append(('R005', f'Accessed {log.resource_accessed} {access_counts[key]} times in one day', 0.55))

        # R006 — DELETE on HIGH sensitivity
        if log.action == 'DELETE' and log.sensitivity == 'HIGH':
            triggered.append(('R006', f'DELETE action on HIGH sensitivity data by {log.user_id}', 0.95))

        for rule_id, explanation, risk_score in triggered:
            if (log.id, rules[rule_id].id) not in existing:
                violations_to_create.append(Violation(
                    log=log,
                    rule=rules[rule_id],
                    risk_score=risk_score,
                    explanation=explanation,
                ))

    Violation.objects.bulk_create(violations_to_create)
    return len(violations_to_create)