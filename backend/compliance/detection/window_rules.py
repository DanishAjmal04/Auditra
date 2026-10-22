"""Rules that need several events over time. Each returns a Finding with a dedupe key for the window, so a burst
becomes one incident whose evidence grows, not twenty incidents."""
from datetime import timedelta

from django.db.models import Q

from ..models import DPORecord, Event
from . import Finding
from .context import at, who

BRUTE_FORCE_FAILURES = 5
MASS_READ_FILES = 20
MASS_DELETE_FILES = 3
MASS_EXPORT_FILES = 3
MANY_MACHINES = 3
WINDOW = timedelta(minutes=10)


def _username(account):
    return account.split('\\')[-1].lower()


def _window_key(code, account, moment, minutes=30):
    bucket = int(moment.timestamp() // (minutes * 60))
    return f'{code}:{account}:{bucket}'


def brute_force(event):
    if event.event_type not in ('LOGON', 'UNLOCK'):
        return None
    user = _username(event.account)
    failures = list(
        Event.objects.filter(
            event_type='LOGON_FAILED',
            machine__iexact=event.machine,
            occurred_at__gte=event.occurred_at - WINDOW,
            occurred_at__lte=event.occurred_at,
        ).filter(Q(account__iendswith='\\' + user) | Q(account__iexact=user)).order_by('occurred_at')
    )
    if len(failures) < BRUTE_FORCE_FAILURES:
        return None
    return Finding(
        'brute_force',
        f'{len(failures)} failed logons for {user} on {event.machine} between {at(failures[0])} and '
        f'{at(failures[-1])}, then a successful logon at {at(event)}.',
        dedupe_key=_window_key('brute_force', event.account, failures[0].occurred_at),
        evidence=failures,
    )


def _catalogued(qs):
    return qs.filter(catalogue_entry__isnull=False).exclude(catalogue_entry__category='GENERAL')


def mass_read(event):
    if event.event_type != 'FILE_READ' or not event.catalogue_entry or event.catalogue_entry.category == 'GENERAL':
        return None
    reads = _catalogued(Event.objects.filter(
        account=event.account, event_type='FILE_READ',
        occurred_at__gte=event.occurred_at - WINDOW, occurred_at__lte=event.occurred_at,
    ))
    paths = reads.values_list('path', flat=True).distinct()
    count = paths.count()
    if count < MASS_READ_FILES:
        return None
    return Finding(
        'mass_read',
        f'{who(event)} opened {count} different personal-data files in 10 minutes (up to {at(event)}).',
        dedupe_key=_window_key('mass_read', event.account, event.occurred_at),
        evidence=list(reads.order_by('-occurred_at')[:25]),
    )


def mass_delete(event):
    if event.event_type != 'FILE_DELETE' or not event.catalogue_entry or event.catalogue_entry.category == 'GENERAL':
        return None
    deletes = _catalogued(Event.objects.filter(
        account=event.account, event_type='FILE_DELETE',
        occurred_at__gte=event.occurred_at - WINDOW, occurred_at__lte=event.occurred_at,
    )).select_related('catalogue_entry')
    deletes = list(deletes)
    if len({e.path for e in deletes}) < MASS_DELETE_FILES:
        return None
    high = any(e.catalogue_entry.sensitivity == 'HIGH' for e in deletes)
    return Finding(
        'mass_delete',
        f'{who(event)} deleted {len(deletes)} personal-data files in 10 minutes (up to {at(event)}).',
        severity='CRITICAL' if high else 'HIGH',
        dedupe_key=_window_key('mass_delete', event.account, event.occurred_at),
        evidence=deletes[:25],
    )


def usb_mass_export(event):
    if event.event_type != 'FILE_COPY_TO_USB' or not event.catalogue_entry:
        return None
    copies = list(_catalogued(Event.objects.filter(
        account=event.account, event_type='FILE_COPY_TO_USB',
        occurred_at__gte=event.occurred_at - WINDOW, occurred_at__lte=event.occurred_at,
    )))
    if len(copies) < MASS_EXPORT_FILES:
        return None
    return Finding(
        'usb_mass_export',
        f'{who(event)} copied {len(copies)} personal-data files to removable storage in 10 minutes with no '
        f'declared purpose.',
        dedupe_key=_window_key('usb_mass_export', event.account, event.occurred_at),
        evidence=copies,
    )


def many_machines(event):
    if event.event_type not in ('LOGON', 'UNLOCK'):
        return None
    day_start = event.occurred_at - timedelta(hours=24)
    logons = Event.objects.filter(
        account=event.account, event_type__in=['LOGON', 'UNLOCK'],
        occurred_at__gte=day_start, occurred_at__lte=event.occurred_at,
    )
    machines = sorted({m.lower() for m in logons.values_list('machine', flat=True)})
    if len(machines) < MANY_MACHINES:
        return None
    return Finding(
        'many_machines',
        f'{who(event)} logged on to {len(machines)} machines in 24 hours: {", ".join(machines)}.',
        dedupe_key=f'many_machines:{event.account}:{event.occurred_at:%Y%m%d}',
        evidence=list(logons.order_by('-occurred_at')[:10]),
    )


def shared_account(event):
    if event.event_type not in ('LOGON', 'UNLOCK'):
        return None
    other = (
        Event.objects.filter(
            account=event.account, event_type__in=['LOGON', 'UNLOCK'],
            occurred_at__gte=event.occurred_at - timedelta(minutes=15),
            occurred_at__lte=event.occurred_at,
        )
        .exclude(machine__iexact=event.machine)
        .order_by('-occurred_at')
        .first()
    )
    if not other:
        return None
    return Finding(
        'shared_account',
        f'The account {event.account} was used on {other.machine} at {at(other)} and on {event.machine} at '
        f'{at(event)}. Its actions cannot be tied to one person.',
        dedupe_key=_window_key('shared_account', event.account, event.occurred_at, minutes=60),
        evidence=[other],
    )


def dpo_missing(event):
    entry = event.catalogue_entry
    if not entry or entry.sensitivity != 'HIGH':
        return None
    record = DPORecord.objects.first()
    if record and record.compliance_status in ('COMPLIANT', 'NOT_REQUIRED'):
        return None
    status = record.compliance_status if record else 'MISSING'
    return Finding(
        'dpo_missing',
        f'High-risk processing ({entry.category} data in "{entry.name}") observed while the DPO designation is '
        f'{status.replace("_", " ").lower()}.',
        dedupe_key=f'dpo_missing:{event.occurred_at:%Y%m%d}',
    )


WINDOW_RULES = [brute_force, mass_read, mass_delete, usb_mass_export, many_machines, shared_account, dpo_missing]


def evaluate(event):
    findings = []
    for rule in WINDOW_RULES:
        finding = rule(event)
        if finding:
            findings.append(finding)
    return findings
