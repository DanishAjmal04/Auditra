"""Builds a small organisation and agent payloads shaped exactly like agent.py sends them."""
import itertools
from datetime import datetime, time, timedelta

from django.utils import timezone

from ..models import (
    Agent, CatalogueEntry, DataSubject, DPORecord, Employee, EmployeeAccount, ProcessingActivity,
)

ROOT = r'C:\AuditraCompany'
MACHINE = 'MACBOOK'
_keys = itertools.count(1)


def local(hour, minute=0, days_ago=1):
    """An aware datetime on the most recent weekday at least N days ago, at the given local time."""
    day = timezone.localdate() - timedelta(days=days_ago)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def build_org(dpo_compliant=True):
    payroll = ProcessingActivity.objects.create(activity_name='Payroll', purpose='Pay staff',
                                                legal_basis='CONTRACT')
    hr = ProcessingActivity.objects.create(activity_name='HR administration', purpose='Employment',
                                           legal_basis='LEGAL_OBLIGATION')
    health = ProcessingActivity.objects.create(activity_name='Occupational health', purpose='Health checks',
                                               legal_basis='LEGAL_OBLIGATION')
    customers = ProcessingActivity.objects.create(activity_name='Customer marketing', purpose='Marketing',
                                                  legal_basis='CONSENT')
    unlawful = ProcessingActivity.objects.create(activity_name='Shadow analytics', purpose='Profiling',
                                                 legal_basis='')
    entries = {
        'finance': CatalogueEntry.objects.create(name='Finance', path_prefix=rf'{ROOT}\Finance', category='FINANCIAL',
                                                 sensitivity='MEDIUM', processing_activity=payroll),
        'payroll': CatalogueEntry.objects.create(name='Payroll', path_prefix=rf'{ROOT}\Payroll', category='FINANCIAL',
                                                 sensitivity='HIGH', processing_activity=payroll),
        'hr': CatalogueEntry.objects.create(name='HR records', path_prefix=rf'{ROOT}\HR', category='HR_EMPLOYEE',
                                            sensitivity='HIGH', processing_activity=hr),
        'cnic': CatalogueEntry.objects.create(name='Employee CNIC list', path_prefix=rf'{ROOT}\HR\employees_cnic.csv',
                                              category='NATIONAL_ID', sensitivity='HIGH', processing_activity=hr),
        'medical': CatalogueEntry.objects.create(name='Medical', path_prefix=rf'{ROOT}\Medical', category='HEALTH',
                                                 sensitivity='HIGH', processing_activity=health),
        'legal': CatalogueEntry.objects.create(name='Legal checks', path_prefix=rf'{ROOT}\Legal', category='CRIMINAL',
                                               sensitivity='HIGH', processing_activity=hr),
        'customers': CatalogueEntry.objects.create(name='Customers', path_prefix=rf'{ROOT}\Customers',
                                                   category='CUSTOMER', sensitivity='MEDIUM',
                                                   processing_activity=customers),
        'biometrics': CatalogueEntry.objects.create(name='Biometrics', path_prefix=rf'{ROOT}\Biometrics',
                                                    category='BIOMETRIC', sensitivity='HIGH'),
        'shadow': CatalogueEntry.objects.create(name='Shadow analytics', path_prefix=rf'{ROOT}\Analytics',
                                                category='CUSTOMER', sensitivity='MEDIUM',
                                                processing_activity=unlawful),
        'archive': CatalogueEntry.objects.create(name='Old invoices', path_prefix=rf'{ROOT}\Finance\archive',
                                                 category='FINANCIAL', sensitivity='MEDIUM', retention_days=30,
                                                 processing_activity=payroll),
    }
    bilal = Employee.objects.create(
        full_name='Bilal Ahmed', employee_code='E-1001', department='Finance', role='STAFF',
        shift_start=time(9, 0), shift_end=time(18, 0), work_days=[0, 1, 2, 3, 4], max_sensitivity='MEDIUM',
        allowed_categories=['FINANCIAL', 'CUSTOMER'],
    )
    EmployeeAccount.objects.create(employee=bilal, account=rf'{MACHINE}\bilal')
    sara = Employee.objects.create(
        full_name='Sara Khan', employee_code='E-1002', department='HR', role='HR_OFFICER',
        max_sensitivity='HIGH', allowed_categories=['HR_EMPLOYEE', 'NATIONAL_ID'],
    )
    EmployeeAccount.objects.create(employee=sara, account=rf'{MACHINE}\sara')
    ali = DataSubject.objects.create(name='Ali Khan', reference='C-501',
                                     path_prefix=rf'{ROOT}\Customers\ali_khan_profile.csv')
    if dpo_compliant:
        DPORecord.objects.create(name='Ayesha DPO', contact='dpo@example.com', designated_at=timezone.localdate(),
                                 scope='All processing', independent=True, direct_access_to_management=True,
                                 conflict_free=True, published_contact_details=True)
    return {'entries': entries, 'bilal': bilal, 'sara': sara, 'ali': ali}


def agent(hostname=MACHINE):
    return Agent.objects.create(hostname=hostname, token=Agent.new_token(), is_admin=True)


def ev(event_type, when, account=rf'{MACHINE}\bilal', **fields):
    payload = {
        'type': event_type,
        'occurred_at': when.isoformat(),
        'account': account,
        'machine': fields.pop('machine', MACHINE),
        'key': f'test:{next(_keys)}',
        'source': 'test',
    }
    payload.update(fields)
    return payload


def file_event(event_type, when, relative, account=rf'{MACHINE}\bilal', **fields):
    path = rf'{ROOT}\{relative}'
    return ev(event_type, when, account=account, path=path, file_name=path.split('\\')[-1],
              process=r'C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE', **fields)


def usb_copy(when, relative, account=rf'{MACHINE}\bilal'):
    name = relative.split('\\')[-1]
    return ev('FILE_COPY_TO_USB', when, account=account, path=rf'E:\{name}', file_name=name, device='E: SanDisk',
              details={'source_path': rf'{ROOT}\{relative}', 'size': 2048})
