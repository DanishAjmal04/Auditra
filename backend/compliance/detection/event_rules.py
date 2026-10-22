"""Rules that look at one event (plus the catalogue, the employee and the GDPR records)."""
from datetime import timedelta

from ..models import SENSITIVITY_RANK, SPECIAL_CATEGORIES, ConsentRecord, DataSubjectRequest
from . import Finding
from .context import (
    DATA_ACCESS_TYPES, PROCESSING_TYPES, allowed_categories, at, max_sensitivity_rank, shift_text, what, who,
)

PRIVILEGED_GROUP_WORDS = ('admin', 'administrators', 'domain admins', 'remote desktop', 'backup operators')


def _entry(event):
    return event.catalogue_entry


def role_scope(event):
    entry = _entry(event)
    if event.event_type not in DATA_ACCESS_TYPES or not entry:
        return None
    emp = event.employee
    too_sensitive = SENSITIVITY_RANK[entry.sensitivity] > max_sensitivity_rank(emp)
    wrong_category = entry.category not in allowed_categories(emp)
    if not (too_sensitive or wrong_category):
        return None
    if emp:
        limits = (f"role {emp.get_role_display()} allows up to {emp.max_sensitivity} data in "
                  f"{', '.join(sorted(allowed_categories(emp)))}")
    else:
        limits = 'the account has no permissions on record'
    return Finding('role_scope', f'{who(event)} {what(event)} ({entry.category}, {entry.sensitivity}); {limits}.',
                   category_reason=True)


def _category_rule(code, categories, label):
    def rule(event):
        entry = _entry(event)
        if event.event_type not in DATA_ACCESS_TYPES or not entry or entry.category not in categories:
            return None
        if entry.category in allowed_categories(event.employee):
            return None
        return Finding(code, f'{who(event)} {what(event)}: {label} without authorisation for this category.',
                       category_reason=True)
    return rule


special_category = _category_rule('special_category', SPECIAL_CATEGORIES, 'special-category (health/biometric) data')
criminal_data = _category_rule('criminal_data', {'CRIMINAL'}, 'criminal offence data')
national_id = _category_rule('national_id', {'NATIONAL_ID'}, 'national ID (CNIC) data')


def employee_data(event):
    entry = _entry(event)
    if event.event_type not in DATA_ACCESS_TYPES or not entry or entry.category != 'HR_EMPLOYEE':
        return None
    emp = event.employee
    if 'HR_EMPLOYEE' in allowed_categories(emp) or (emp and emp.department.strip().lower() in ('hr', 'human resources')):
        return None
    dept = emp.department if emp else 'unknown department'
    return Finding('employee_data', f'{who(event)} from {dept} {what(event)}: employee records outside HR.',
                   category_reason=True)


def no_lawful_basis(event):
    entry = _entry(event)
    if event.event_type not in PROCESSING_TYPES or not entry or not entry.processing_activity:
        return None
    activity = entry.processing_activity
    if activity.legal_basis:
        return None
    return Finding('no_lawful_basis',
                   f'{what(event)} belongs to processing activity "{activity.activity_name}", '
                   f'which has no lawful basis recorded.')


def not_in_ropa(event):
    entry = _entry(event)
    if event.event_type not in DATA_ACCESS_TYPES or not entry or entry.processing_activity_id:
        return None
    if entry.category == 'GENERAL':
        return None
    return Finding('not_in_ropa',
                   f'{what(event)} is {entry.category} data, but no Records of Processing entry covers '
                   f'"{entry.name}".')


def consent_withdrawn(event):
    subject = event.data_subject
    if event.event_type not in PROCESSING_TYPES or not subject:
        return None
    consents = list(ConsentRecord.objects.filter(data_subject=subject, lawful_basis='CONSENT'))
    if not consents or any(c.status == 'GIVEN' for c in consents):
        return None
    withdrawn = max((c.withdrawn_at for c in consents if c.withdrawn_at), default=None)
    if withdrawn and event.occurred_at < withdrawn:
        return None
    when = withdrawn.strftime('%d %b %H:%M') if withdrawn else 'earlier'
    return Finding('consent_withdrawn',
                   f'{who(event)} {what(event)}, the data of {subject.name} ({subject.reference}), who withdrew '
                   f'consent on {when}.')


def _subject_requests(subject, right, statuses):
    return DataSubjectRequest.objects.filter(data_subject=subject, right_type=right, status__in=statuses)


def after_erasure(event):
    subject = event.data_subject
    if event.event_type not in DATA_ACCESS_TYPES - {'FILE_DELETE'} or not subject:
        return None
    done = _subject_requests(subject, 'ERASURE', ['COMPLETED']).filter(completed_at__lte=event.occurred_at).first()
    if not done:
        return None
    return Finding('after_erasure',
                   f'{who(event)} {what(event)}: {subject.name}\'s erasure request was marked completed on '
                   f'{done.completed_at:%d %b %H:%M}, but the data still exists and was accessed.')


