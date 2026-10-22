from django.test import TestCase
from rest_framework.test import APIClient

from ..ai import ALERT_SCORE, score_features
from ..models import Agent, AuditraUser, Incident
from .helpers import MACHINE, agent, build_org, ev, file_event, local, usb_copy

NORMAL = {'activity_events': 11, 'login_events': 1, 'logins_after_hours': 0, 'logins_weekend': 0,
          'distinct_hosts': 1, 'after_hours_events': 1, 'exfil_events': 3, 'removable_media_events': 0}


class AiScoreTests(TestCase):
    def test_typical_cert_day_is_quiet(self):
        result = score_features(NORMAL)
        self.assertLess(result['score'], 10)
        self.assertFalse(result['alert'])

    def test_score_never_drops_when_a_feature_rises(self):
        for feature in NORMAL:
            previous = score_features(NORMAL)['score']
            for value in (2, 5, 10, 20, 50, 100):
                row = dict(NORMAL, **{feature: NORMAL[feature] + value})
                current = score_features(row)['score']
                self.assertGreaterEqual(current, previous, f'{feature}={row[feature]}')
                previous = current

    def test_after_hours_usb_exfiltration_beats_a_normal_day(self):
        risky = dict(NORMAL, after_hours_events=15, logins_after_hours=1, exfil_events=8, removable_media_events=2)
        result = score_features(risky)
        self.assertGreater(result['score'], score_features(NORMAL)['score'])
        self.assertGreaterEqual(result['score'], ALERT_SCORE)
        self.assertTrue(result['alert'])
        self.assertIn('activity outside shift', result['reason'])

    def test_many_logons_alone_do_not_alert(self):
        result = score_features(dict(NORMAL, login_events=12))
        self.assertFalse(result['alert'])

    def test_personal_baseline_after_five_days(self):
        history = [dict(NORMAL, after_hours_events=20) for _ in range(5)]
        busy_evening = dict(NORMAL, after_hours_events=20)
        self.assertEqual(score_features(busy_evening, history)['basis'], 'personal')
        self.assertLess(score_features(busy_evening, history)['score'],
                        score_features(busy_evening)['score'])


class AiIncidentTests(TestCase):
    def setUp(self):
        build_org()
        self.agent = agent()

    def test_ai_flags_late_bulk_reading_that_no_rule_explains(self):
        from ..ingest import ingest_events
        bilal = r'MACBOOK\bilal'
        # 40 files over 100 minutes after shift: never 20 in 10 minutes, so mass_read stays silent.
        events = []
        for i in range(40):
            minutes = i * 150 // 60
            events.append(file_event('FILE_READ', local(20 + minutes // 60, minutes % 60),
                                     rf'Finance\report_{i}.csv', account=bilal))
        # Finance files are allowed and MEDIUM: no rule fires, the AI does.
        result = ingest_events(events, agent=self.agent)
        incident = Incident.objects.get(kind='ANOMALY')
        self.assertIn(incident, result['incidents'])
        self.assertGreaterEqual(incident.ai_score, ALERT_SCORE)
        self.assertEqual(Incident.objects.exclude(kind='ANOMALY').count(), 0)


class ApiTests(TestCase):
    def setUp(self):
        self.org = build_org()
        self.officer = AuditraUser.objects.create_user('officer', password='Officer@2026', role='compliance_officer')
        self.admin = AuditraUser.objects.create_user('boss', password='Admin@2026', role='admin')
        self.client = APIClient()

    def login(self, user):
        self.client.force_authenticate(user)

    def test_agent_register_heartbeat_and_events(self):
        anon = APIClient()
        bad = anon.post('/api/agent/register/', {'hostname': MACHINE, 'enrolment_key': 'wrong'}, format='json')
        self.assertEqual(bad.status_code, 403)
        ok = anon.post('/api/agent/register/', {'hostname': MACHINE, 'enrolment_key': 'auditra-ingest-dev-key',
                                                'is_admin': True}, format='json')
        self.assertEqual(ok.status_code, 200)
        self.assertIn(r'c:\auditracompany\payroll', ok.data['config']['catalogue_paths'])
        anon.credentials(HTTP_X_AGENT_TOKEN=ok.data['token'])
        self.assertEqual(anon.post('/api/agent/heartbeat/', {'console_user': r'MACBOOK\bilal'},
                                   format='json').status_code, 200)
        sent = anon.post('/api/agent/events/', {'events': [usb_copy(local(19), r'Payroll\salaries_2026.csv'),
                                                           {'type': 'NOPE'}]}, format='json')
        self.assertEqual(sent.status_code, 200)
        self.assertEqual(sent.data['stored'], 1)
        self.assertEqual(len(sent.data['rejected']), 1)
        self.assertEqual(sent.data['incidents'][0]['severity'], 'CRITICAL')
        agent_row = Agent.objects.get(hostname=MACHINE)
        agent_row.revoked = True
        agent_row.save()
        self.assertEqual(anon.post('/api/agent/heartbeat/', {}, format='json').status_code, 401)

    def test_officer_sees_live_feed_and_acts(self):
        a = agent()
        from ..ingest import ingest_events
        ingest_events([ev('USB_CONNECTED', local(20), device='SanDisk')], agent=a)
        self.login(self.officer)
        live = self.client.get('/api/live/')
        self.assertEqual(live.status_code, 200)
        self.assertEqual(len(live.data['incidents']), 1)
        incident_id = live.data['incidents'][0]['id']
        detail = self.client.get(f'/api/incidents/{incident_id}/')
        self.assertEqual(detail.status_code, 200)
        self.assertTrue(detail.data['timeline'])
        refused = self.client.post(f'/api/incidents/{incident_id}/act/', {'action': 'RESOLVE'}, format='json')
        self.assertEqual(refused.status_code, 400)
        done = self.client.post(f'/api/incidents/{incident_id}/act/',
                                {'action': 'FALSE_POSITIVE', 'note': 'IT staff installing drivers'}, format='json')
        self.assertEqual(done.data['status'], 'FALSE_POSITIVE')
        breach = self.client.post(f'/api/incidents/{incident_id}/report-lost-device/', {}, format='json')
        self.assertEqual(breach.status_code, 201)

    def test_officer_cannot_use_admin_endpoints(self):
        self.login(self.officer)
        self.assertEqual(self.client.get('/api/admin/users/').status_code, 403)
        self.assertEqual(self.client.post('/api/admin/reset-monitoring/', {'confirm': 'RESET'},
                                          format='json').status_code, 403)
        self.assertEqual(self.client.get('/api/employees/').status_code, 200)

    def test_admin_links_account_and_events_follow(self):
        a = agent()
        from ..ingest import ingest_events
        ingest_events([file_event('FILE_READ', local(11), r'Finance\x.csv', account=r'MACBOOK\newhire')], agent=a)
        self.login(self.admin)
        unlinked = self.client.get('/api/admin/unlinked-accounts/')
        self.assertEqual(unlinked.data[0]['account'], r'MACBOOK\newhire')
        employee = self.org['bilal']
        linked = self.client.post(f'/api/admin/employees/{employee.id}/accounts/', {'account': r'MACBOOK\newhire'},
                                  format='json')
        self.assertEqual(linked.status_code, 201)
        self.assertEqual(linked.data['events_relinked'], 1)

    def test_pdf_report(self):
        self.login(self.officer)
        response = self.client.get('/api/reports/compliance.pdf?days=7')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
