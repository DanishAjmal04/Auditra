from django.utils import timezone
from datetime import timedelta

WINDOWS_SYSTEM_RESOURCES = [
    'security_logs', 'system_logs',
    'application_logs', 'powershell_logs',
    'task_scheduler_logs', 'windows_logs'
]

SPECIAL_CATEGORY_RESOURCES = [
    'health_records', 'biometric_data', 'genetic_data',
    'patient_records', 'mental_health_records', 'racial_data',
    'ethnic_data', 'religious_data', 'political_data'
]

CRIMINAL_RESOURCES = [
    'criminal_records', 'offence_data', 'conviction_records'
]

NATIONAL_ID_RESOURCES = [
    'national_id_data', 'cnic_records', 'passport_data',
    'ssn_records', 'identity_documents'
]

EMPLOYEE_RESOURCES = [
    'employee_records', 'hr_records', 'payroll_data',
    'performance_records', 'attendance_data'
]

AUTOMATED_RESOURCES = [
    'automated_decisions', 'credit_scoring', 'risk_profiling',
    'automated_hiring', 'fraud_detection_results'
]

ROLE_SENSITIVITY_MAP = {
    'INTERN': ['LOW'],
    'STAFF': ['LOW', 'MEDIUM'],
    'HR': ['LOW', 'MEDIUM'],
    'ANALYST': ['LOW', 'MEDIUM', 'HIGH'],
    'MANAGER': ['LOW', 'MEDIUM', 'HIGH'],
    'AUDITOR': ['LOW', 'MEDIUM', 'HIGH'],
}

USERS_ROLES = {
    'u_hassan': 'ANALYST',
    'u_ayesha': 'MANAGER',
    'u_tariq': 'INTERN',
    'u_zara': 'ANALYST',
    'u_bilal': 'HR',
    'u_nadia': 'MANAGER',
    'u_omar': 'INTERN',
    'u_sara': 'AUDITOR'
}


def is_windows_system_event(log):
    username = log.user_id.lower().replace('/', '\\').split('\\')[-1]
    if username in (
        '-', 'system', 'local service', 'network service',
        'anonymous logon', 'window manager', 'unknown',
    ):
        return True
    if username.startswith(('dwm-', 'umfd-')):
        return True
    if log.resource_accessed in WINDOWS_SYSTEM_RESOURCES:
        return True
    return False


def get_user_role(user_id):
    if user_id in USERS_ROLES:
        return USERS_ROLES[user_id]
    if '\\' in user_id or '/' in user_id:
        username = user_id.replace('/', '\\').split('\\')[-1].lower()
        if username in ('admin', 'administrator'):
            return 'MANAGER'
        if username in ('system', 'local service', 'network service'):
            return 'AUDITOR'
        # A domain or machine account is not one of the seeded analysts.
        # HIGH resources are outside this role, so Art. 25 can fire.
        return 'STAFF'
    return 'ANALYST'


def get_risk_score(severity):
    """Fixed score for a rule severity. Anomaly rows use the model score instead."""
    scores = {
        'CRITICAL': 0.95,
        'HIGH': 0.75,
        'MEDIUM': 0.50,
        'LOW': 0.25,
    }
    return scores.get(severity, 0.50)


def create_violation(log, rule, reason):
    from .models import Violation
    violation, created = Violation.objects.get_or_create(
        log=log,
        rule=rule,
        defaults={
            'reason': reason,
            'risk_score': get_risk_score(rule.severity),
            'status': 'OPEN',
        },
    )
    if created and rule.severity == 'CRITICAL':
        try:
            from .notifications import notify_critical_violation
            notify_critical_violation(violation)
        except Exception:
            # Notification delivery must never interrupt compliance detection.
            pass
    return violation


def get_rule(gdpr_article):
    from .models import Rule
    try:
        return Rule.objects.get(gdpr_article=gdpr_article, enabled=True)
    except Rule.DoesNotExist:
        return None


