"""Detection validation: every scene of the demo, replayed as the exact payload the agent sends.

Run:  $env:DB_ENGINE="sqlite"; $env:DB_NAME=":memory:"; python manage.py test compliance
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from ..ingest import ingest_events
from ..models import (
    AutomatedDecision, BreachRecord, ConsentRecord, DataSubjectRequest, DPORecord, Event, Incident,
)
from ..scheduler import run_compliance_cycle
from .helpers import MACHINE, agent, build_org, ev, file_event, local, usb_copy


def codes(incident):
    return set(incident.rule_codes)


class DetectionBase(TestCase):
    def setUp(self):
        self.org = build_org()
        self.agent = agent()

    def send(self, *events):
        return ingest_events(list(events), agent=self.agent)

    def only_incident(self, result):
        self.assertEqual(len(result['incidents']), 1, [i.title for i in result['incidents']])
        return result['incidents'][0]


class BaselineTests(DetectionBase):
    def test_normal_work_raises_nothing(self):
        result = self.send(
            ev('LOGON', local(9, 2), logon_type=2),
            file_event('FILE_READ', local(9, 15), r'Finance\invoices_2026.csv'),
            file_event('FILE_WRITE', local(9, 20), r'Finance\invoices_2026.csv'),
            file_event('FILE_READ', local(11, 0), r'Customers\fatima_noor_profile.csv'),
            ev('LOCK', local(13, 0)),
            ev('UNLOCK', local(13, 40), logon_type=7),
        )
        self.assertEqual(result['stored'], 6)
        self.assertEqual(Incident.objects.count(), 0)

    def test_duplicate_payload_is_stored_once(self):
        payload = file_event('FILE_READ', local(10), r'Finance\budget_q4.csv')
        self.send(payload)
        result = self.send(payload)
        self.assertEqual(result['duplicates'], 1)
        self.assertEqual(Event.objects.count(), 1)

    def test_timestamp_keeps_local_offset(self):
        moment = local(18, 42)
        self.send(ev('USB_CONNECTED', moment, device='Silicon-Power USB'))
        stored = Event.objects.get()
        self.assertEqual(stored.occurred_at, moment)
        self.assertEqual(timezone.localtime(stored.occurred_at).hour, 18)


class UsbTests(DetectionBase):
    def test_usb_in_shift_is_only_an_indicator(self):
        incident = self.only_incident(self.send(ev('USB_CONNECTED', local(11), device='SanDisk Cruzer')))
        self.assertEqual(incident.kind, 'INDICATOR')
        self.assertEqual(incident.severity, 'LOW')

    def test_usb_after_shift_is_high(self):
        incident = self.only_incident(self.send(ev('USB_CONNECTED', local(19, 30), device='SanDisk Cruzer')))
        self.assertEqual(codes(incident), {'usb_after_shift'})
        self.assertEqual(incident.kind, 'VIOLATION')
        self.assertEqual(incident.rule_severity, 'HIGH')

    def test_cnic_copy_to_usb_after_shift_is_critical(self):
        incident = self.only_incident(self.send(usb_copy(local(19, 5), r'HR\employees_cnic.csv')))
        self.assertIn('usb_copy_sensitive', codes(incident))
        self.assertIn('87', incident.articles)
        self.assertIn('5(1)(f)', incident.articles)
        self.assertEqual(incident.rule_severity, 'CRITICAL')
        self.assertEqual(incident.severity, 'CRITICAL')
        labels = ' '.join(item['label'] for item in incident.score_breakdown)
        self.assertIn('Rule severity CRITICAL', labels)
        self.assertEqual(incident.score, min(100, sum(i['points'] for i in incident.score_breakdown)))

    def test_special_category_copy_adds_art_9(self):
        incident = self.only_incident(self.send(usb_copy(local(11), r'Medical\patient_records.csv')))
        self.assertIn('9', incident.articles)
        self.assertEqual(incident.rule_severity, 'CRITICAL')

    def test_three_copies_raise_bulk_export(self):
        self.send(*[usb_copy(local(11, i), rf'Payroll\salaries_{i}.csv') for i in range(3)])
        bulk = Incident.objects.filter(rule__code='usb_mass_export')
        self.assertEqual(bulk.count(), 1)
        self.assertEqual(bulk.get().events.count(), 3)


class CatalogueRuleTests(DetectionBase):
    def test_salary_file_is_beyond_role(self):
        incident = self.only_incident(self.send(file_event('FILE_READ', local(11), r'Payroll\salaries_2026.csv')))
        self.assertIn('role_scope', codes(incident))
        self.assertIn('25', incident.articles)

    def test_medical_file_is_special_category(self):
        incident = self.only_incident(self.send(file_event('FILE_READ', local(11), r'Medical\patient_records.csv')))
        self.assertIn('special_category', codes(incident))
        self.assertEqual(incident.rule_severity, 'CRITICAL')

    def test_criminal_and_biometric_and_cnic(self):
        legal = self.only_incident(self.send(file_event('FILE_READ', local(11), r'Legal\criminal_record_checks.csv')))
        self.assertIn('criminal_data', codes(legal))
        bio = self.only_incident(self.send(file_event('FILE_READ', local(11, 5), r'Biometrics\fingerprints.csv')))
        self.assertIn('special_category', codes(bio))
        self.assertIn('not_in_ropa', codes(bio))
        cnic = self.only_incident(self.send(file_event('FILE_READ', local(11, 10), r'HR\employees_cnic.csv')))
        self.assertTrue({'national_id', 'role_scope'} <= codes(cnic))
        hr = self.only_incident(self.send(file_event('FILE_READ', local(11, 15), r'HR\performance_reviews.csv')))
        self.assertIn('employee_data', codes(hr))

    def test_hr_officer_may_open_hr_files(self):
        self.send(file_event('FILE_READ', local(11), r'HR\employees_cnic.csv', account=rf'{MACHINE}\sara'))
        self.assertEqual(Incident.objects.count(), 0)

    def test_after_shift_access_to_high_data(self):
        result = self.send(file_event('FILE_READ', local(20), r'HR\performance_reviews.csv',
                                      account=rf'{MACHINE}\sara'))
        incident = self.only_incident(result)
        self.assertEqual(codes(incident), {'after_shift_sensitive'})

    def test_processing_without_lawful_basis(self):
        incident = self.only_incident(self.send(file_event('FILE_READ', local(11), r'Analytics\segments.csv')))
        self.assertIn('no_lawful_basis', codes(incident))

    def test_unlinked_account_has_no_permissions(self):
        incident = self.only_incident(self.send(
            file_event('FILE_READ', local(11), r'Payroll\salaries_2026.csv', account=rf'{MACHINE}\guest')))
        self.assertIn('role_scope', codes(incident))
        self.assertIsNone(incident.employee)


class DataSubjectRuleTests(DetectionBase):
    def test_access_after_consent_withdrawn(self):
        ConsentRecord.objects.create(data_subject=self.org['ali'], purpose='Marketing', status='WITHDRAWN',
                                     given_at=local(9, days_ago=20), withdrawn_at=local(9, days_ago=3))
        incident = self.only_incident(self.send(file_event('FILE_READ', local(11),
                                                           r'Customers\ali_khan_profile.csv')))
        self.assertEqual(codes(incident), {'consent_withdrawn'})
        self.assertEqual(incident.rule_severity, 'CRITICAL')

    def test_access_with_valid_consent_is_clean(self):
        ConsentRecord.objects.create(data_subject=self.org['ali'], purpose='Marketing', status='GIVEN')
        self.send(file_event('FILE_READ', local(11), r'Customers\ali_khan_profile.csv'))
        self.assertEqual(Incident.objects.count(), 0)

    def test_erasure_restriction_objection(self):
        DataSubjectRequest.objects.create(data_subject=self.org['ali'], right_type='ERASURE', status='COMPLETED',
                                          received_at=local(9, days_ago=10), completed_at=local(9, days_ago=5))
        DataSubjectRequest.objects.create(data_subject=self.org['ali'], right_type='RESTRICTION',
                                          received_at=local(9, days_ago=4))
        DataSubjectRequest.objects.create(data_subject=self.org['ali'], right_type='OBJECTION',
                                          received_at=local(9, days_ago=4))
        incident = self.only_incident(self.send(file_event('FILE_READ', local(11),
                                                           r'Customers\ali_khan_profile.csv')))
        self.assertTrue({'after_erasure', 'restricted_subject', 'objection_ignored'} <= codes(incident))
        self.assertTrue({'17', '18', '21'} <= set(incident.articles))


class WindowRuleTests(DetectionBase):
    def test_brute_force_then_success(self):
        failures = [ev('LOGON_FAILED', local(10, i), account=rf'{MACHINE}\bilal', logon_type=2) for i in range(5)]
        self.send(*failures, ev('UNLOCK', local(10, 6), logon_type=7))
        incident = Incident.objects.get(rule__code='brute_force')
        self.assertEqual(incident.events.count(), 6)

    def test_four_failures_are_not_brute_force(self):
        failures = [ev('LOGON_FAILED', local(10, i), logon_type=2) for i in range(4)]
        self.send(*failures, ev('UNLOCK', local(10, 6), logon_type=7))
        self.assertFalse(Incident.objects.filter(rule__code='brute_force').exists())

    def test_mass_delete(self):
        self.send(*[file_event('FILE_DELETE', local(11, i), rf'Customers\c_{i}.csv') for i in range(3)])
        incident = Incident.objects.get(rule__code='mass_delete')
        self.assertEqual(incident.rule_severity, 'HIGH')

    def test_mass_read_in_allowed_folder(self):
        self.send(*[file_event('FILE_READ', local(11, i // 3), rf'Customers\c_{i}.csv') for i in range(20)])
        self.assertEqual(Incident.objects.filter(rule__code='mass_read').count(), 1)

    def test_shared_account_and_many_machines(self):
        self.send(ev('LOGON', local(10, 0), logon_type=2, machine='PC-1'),
                  ev('LOGON', local(10, 5), logon_type=2, machine='PC-2'),
                  ev('LOGON', local(10, 9), logon_type=2, machine='PC-3'))
        self.assertTrue(Incident.objects.filter(rule__code='shared_account').exists())
        self.assertTrue(Incident.objects.filter(rule__code='many_machines').exists())


class AccountAndSystemTests(DetectionBase):
    def test_security_events(self):
        self.send(
            ev('ACCOUNT_CREATED', local(11), details={'target_account': rf'{MACHINE}\tempuser'}),
            ev('GROUP_MEMBER_ADDED', local(11, 1), details={'group': 'Administrators', 'member': 'tempuser'}),
            ev('GROUP_MEMBER_ADDED', local(11, 2), details={'group': 'Users', 'member': 'tempuser'}),
            ev('ACCOUNT_LOCKED', local(11, 3)),
            ev('LOG_CLEARED', local(11, 4)),
            ev('AUDIT_POLICY_CHANGED', local(11, 5), details={'subcategory': 'File System'}),
            ev('TASK_CREATED', local(11, 6), details={'task_name': r'\Updater'}),
        )
        found = set(Incident.objects.values_list('rule__code', flat=True))
        self.assertEqual(found, {'account_created', 'admin_group_add', 'account_lockout', 'log_cleared',
                                 'audit_policy_changed', 'task_created'})
        self.assertEqual(Incident.objects.get(rule__code='log_cleared').rule_severity, 'CRITICAL')

    def test_departed_employee_and_vendor(self):
        bilal = self.org['bilal']
        bilal.status, bilal.left_at = 'LEFT', local(9, days_ago=5)
        bilal.save()
        incident = self.only_incident(self.send(ev('LOGON', local(10), logon_type=2)))
        self.assertIn('departed_employee', codes(incident))

    def test_vendor_remote_access(self):
        bilal = self.org['bilal']
        bilal.employment_type = 'VENDOR'
        bilal.save()
        incident = self.only_incident(self.send(ev('LOGON', local(11), logon_type=10, source_ip='10.0.0.9')))
        self.assertTrue({'remote_logon', 'vendor_scope'} <= codes(incident))
        self.assertIn('29', incident.articles)

    def test_print_and_web(self):
        self.send(file_event('PRINT', local(11), r'Customers\fatima_noor_profile.csv',
                             details={'printer': 'Microsoft Print to PDF'}))
        self.assertTrue(Incident.objects.filter(rule__code='print_sensitive', kind='INDICATOR').exists())
        self.send(ev('WEB_VISIT', local(12), domain='facebook.com', details={'site_category': 'SOCIAL_MEDIA'}))
        self.assertTrue(Incident.objects.filter(rule__code='social_media', kind='INDICATOR').exists())

    def test_file_sharing_after_personal_data_is_a_violation(self):
        self.send(file_event('FILE_READ', local(14, 0), r'Customers\fatima_noor_profile.csv'))
        self.send(ev('WEB_VISIT', local(14, 10), domain='wetransfer.com', details={'site_category': 'FILE_SHARING'}))
        incident = Incident.objects.get(rule__code='file_sharing_site')
        self.assertEqual(incident.kind, 'VIOLATION')
        self.assertEqual(incident.events.count(), 2)

    def test_disabled_rule_is_silent(self):
        from ..models import Rule
        Rule.objects.filter(code='usb_after_shift').update(enabled=False)
        self.send(ev('USB_CONNECTED', local(20), device='SanDisk'))
        self.assertEqual(Incident.objects.count(), 0)


class WorkflowRuleTests(DetectionBase):
    def test_workflow_cycle(self):
        now = timezone.now()
        ali = self.org['ali']
        DataSubjectRequest.objects.create(data_subject=ali, right_type='ACCESS', received_at=now - timedelta(days=40))
        DataSubjectRequest.objects.create(data_subject=ali, right_type='PORTABILITY', status='DENIED')
        BreachRecord.objects.create(title='Lost laptop', detected_at=now - timedelta(hours=80), high_risk=True)
        AutomatedDecision.objects.create(system='LoanEngine', subject_reference='C-501', decision='Loan rejected',
                                         made_at=now - timedelta(hours=2))
        job = run_compliance_cycle(trigger='MANUAL')
        self.assertEqual(job.status, 'SUCCESS')
        found = set(Incident.objects.values_list('rule__code', flat=True))
        self.assertEqual(found, {'dsr_overdue', 'portability_denied', 'breach_not_reported',
                                 'subjects_not_notified', 'automated_decision'})
        self.assertIn('15', Incident.objects.get(rule__code='dsr_overdue').articles)
        run_compliance_cycle(trigger='MANUAL')
        self.assertEqual(Incident.objects.count(), 5)

    def test_dpo_missing_on_high_risk_processing(self):
        DPORecord.objects.all().delete()
        self.send(file_event('FILE_READ', local(11), r'HR\performance_reviews.csv', account=rf'{MACHINE}\sara'))
        incident = Incident.objects.get(rule__code='dpo_missing')
        self.assertIsNone(incident.employee)

    def test_retention_through_inventory(self):
        from rest_framework.test import APIClient
        client = APIClient()
        client.credentials(HTTP_X_AGENT_TOKEN=self.agent.token)
        old = (timezone.now() - timedelta(days=90)).isoformat()
        response = client.post('/api/agent/inventory/', {'files': [
            {'path': r'C:\AuditraCompany\Finance\archive\inv_2019.csv', 'size': 100, 'modified_at': old},
            {'path': r'C:\AuditraCompany\Finance\invoices_2026.csv', 'size': 100, 'modified_at': old},
        ]}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.data['over_retention'], 1)
        self.assertTrue(Incident.objects.filter(rule__code='retention_exceeded').exists())


class ScoreTests(DetectionBase):
    def test_repeat_offender_gets_art_83_points(self):
        for minute in range(3):
            self.send(file_event('FILE_READ', local(11, minute * 20), rf'Payroll\salaries_{minute}.csv'))
        latest = Incident.objects.filter(rule__code='role_scope').order_by('-number').first()
        labels = [item['label'] for item in latest.score_breakdown]
        self.assertTrue(any('Art. 83' in label for label in labels), labels)

    def test_false_positive_does_not_count_for_art_83(self):
        for minute in range(2):
            self.send(file_event('FILE_READ', local(11, minute * 20), rf'Payroll\s_{minute}.csv'))
        Incident.objects.update(status='FALSE_POSITIVE')
        self.send(file_event('FILE_READ', local(12), r'Payroll\s_9.csv'))
        latest = Incident.objects.order_by('-number').first()
        self.assertFalse(any('Art. 83' in i['label'] for i in latest.score_breakdown))
