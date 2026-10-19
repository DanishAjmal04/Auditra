import random
from datetime import datetime, timedelta
from django.utils import timezone


USERS = [
    'u_hassan', 'u_ayesha', 'u_tariq',
    'u_zara', 'u_bilal', 'u_nadia', 'u_omar', 'u_sara'
]

RESOURCES = {
    'HIGH': [
        'patient_records', 'biometric_data', 'health_records',
        'criminal_records', 'financial_reports', 'payment_data',
        'personal_identifiers', 'genetic_data'
    ],
    'MEDIUM': [
        'employee_records', 'user_profiles', 'customer_data',
        'audit_logs', 'contract_documents', 'hr_records'
    ],
    'LOW': [
        'public_announcements', 'product_catalog',
        'general_reports', 'system_configs'
    ]
}

ACTIONS = ['READ', 'WRITE', 'DELETE', 'EXPORT', 'LOGIN', 'LOGOUT']

PURPOSES = [
    'Research', 'Audit', 'Compliance', 'Update',
    'GDPR Request', 'Reporting', None, None, None
]

IP_POOL = [
    '192.168.1.10', '192.168.1.22', '192.168.1.35',
    '192.168.1.41', '192.168.1.18', '192.168.1.55',
    '192.168.1.62', '192.168.1.77'
]

ROLES = {
    'u_hassan': 'ANALYST',
    'u_ayesha': 'MANAGER',
    'u_tariq': 'INTERN',
    'u_zara': 'ANALYST',
    'u_bilal': 'HR',
    'u_nadia': 'MANAGER',
    'u_omar': 'INTERN',
    'u_sara': 'AUDITOR'
}


def is_outside_hours(dt):
    hour = dt.hour
    return hour < 8 or hour > 18


def generate_single_log():
    from .models import Log

    sensitivity = random.choices(
        ['HIGH', 'MEDIUM', 'LOW'],
        weights=[40, 35, 25]
    )[0]

    resource = random.choice(RESOURCES[sensitivity])
    action = random.choices(
        ACTIONS,
        weights=[30, 20, 15, 20, 10, 5]
    )[0]
    user = random.choice(USERS)
    ip = random.choice(IP_POOL)
    purpose = random.choice(PURPOSES)

    now = timezone.now()
    random_offset = random.randint(0, 7 * 24 * 60)
    timestamp = now - timedelta(minutes=random_offset)

    outside = is_outside_hours(timestamp)

    log = Log.objects.create(
        user_id=user,
        timestamp=timestamp,
        resource_accessed=resource,
        action=action,
        resource_sensitivity=sensitivity,
        ip_address=ip,
        purpose=purpose,
        is_outside_hours=outside
    )

    return log


def generate_bulk_logs(count=100):
    logs = []
    for _ in range(count):
        log = generate_single_log()
        logs.append(log)
    return logs


def generate_scenario_log(scenario='random'):
    from .models import Log

    now = timezone.now()

    scenarios = {
        'bulk_export': {
            'user_id': random.choice(USERS),
            'timestamp': now,
            'resource_accessed': random.choice(RESOURCES['HIGH']),
            'action': 'EXPORT',
            'resource_sensitivity': 'HIGH',
            'ip_address': random.choice(IP_POOL),
            'purpose': None,
            'is_outside_hours': False
        },
        'after_hours': {
            'user_id': random.choice(USERS),
            'timestamp': now.replace(hour=2, minute=30),
            'resource_accessed': random.choice(RESOURCES['HIGH']),
            'action': 'READ',
            'resource_sensitivity': 'HIGH',
            'ip_address': random.choice(IP_POOL),
            'purpose': None,
            'is_outside_hours': True
        },
        'no_purpose': {
            'user_id': random.choice(USERS),
            'timestamp': now,
            'resource_accessed': random.choice(RESOURCES['HIGH']),
            'action': 'READ',
            'resource_sensitivity': 'HIGH',
            'ip_address': random.choice(IP_POOL),
            'purpose': None,
            'is_outside_hours': False
        },
        'sensitive_delete': {
            'user_id': random.choice(USERS),
            'timestamp': now,
            'resource_accessed': random.choice(RESOURCES['HIGH']),
            'action': 'DELETE',
            'resource_sensitivity': 'HIGH',
            'ip_address': random.choice(IP_POOL),
            'purpose': 'Cleanup',
            'is_outside_hours': False
        },
        'random': None
    }

    if scenario == 'random' or scenario not in scenarios:
        return generate_single_log()

    data = scenarios[scenario]
    log = Log.objects.create(**data)
    return log