def check_all_rules(log):
    violations = []

    # Art. 5 — Bulk export without purpose
    rule = get_rule('Art. 5')
    if rule:
        if (log.action == 'EXPORT' and
                log.resource_sensitivity == 'HIGH' and
                not log.purpose and
                log.resource_accessed not in WINDOWS_SYSTEM_RESOURCES):
            v = create_violation(
                log, rule,
                f"Bulk export of {log.resource_accessed} without declared purpose"
            )
            violations.append(v)

    # Art. 6 — No lawful basis
    rule = get_rule('Art. 6')
    if rule:
        if (log.resource_sensitivity == 'HIGH' and
                not log.purpose and
                log.action in ['READ', 'WRITE', 'EXPORT'] and
                not is_windows_system_event(log)):
            v = create_violation(
                log, rule,
                f"Processing {log.resource_accessed} without a declared lawful basis"
            )
            violations.append(v)

    # Art. 7 — Consent withdrawn
    rule = get_rule('Art. 7')
    if rule:
        from .models import ConsentRecord
        withdrawn = ConsentRecord.objects.filter(
            user_id=log.user_id,
            is_valid=False,
            active_processing=True
        ).first()
        if withdrawn:
            v = create_violation(
                log, rule,
                f"Processing continues for {log.user_id} after consent withdrawn for: {withdrawn.purpose}"
            )
            violations.append(v)

    # Art. 9 — Special category data
    rule = get_rule('Art. 9')
    if rule:
        if (log.resource_accessed in SPECIAL_CATEGORY_RESOURCES and
                not log.purpose):
            v = create_violation(
                log, rule,
                f"Unauthorized access to special category data: {log.resource_accessed}"
            )
            violations.append(v)

    # Art. 10 — Criminal offence data
    rule = get_rule('Art. 10')
    if rule:
        if log.resource_accessed in CRIMINAL_RESOURCES:
            v = create_violation(
                log, rule,
                f"Access to criminal offence data: {log.resource_accessed}"
            )
            violations.append(v)

    # Art. 15-21 — Data subject rights
    # Sirf ek baar check karo, har log pe nahi
    rights_map = {
        'Art. 15': 'ACCESS',
        'Art. 16': 'RECTIFICATION',
        'Art. 17': 'ERASURE',
        'Art. 18': 'RESTRICTION',
        'Art. 20': 'PORTABILITY',
        'Art. 21': 'OBJECTION',
    }
    reasons_map = {
        'Art. 15': 'Subject access request overdue',
        'Art. 16': 'Rectification request overdue',
        'Art. 17': 'Erasure request overdue',
        'Art. 18': 'Restriction request overdue',
        'Art. 20': 'Portability request overdue',
        'Art. 21': 'Objection request overdue',
    }

    # Sirf tab check karo jab log specifically rights se related ho
    if not is_windows_system_event(log):
        from .models import DataSubjectRequest, Violation as ViolationModel
        for article, right_type in rights_map.items():
            rule = get_rule(article)
            if not rule:
                continue
            overdue = DataSubjectRequest.objects.filter(
                subject_id=log.user_id,
                right_type=right_type,
                status__in=['PENDING', 'IN_PROGRESS'],
                response_deadline__lt=timezone.now()
            )
            if overdue.exists():
                # Same log pe same article ki violation pehle se hai toh skip
                already = ViolationModel.objects.filter(
                    log=log,
                    rule__gdpr_article=article
                ).exists()
                if not already:
                    v = create_violation(
                        log, rule,
                        f"{reasons_map[article]} — not fulfilled within 30 days"
                    )
                    violations.append(v)

    # Art. 22 — Automated decision
    rule = get_rule('Art. 22')
    if rule:
        if (log.resource_accessed in AUTOMATED_RESOURCES and
                (not log.purpose or 'human' not in log.purpose.lower())):
            v = create_violation(
                log, rule,
                f"Automated decision on {log.resource_accessed} without human review"
            )
            violations.append(v)

    # Art. 25 — Role based access
    rule = get_rule('Art. 25')
    if rule:
        if not is_windows_system_event(log):
            user_role = get_user_role(log.user_id)
            allowed = ROLE_SENSITIVITY_MAP.get(user_role, ['LOW', 'MEDIUM', 'HIGH'])
            if log.resource_sensitivity not in allowed:
                v = create_violation(
                    log, rule,
                    f"{log.user_id} (role: {user_role}) accessed {log.resource_sensitivity} "
                    f"resource — exceeds role permissions"
                )
                violations.append(v)

    # Art. 29 — Processor beyond scope
    rule = get_rule('Art. 29')
    if rule:
        if (log.action == 'EXPORT' and
                log.resource_sensitivity == 'HIGH' and
                log.purpose and
                'processor' in log.purpose.lower()):
            v = create_violation(
                log, rule,
                f"Processor {log.user_id} acting beyond controller instructions"
            )
            violations.append(v)

    # Art. 30 — Not in RoPA
    rule = get_rule('Art. 30')
    if rule:
        if (log.resource_sensitivity == 'HIGH' and
                not is_windows_system_event(log) and
                log.purpose):
            from .models import ProcessingActivity
            ropa_exists = ProcessingActivity.objects.filter(
                purpose__icontains=log.purpose
            ).exists()
            if not ropa_exists:
                v = create_violation(
                    log, rule,
                    f"Processing activity on {log.resource_accessed} not in Records of Processing"
                )
                violations.append(v)

    # Art. 32 — After hours access
    rule = get_rule('Art. 32')
    if rule:
        if (log.is_outside_hours and
                log.resource_sensitivity == 'HIGH' and
                not is_windows_system_event(log) and
                log.action in ['EXPORT', 'DELETE', 'WRITE']):
            v = create_violation(
                log, rule,
                f"After-hours {log.action} on {log.resource_accessed} by {log.user_id}"
            )
            violations.append(v)

    # Art. 37 — No DPO
    rule = get_rule('Art. 37')
    if rule:
        if (log.resource_sensitivity == 'HIGH' and
                not is_windows_system_event(log)):
            from .models import DPORecord
            has_compliant_dpo = any(
                record.compliance_status == 'COMPLIANT'
                for record in DPORecord.objects.all()
            )
            if not has_compliant_dpo:
                v = create_violation(
                    log, rule,
                    f"High-risk processing on {log.resource_accessed} — no compliant DPO designation"
                )
                violations.append(v)

    # Art. 83 — Repeated violations
    rule = get_rule('Art. 83')
    if rule:
        if not is_windows_system_event(log):
            from .models import Violation as ViolationModel
            week_ago = timezone.now() - timedelta(days=7)
            recent_count = ViolationModel.objects.filter(
                log__user_id=log.user_id,
                detected_at__gte=week_ago
            ).count()
            if recent_count >= 5:
                v = create_violation(
                    log, rule,
                    f"{log.user_id} has {recent_count} violations in last 7 days"
                )
                violations.append(v)

    # Art. 87 — National ID without safeguards
    rule = get_rule('Art. 87')
    if rule:
        if (log.resource_accessed in NATIONAL_ID_RESOURCES and
                not log.purpose):
            v = create_violation(
                log, rule,
                f"National ID data {log.resource_accessed} processed without safeguards"
            )
            violations.append(v)

    # Art. 88 — Employee data without legal basis
    rule = get_rule('Art. 88')
    if rule:
        if (log.resource_accessed in EMPLOYEE_RESOURCES and
                not log.purpose and
                log.action in ['EXPORT', 'DELETE']):
            v = create_violation(
                log, rule,
                f"Employee data {log.resource_accessed} processed without legal basis"
            )
            violations.append(v)

    return violations


def check_overdue_breaches():
    """One open violation per overdue breach, attached to the breach's own log.

    Art. 33 and Art. 34 are organisational deadlines. They must not be copied
    onto every unrelated access event.
    """
    from .models import BreachRecord

    created = []
    now = timezone.now()
    overdue = BreachRecord.objects.filter(
        notification_sent=False,
        notification_deadline__lt=now,
    ).select_related('violation__log')

    rule_33 = get_rule('Art. 33')
    rule_34 = get_rule('Art. 34')

    for breach in overdue:
        source_log = breach.violation.log
        if rule_33:
            created.append(create_violation(
                source_log,
                rule_33,
                f"Data breach {breach.id} not reported to the supervisory authority within 72 hours",
            ))
        if rule_34 and breach.severity in ('HIGH', 'CRITICAL'):
            created.append(create_violation(
                source_log,
                rule_34,
                f"High risk breach {breach.id} — affected data subjects not notified",
            ))
    return created
