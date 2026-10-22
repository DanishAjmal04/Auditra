"""Stores clean events sent by the agent and runs detection on them."""
import hashlib
from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from . import ai
from .detection import event_rules, window_rules
from .incidents import raise_ai_anomaly, raise_for_event, rule_map
from .models import CatalogueEntry, DataSubject, EmployeeAccount, Event, normalize_account, normalize_path

EVENT_TYPES = {code for code, _ in Event.TYPE_CHOICES}
MAX_FUTURE = timedelta(minutes=5)


class IngestError(ValueError):
    pass


def _longest_prefix(objects, path):
    path = normalize_path(path)
    if not path:
        return None
    best = None
    for obj in objects:
        prefix = obj.path_prefix
        if prefix and (path == prefix or path.startswith(prefix + '\\')):
            if best is None or len(prefix) > len(best.path_prefix):
                best = obj
    return best


class Resolver:
    """Caches the catalogue, data subjects and account links for one batch."""

    def __init__(self):
        self.catalogue = list(CatalogueEntry.objects.select_related('processing_activity'))
        self.subjects = [s for s in DataSubject.objects.all() if s.path_prefix]
        self.accounts = {a.account: a.employee for a in EmployeeAccount.objects.select_related('employee')}

    def employee(self, account):
        account = normalize_account(account)
        if account in self.accounts:
            return self.accounts[account]
        username = account.split('\\')[-1]
        return self.accounts.get(username)

    def entry(self, path):
        return _longest_prefix(self.catalogue, path)

    def subject(self, path):
        return _longest_prefix(self.subjects, path)


def _clean(value, limit):
    return str(value or '').strip()[:limit]


def canonical_account(account):
    """One spelling per account whatever the source: DOMAIN upper case, user name lower case."""
    account = account.replace('/', '\\')
    if '\\' not in account:
        return account.lower()
    domain, user = account.split('\\', 1)
    return f'{domain.upper()}\\{user.lower()}'


def build_event(raw, agent, resolver):
    event_type = _clean(raw.get('type'), 30).upper()
    if event_type not in EVENT_TYPES:
        raise IngestError(f'unknown event type {event_type!r}')
    occurred = parse_datetime(_clean(raw.get('occurred_at'), 40))
    if occurred is None:
        raise IngestError('occurred_at is missing or not ISO 8601')
    if timezone.is_naive(occurred):
        occurred = timezone.make_aware(occurred)
    if occurred > timezone.now() + MAX_FUTURE:
        raise IngestError('occurred_at is in the future')

    machine = _clean(raw.get('machine') or (agent.hostname if agent else ''), 100)
    account = canonical_account(_clean(raw.get('account'), 150))
    if not account:
        raise IngestError('account is missing')
    details = raw.get('details') if isinstance(raw.get('details'), dict) else {}
    path = _clean(raw.get('path'), 500)
    lookup_path = details.get('source_path') or path
    entry = resolver.entry(lookup_path)
    subject = resolver.subject(lookup_path)
    employee = resolver.employee(account)

    key_source = f"{machine.lower()}|{_clean(raw.get('key'), 200) or ''}"
    if not raw.get('key'):
        key_source += f"|{event_type}|{occurred.isoformat()}|{account.lower()}|{path.lower()}|{raw.get('domain', '')}"
    dedupe_key = hashlib.sha256(key_source.encode('utf-8')).hexdigest()

    if employee:
        outside = not employee.is_on_shift(occurred)
    else:
        local = timezone.localtime(occurred)
        outside = local.weekday() >= 5 or not (8 <= local.hour < 18)

    return Event(
        agent=agent,
        event_type=event_type,
        occurred_at=occurred,
        machine=machine,
        account=account,
        employee=employee,
        path=path,
        file_name=_clean(raw.get('file_name'), 255) or (path.replace('/', '\\').split('\\')[-1] if path else ''),
        process=_clean(raw.get('process'), 255),
        domain=_clean(raw.get('domain'), 255).lower(),
        device=_clean(raw.get('device'), 255),
        source_ip=_clean(raw.get('source_ip'), 60),
        logon_type=raw.get('logon_type') if isinstance(raw.get('logon_type'), int) else None,
        details=details,
        catalogue_entry=entry,
        category=entry.category if entry else '',
        sensitivity=entry.sensitivity if entry else '',
        data_subject=subject,
        outside_shift=outside,
        source=_clean(raw.get('source'), 120),
        source_event_id=raw.get('source_event_id') if isinstance(raw.get('source_event_id'), int) else None,
        dedupe_key=dedupe_key,
    )


def ingest_events(raw_events, agent=None):
    """Store and analyse a batch. Returns counts and the incidents created."""
    resolver = Resolver()
    stored, duplicates, rejected = [], 0, []
    for index, raw in enumerate(raw_events):
        if not isinstance(raw, dict):
            rejected.append({'index': index, 'error': 'not an object'})
            continue
        try:
            event = build_event(raw, agent, resolver)
        except IngestError as exc:
            rejected.append({'index': index, 'error': str(exc)})
            continue
        if Event.objects.filter(dedupe_key=event.dedupe_key).exists():
            duplicates += 1
            continue
        event.save()
        stored.append(event)
    return _analyse(stored, duplicates, rejected)


def _analyse(stored, duplicates=0, rejected=()):
    rules = rule_map()
    ai_results = {}
    latest_for_subject = {}
    for event in sorted(stored, key=lambda e: e.occurred_at):
        day = timezone.localtime(event.occurred_at).date()
        subject = (event.employee_id, event.account if not event.employee_id else '', day)
        latest_for_subject[subject] = event
    for (employee_id, account, day), event in latest_for_subject.items():
        ai_results[(employee_id, account, day)] = ai.score_day(event.employee, account or event.account, day)

    created = []
    for event in sorted(stored, key=lambda e: e.occurred_at):
        day = timezone.localtime(event.occurred_at).date()
        result = ai_results[(event.employee_id, event.account if not event.employee_id else '', day)]
        findings = event_rules.evaluate(event)
        windows = window_rules.evaluate(event)
        if findings or windows:
            created.extend(raise_for_event(event, findings, windows, ai=result, rules=rules))

    for (employee_id, account, day), event in latest_for_subject.items():
        incident = raise_ai_anomaly(event.employee, account or event.account, day,
                                    ai_results[(employee_id, account, day)], event, rules=rules)
        if incident:
            created.append(incident)

    return {
        'stored': len(stored),
        'duplicates': duplicates,
        'rejected': list(rejected),
        'incidents_created': len(created),
        'incidents': created,
    }


def analyse_events(events):
    """Run detection on events that were stored by other code (inventory, decisions API)."""
    return _analyse(list(events))