def restricted_subject(event):
    subject = event.data_subject
    if event.event_type not in PROCESSING_TYPES or not subject:
        return None
    req = _subject_requests(subject, 'RESTRICTION', ['PENDING', 'IN_PROGRESS', 'COMPLETED']).filter(
        received_at__lte=event.occurred_at).first()
    if not req:
        return None
    return Finding('restricted_subject',
                   f'{who(event)} {what(event)} while {subject.name}\'s restriction request '
                   f'({req.get_status_display().lower()}) is in force.')


def objection_ignored(event):
    subject = event.data_subject
    if event.event_type not in PROCESSING_TYPES or not subject:
        return None
    req = _subject_requests(subject, 'OBJECTION', ['PENDING', 'IN_PROGRESS', 'COMPLETED']).filter(
        received_at__lte=event.occurred_at).first()
    if not req:
        return None
    return Finding('objection_ignored',
                   f'{who(event)} {what(event)} although {subject.name} objected to processing on '
                   f'{req.received_at:%d %b}.')


def after_shift_sensitive(event):
    entry = _entry(event)
    if event.event_type not in DATA_ACCESS_TYPES or not entry or entry.sensitivity != 'HIGH':
        return None
    if not event.outside_shift:
        return None
    return Finding('after_shift_sensitive',
                   f'{who(event)} {what(event)} (HIGH sensitivity) at {at(event)}, outside '
                   f'{shift_text(event.employee)}.', shift_reason=True)


def vendor_scope(event):
    emp = event.employee
    if not emp or emp.employment_type != 'VENDOR':
        return None
    entry = _entry(event)
    problems = []
    if event.event_type in ('FILE_DELETE', 'FILE_COPY_TO_USB'):
        problems.append('vendor exported or deleted data')
    if entry and event.event_type in DATA_ACCESS_TYPES and entry.category not in allowed_categories(emp):
        problems.append(f'{entry.category} is outside the agreed scope')
    if event.outside_shift:
        problems.append(f'active outside agreed hours ({shift_text(emp)})')
    if event.event_type == 'LOGON' and event.logon_type == 10:
        problems.append('remote desktop access')
    if not problems:
        return None
    return Finding('vendor_scope', f'{who(event)} {what(event)}: ' + '; '.join(problems) + '.',
                   shift_reason=event.outside_shift)


def departed_employee(event):
    emp = event.employee
    if not emp or emp.status != 'LEFT':
        return None
    if emp.left_at and event.occurred_at < emp.left_at:
        return None
    left = f' on {emp.left_at:%d %b %Y}' if emp.left_at else ''
    return Finding('departed_employee', f'{who(event)} {what(event)}, but {emp.full_name} left the organisation{left}.')


def usb_connected(event):
    if event.event_type != 'USB_CONNECTED':
        return None
    device = event.device or 'USB storage'
    if event.outside_shift:
        return Finding('usb_after_shift', f'{who(event)} connected {device} at {at(event)}, outside '
                                          f'{shift_text(event.employee)}.', shift_reason=True)
    return Finding('usb_in_shift', f'{who(event)} connected {device} at {at(event)}.', shift_reason=True)


def usb_copy_sensitive(event):
    entry = _entry(event)
    if event.event_type != 'FILE_COPY_TO_USB' or not entry or entry.category == 'GENERAL':
        return None
    articles = ['32', '5(1)(f)']
    special = entry.category in SPECIAL_CATEGORIES
    if special:
        articles.append('9')
    if entry.category == 'NATIONAL_ID':
        articles.append('87')
    if entry.category == 'CRIMINAL':
        articles.append('10')
    severity = 'CRITICAL' if entry.sensitivity == 'HIGH' or special else 'HIGH'
    source = event.details.get('source_path') or entry.name
    return Finding('usb_copy_sensitive',
                   f'{who(event)} copied {event.file_name} ({entry.category}, {entry.sensitivity}) from '
                   f'{source} to removable drive {event.device or ""} at {at(event)}.'.replace('  ', ' '),
                   severity=severity, articles=articles, category_reason=True)


def remote_logon(event):
    if event.event_type != 'LOGON' or event.logon_type != 10:
        return None
    source = event.source_ip or 'an unknown host'
    return Finding('remote_logon', f'{who(event)} logged on through Remote Desktop from {source}.')


def account_created(event):
    if event.event_type != 'ACCOUNT_CREATED':
        return None
    target = event.details.get('target_account', 'a new account')
    return Finding('account_created', f'{who(event)} created the user account {target} on {event.machine}.')


def admin_group_add(event):
    if event.event_type != 'GROUP_MEMBER_ADDED':
        return None
    group = (event.details.get('group') or '').lower()
    if not any(word in group for word in PRIVILEGED_GROUP_WORDS):
        return None
    member = event.details.get('member') or 'an account'
    return Finding('admin_group_add', f'{who(event)} added {member} to the privileged group '
                                      f'"{event.details.get("group")}" on {event.machine}.')


def account_lockout(event):
    if event.event_type != 'ACCOUNT_LOCKED':
        return None
    return Finding('account_lockout', f'Windows locked the account {event.account} on {event.machine} after '
                                      f'repeated failed logons.')


def log_cleared(event):
    if event.event_type != 'LOG_CLEARED':
        return None
    return Finding('log_cleared', f'{who(event)} cleared the Windows Security log on {event.machine} at {at(event)}.')


def audit_policy_changed(event):
    if event.event_type != 'AUDIT_POLICY_CHANGED':
        return None
    change = event.details.get('subcategory') or 'an audit subcategory'
    return Finding('audit_policy_changed', f'{who(event)} changed the audit policy ({change}) on {event.machine}.')


def task_created(event):
    if event.event_type != 'TASK_CREATED':
        return None
    return Finding('task_created', f'{who(event)} created the scheduled task "{event.details.get("task_name", "")}" '
                                   f'on {event.machine}.')


def print_sensitive(event):
    entry = _entry(event)
    if event.event_type != 'PRINT' or not entry or entry.category == 'GENERAL':
        return None
    printer = event.details.get('printer', 'a printer')
    return Finding('print_sensitive', f'{who(event)} printed {event.file_name} ({entry.category}) on {printer}.')


def web_visit(event):
    if event.event_type != 'WEB_VISIT':
        return None
    category = event.details.get('site_category')
    hour_key = event.occurred_at.strftime('%Y%m%d%H')
    if category == 'SOCIAL_MEDIA':
        return Finding('social_media', f'{who(event)} visited {event.domain} during work.',
                       dedupe_key=f'web:{event.account}:{event.domain}:{hour_key}')
    if category != 'FILE_SHARING':
        return None
    from ..models import Event

    recent = (
        Event.objects.filter(
            account=event.account,
            event_type__in=DATA_ACCESS_TYPES,
            catalogue_entry__isnull=False,
            occurred_at__gte=event.occurred_at - timedelta(minutes=30),
            occurred_at__lte=event.occurred_at,
        )
        .exclude(catalogue_entry__category='GENERAL')
        .select_related('catalogue_entry')
        .order_by('-occurred_at')
    )
    recent = list(recent[:20])
    key = f'web:{event.account}:{event.domain}:{hour_key}'
    if not recent:
        return Finding('file_sharing_site', f'{who(event)} visited the file-sharing site {event.domain}.',
                       dedupe_key=key)
    worst = max(recent, key=lambda e: SENSITIVITY_RANK[e.catalogue_entry.sensitivity])
    severity = 'HIGH' if worst.catalogue_entry.sensitivity == 'HIGH' else 'MEDIUM'
    return Finding('file_sharing_site',
                   f'{who(event)} visited the file-sharing site {event.domain} {len(recent)} file event(s) after '
                   f'opening personal data (last: {worst.file_name}, {worst.catalogue_entry.category}). '
                   f'Possible upload of personal data.',
                   kind='VIOLATION', severity=severity, dedupe_key=key, evidence=recent[:5])


def retention_exceeded(event):
    if event.event_type != 'RETENTION_EXCEEDED':
        return None
    entry = _entry(event)
    days = event.details.get('age_days')
    limit = entry.retention_days if entry else event.details.get('retention_days')
    return Finding('retention_exceeded',
                   f'{event.path} is {days} days old; the retention period for "{entry.name if entry else "?"}" '
                   f'is {limit} days.', dedupe_key=f'retention:{event.machine}:{event.path}')


EVENT_RULES = [
    role_scope, special_category, criminal_data, national_id, employee_data, no_lawful_basis, not_in_ropa,
    consent_withdrawn, after_erasure, restricted_subject, objection_ignored, after_shift_sensitive, vendor_scope,
    departed_employee, usb_connected, usb_copy_sensitive, remote_logon, account_created, admin_group_add,
    account_lockout, log_cleared, audit_policy_changed, task_created, print_sensitive, web_visit,
    retention_exceeded,
]


def evaluate(event):
    findings = []
    for rule in EVENT_RULES:
        finding = rule(event)
        if finding:
            findings.append(finding)
    return findings
