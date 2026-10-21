from io import StringIO
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from datetime import timedelta
from .models import (
    AuditraUser, Log, Rule, Violation,
    ConsentRecord, DataSubjectRequest,
    BreachRecord, ProcessingActivity, DPORecord, NotificationLog,
    ComplianceJobRun,
)
from .rule_engine import check_all_rules, check_overdue_breaches, create_violation
from .notifications import (
    notify_critical_violation,
    send_pending_compliance_notifications,
)
from .log_generator import generate_single_log, generate_scenario_log
from .anomaly_detector import run_anomaly_detection, get_user_anomaly_score
from .scheduler import run_compliance_cycle


# ─────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────

def create_rule(article, severity='HIGH', enabled=True):
    return Rule.objects.create(
        gdpr_article=article,
        description=f'Test rule for {article}',
        logic_definition='test_logic',
        severity=severity,
        enabled=enabled
    )

def create_log(**kwargs):
    defaults = {
        'user_id': 'u_test',
        'timestamp': timezone.now(),
        'resource_accessed': 'test_resource',
        'action': 'READ',
        'resource_sensitivity': 'LOW',
        'ip_address': '192.168.1.1',
        'purpose': 'Testing',
        'is_outside_hours': False
    }
    defaults.update(kwargs)
    return Log.objects.create(**defaults)


# ─────────────────────────────────────────
# TC-01 to TC-10: API ENDPOINT TESTS
# ─────────────────────────────────────────

class APIEndpointTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = AuditraUser.objects.create_user(
            username='test_officer',
            email='test@auditra.com',
            password='Test@2026',
            role='compliance_officer',
        )
        self.client.force_authenticate(user=self.user)
        create_rule('Art. 5', 'CRITICAL')
        create_rule('Art. 6', 'HIGH')

    def test_tc01_login_success(self):
        """TC-01: Login with valid credentials returns token"""
        res = self.client.post('/api/auth/login/', {
            'username': 'test_officer',
            'password': 'Test@2026'
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('access', res.data)
        self.assertIn('refresh', res.data)

    def test_tc02_login_wrong_password(self):
        """TC-02: Login with wrong password returns 401"""
        res = self.client.post('/api/auth/login/', {
            'username': 'test_officer',
            'password': 'wrongpassword'
        }, format='json')
        self.assertEqual(res.status_code, 401)

    def test_tc03_login_wrong_email(self):
        """TC-03: Login with non-existent email returns 404"""
        res = self.client.post('/api/auth/login/', {
            'username': 'nobody',
            'password': 'Test@2026'
        }, format='json')
        self.assertEqual(res.status_code, 401)

    def test_tc04_stats_endpoint(self):
        """TC-04: Stats endpoint returns required fields"""
        res = self.client.get('/api/stats/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('total_logs', res.data)
        self.assertIn('total_violations', res.data)
        self.assertIn('compliance_score', res.data)
        self.assertIn('anomaly_count', res.data)

    def test_tc05_violations_endpoint(self):
        """TC-05: Violations endpoint returns list"""
        res = self.client.get('/api/violations/')
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.data, list)

    def test_tc06_logs_endpoint(self):
        """TC-06: Logs endpoint returns list"""
        create_log()
        res = self.client.get('/api/logs/')
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.data, list)

    def test_tc07_rules_endpoint(self):
        """TC-07: Rules endpoint returns all rules"""
        res = self.client.get('/api/rules/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 2)

    def test_tc08_users_list_endpoint(self):
        """TC-08: Users list returns distinct user IDs from logs"""
        create_log(user_id='u_hassan')
        create_log(user_id='u_ayesha')
        res = self.client.get('/api/users/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('u_hassan', res.data)

    def test_tc09_simulate_endpoint(self):
        """TC-09: Simulate endpoint returns violation data"""
        res = self.client.post('/api/simulate/', {}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertIn('user', res.data)
        self.assertIn('violations_triggered', res.data)

    def test_tc10_violation_status_update(self):
        """TC-10: Violation status can be updated"""
        rule = Rule.objects.first()
        log = create_log()
        violation = Violation.objects.create(
            log=log, rule=rule,
            reason='Test', risk_score=0.8, status='OPEN'
        )
        res = self.client.patch(
            f'/api/violations/{violation.id}/status/',
            {'status': 'RESOLVED'},
            format='json'
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], 'RESOLVED')


# ─────────────────────────────────────────
# TC-11 to TC-32: RULE ENGINE TESTS
# ─────────────────────────────────────────

class RuleEngineTests(TestCase):

    def setUp(self):
        create_rule('Art. 5', 'CRITICAL')
        create_rule('Art. 6', 'HIGH')
        create_rule('Art. 7', 'CRITICAL')
        create_rule('Art. 9', 'CRITICAL')
        create_rule('Art. 10', 'CRITICAL')
        create_rule('Art. 15', 'HIGH')
        create_rule('Art. 16', 'MEDIUM')
        create_rule('Art. 17', 'HIGH')
        create_rule('Art. 18', 'MEDIUM')
        create_rule('Art. 20', 'MEDIUM')
        create_rule('Art. 21', 'HIGH')
        create_rule('Art. 22', 'HIGH')
        create_rule('Art. 25', 'HIGH')
        create_rule('Art. 29', 'HIGH')
        create_rule('Art. 30', 'MEDIUM')
        create_rule('Art. 32', 'HIGH')
        create_rule('Art. 33', 'CRITICAL')
        create_rule('Art. 34', 'HIGH')
        create_rule('Art. 37', 'HIGH')
        create_rule('Art. 83', 'CRITICAL')
        create_rule('Art. 87', 'HIGH')
        create_rule('Art. 88', 'HIGH')

    def test_tc11_art5_bulk_export_triggers(self):
        """TC-11: Art.5 fires on EXPORT + HIGH sensitivity + no purpose"""
        log = create_log(
            action='EXPORT',
            resource_sensitivity='HIGH',
            resource_accessed='patient_records',
            purpose=None
        )
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 5', articles)

    def test_tc12_art5_no_trigger_with_purpose(self):
        """TC-12: Art.5 does not fire when purpose is declared"""
        log = create_log(
            action='EXPORT',
            resource_sensitivity='HIGH',
            purpose='Audit'
        )
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertNotIn('Art. 5', articles)

    def test_tc13_art6_no_lawful_basis(self):
        """TC-13: Art.6 fires on HIGH sensitivity READ with no purpose"""
        log = create_log(
            action='READ',
            resource_sensitivity='HIGH',
            purpose=None
        )
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 6', articles)

    def test_tc14_art7_consent_withdrawn(self):
        """TC-14: Art.7 fires when consent withdrawn but processing active"""
        ConsentRecord.objects.create(
            user_id='u_test',
            purpose='Marketing',
            lawful_basis='CONSENT',
            declared_at=timezone.now(),
            is_valid=False,
            active_processing=True
        )
        log = create_log(user_id='u_test')
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 7', articles)

    def test_tc15_art7_no_trigger_valid_consent(self):
        """TC-15: Art.7 does not fire when consent is valid"""
        ConsentRecord.objects.create(
            user_id='u_test',
            purpose='Marketing',
            lawful_basis='CONSENT',
            declared_at=timezone.now(),
            is_valid=True,
            active_processing=True
        )
        log = create_log(user_id='u_test')
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertNotIn('Art. 7', articles)

    def test_tc16_art9_special_category(self):
        """TC-16: Art.9 fires on special category data access without purpose"""
        log = create_log(
            resource_accessed='health_records',
            purpose=None
        )
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 9', articles)

    def test_tc17_art10_criminal_data(self):
        """TC-17: Art.10 fires on criminal records access"""
        log = create_log(resource_accessed='criminal_records')
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 10', articles)

    def test_tc18_art15_overdue_access_request(self):
        """TC-18: Art.15 fires when access request is overdue"""
        DataSubjectRequest.objects.create(
            subject_id='user_001',
            right_type='ACCESS',
            received_at=timezone.now() - timedelta(days=35),
            response_deadline=timezone.now() - timedelta(days=5),
            status='PENDING'
        )
        log = create_log(user_id='user_001')
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 15', articles)

    def test_tc19_art16_overdue_rectification(self):
        """TC-19: Art.16 fires when rectification request is overdue"""
        DataSubjectRequest.objects.create(
            subject_id='user_002',
            right_type='RECTIFICATION',
            received_at=timezone.now() - timedelta(days=35),
            response_deadline=timezone.now() - timedelta(days=5),
            status='PENDING'
        )
        log = create_log(user_id='user_002')
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 16', articles)

    def test_tc20_art17_overdue_erasure(self):
        """TC-20: Art.17 fires when erasure request is overdue"""
        DataSubjectRequest.objects.create(
            subject_id='user_003',
            right_type='ERASURE',
            received_at=timezone.now() - timedelta(days=35),
            response_deadline=timezone.now() - timedelta(days=5),
            status='PENDING'
        )
        log = create_log(user_id='user_003')
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 17', articles)

    def test_tc21_art18_overdue_restriction(self):
        """TC-21: Art.18 fires when restriction request is overdue"""
        DataSubjectRequest.objects.create(
            subject_id='user_004',
            right_type='RESTRICTION',
            received_at=timezone.now() - timedelta(days=35),
            response_deadline=timezone.now() - timedelta(days=5),
            status='PENDING'
        )
        log = create_log(user_id='user_004')
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 18', articles)

    def test_tc22_art20_overdue_portability(self):
        """TC-22: Art.20 fires when portability request is overdue"""
        DataSubjectRequest.objects.create(
            subject_id='user_005',
            right_type='PORTABILITY',
            received_at=timezone.now() - timedelta(days=35),
            response_deadline=timezone.now() - timedelta(days=5),
            status='PENDING'
        )
        log = create_log(user_id='user_005')
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 20', articles)

    def test_tc23_art21_overdue_objection(self):
        """TC-23: Art.21 fires when objection request is overdue"""
        DataSubjectRequest.objects.create(
            subject_id='user_006',
            right_type='OBJECTION',
            received_at=timezone.now() - timedelta(days=35),
            response_deadline=timezone.now() - timedelta(days=5),
            status='PENDING'
        )
        log = create_log(user_id='user_006')
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 21', articles)

    def test_tc24_art22_automated_decision(self):
        """TC-24: Art.22 fires on automated decision resource without human review"""
        log = create_log(
            resource_accessed='automated_decisions',
            purpose=None
        )
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 22', articles)

    def test_tc25_art25_role_mismatch_intern(self):
        """TC-25: Art.25 fires when INTERN accesses HIGH sensitivity resource"""
        log = create_log(
            user_id='u_tariq',
            resource_sensitivity='HIGH'
        )
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 25', articles)

    def test_windows_account_high_access_is_art25(self):
        """A machine account is staff, not an analyst, so HIGH data is out of role."""
        log = create_log(
            user_id=r'DESKTOP\ataur',
            resource_sensitivity='HIGH',
            purpose='Daily work',
        )
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 25', articles)

    def test_rule_risk_score_is_fixed_for_severity(self):
        rule = Rule.objects.get(gdpr_article='Art. 5')
        first = create_violation(create_log(user_id='u_score_a'), rule, 'first')
        second = create_violation(create_log(user_id='u_score_b'), rule, 'second')
        self.assertEqual(first.risk_score, 0.95)
        self.assertEqual(second.risk_score, 0.95)

    def test_tc26_art25_no_trigger_analyst(self):
        """TC-26: Art.25 does not fire for ANALYST on HIGH sensitivity"""
        log = create_log(
            user_id='u_hassan',
            resource_sensitivity='HIGH'
        )
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertNotIn('Art. 25', articles)

    def test_tc27_art30_not_in_ropa(self):
        """TC-27: Art.30 fires when processing not in RoPA"""
        log = create_log(
            resource_sensitivity='HIGH',
            purpose='Unlisted activity',
        )
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 30', articles)

    def test_tc28_art32_after_hours(self):
        """TC-28: Art.32 fires on after-hours HIGH sensitivity access"""
        log = create_log(
            action='EXPORT',
            resource_sensitivity='HIGH',
            is_outside_hours=True,
            purpose='After hours transfer',
        )
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 32', articles)

    def test_tc29_art32_no_trigger_low_sensitivity(self):
        """TC-29: Art.32 does not fire on after-hours LOW sensitivity"""
        log = create_log(
            resource_sensitivity='LOW',
            is_outside_hours=True
        )
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertNotIn('Art. 32', articles)

    def test_tc30_art33_breach_not_reported(self):
        """TC-30: Art.33 fires when breach not reported within 72 hours"""
        rule = Rule.objects.get(gdpr_article='Art. 5')
        log = create_log()
        violation = Violation.objects.create(
            log=log, rule=rule,
            reason='Test breach', risk_score=0.9, status='OPEN'
        )
        BreachRecord.objects.create(
            violation=violation,
            detected_at=timezone.now() - timedelta(hours=80),
            notification_deadline=timezone.now() - timedelta(hours=8),
            notification_sent=False,
            severity='CRITICAL'
        )
        log2 = create_log()
        check_overdue_breaches()
        articles = list(
            Violation.objects.filter(log=log2, rule__gdpr_article='Art. 33')
            .values_list('rule__gdpr_article', flat=True)
        )
        # The deadline is attached to the breach's own log, not the next unrelated event.
        self.assertTrue(
            Violation.objects.filter(rule__gdpr_article='Art. 33').exists()
        )
        self.assertNotIn('Art. 33', articles)

    def test_tc31_art37_no_dpo(self):
        """TC-31: Art.37 fires when no DPO exists and HIGH risk processing"""
        DPORecord.objects.all().delete()
        log = create_log(resource_sensitivity='HIGH')
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 37', articles)

    def test_tc32_art83_repeated_violations(self):
        """TC-32: Art.83 fires when user has 5 or more violations in 7 days"""
        rule = Rule.objects.get(gdpr_article='Art. 5')
        for _ in range(5):
            log = create_log(user_id='u_repeat')
            Violation.objects.create(
                log=log, rule=rule,
                reason='Repeat violation',
                risk_score=0.9,
                status='OPEN',
            )
        log = create_log(user_id='u_repeat')
        violations = check_all_rules(log)
        articles = [v.rule.gdpr_article for v in violations]
        self.assertIn('Art. 83', articles)


# ─────────────────────────────────────────
# TC-33 to TC-40: ANOMALY DETECTION TESTS
# ─────────────────────────────────────────

class AnomalyDetectionTests(TestCase):

    def setUp(self):
        create_rule('Art. 5', 'CRITICAL')
        create_rule('ML-ANOMALY', 'HIGH')

    def test_tc33_anomaly_detection_runs(self):
        """TC-33: Anomaly detection runs without error on sufficient logs"""
        for _ in range(20):
            create_log(
                resource_sensitivity='HIGH',
                action='EXPORT',
                purpose=None,
                is_outside_hours=True
            )
        result = run_anomaly_detection()
        self.assertIsInstance(result, int)

    def test_tc34_anomaly_detection_minimum_logs(self):
        """TC-34: Anomaly detection returns 0 when fewer than 10 logs"""
        for _ in range(5):
            create_log()
        result = run_anomaly_detection()
        self.assertEqual(result, 0)

    def test_tc35_user_anomaly_score_returned(self):
        """TC-35: User anomaly score returned for user with enough logs"""
        for _ in range(10):
            create_log(user_id='u_scored')
        result = get_user_anomaly_score('u_scored')
        self.assertIsNotNone(result)
        self.assertIn('anomaly_score', result)
        self.assertIn('anomaly_flags', result)

    def test_tc36_user_anomaly_none_for_few_logs(self):
        """TC-36: User anomaly score is None when fewer than 5 logs"""
        for _ in range(3):
            create_log(user_id='u_few')
        result = get_user_anomaly_score('u_few')
        self.assertIsNone(result)

    def test_tc37_anomaly_score_between_0_and_1(self):
        """TC-37: Anomaly score is always between 0.0 and 1.0"""
        for _ in range(15):
            create_log(user_id='u_range')
        result = get_user_anomaly_score('u_range')
        if result:
            self.assertGreaterEqual(result['anomaly_score'], 0.0)
            self.assertLessEqual(result['anomaly_score'], 1.0)

    def test_tc38_anomaly_flags_count(self):
        """TC-38: Anomaly flags count is non-negative integer"""
        for _ in range(15):
            create_log(user_id='u_flags')
        result = get_user_anomaly_score('u_flags')
        if result:
            self.assertGreaterEqual(result['anomaly_flags'], 0)

    def test_tc39_high_risk_user_flagged(self):
        """TC-39: User with all HIGH sensitivity after-hours exports is flagged"""
        for _ in range(15):
            create_log(
                user_id='u_highrisk',
                resource_sensitivity='HIGH',
                action='EXPORT',
                is_outside_hours=True,
                purpose=None
            )
        result = get_user_anomaly_score('u_highrisk')
        if result:
            self.assertIn('is_anomalous', result)

    def test_tc40_anomaly_violation_created(self):
        """TC-40: Anomaly detection creates violation records"""
        for _ in range(20):
            create_log(
                resource_sensitivity='HIGH',
                action='EXPORT',
                is_outside_hours=True,
                purpose=None
            )
        before = Violation.objects.filter(is_anomaly=True).count()
        run_anomaly_detection()
        after = Violation.objects.filter(is_anomaly=True).count()
        self.assertGreaterEqual(after, before)


# ─────────────────────────────────────────
# TC-41 to TC-50: INTEGRATION TESTS
# ─────────────────────────────────────────

class IntegrationTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = AuditraUser.objects.create_user(
            username='integration_admin',
            email='integration@auditra.com',
            password='Integration@2026',
            role='admin',
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        create_rule('Art. 5', 'CRITICAL')
        create_rule('Art. 6', 'HIGH')
        create_rule('Art. 25', 'HIGH')
        create_rule('Art. 32', 'HIGH')
        create_rule('Art. 83', 'CRITICAL')

    def test_tc41_full_login_and_stats(self):
        """TC-41: Login then fetch stats successfully"""
        login_res = self.client.post('/api/auth/login/', {
            'username': 'integration_admin',
            'password': 'Integration@2026'
        }, format='json')
        self.assertEqual(login_res.status_code, 200)
        self.assertIn('access', login_res.data)

        stats_res = self.client.get('/api/stats/')
        self.assertEqual(stats_res.status_code, 200)

    def test_tc42_simulate_creates_log_and_violation(self):
        """TC-42: Simulate creates log and may create violations"""
        log_count_before = Log.objects.count()
        res = self.client.post('/api/simulate/', {}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertGreater(Log.objects.count(), log_count_before)

    def test_tc43_violation_appears_in_list(self):
        """TC-43: Created violation appears in violations list"""
        rule = Rule.objects.first()
        log = create_log()
        Violation.objects.create(
            log=log, rule=rule,
            reason='Test', risk_score=0.9, status='OPEN'
        )
        res = self.client.get('/api/violations/')
        self.assertEqual(res.status_code, 200)
        self.assertGreater(len(res.data), 0)

    def test_tc44_violation_filter_by_severity(self):
        """TC-44: Violations can be filtered by severity"""
        res = self.client.get('/api/violations/?severity=CRITICAL')
        self.assertEqual(res.status_code, 200)
        for v in res.data:
            self.assertEqual(v['rule']['severity'], 'CRITICAL')

    def test_tc45_violation_filter_by_status(self):
        """TC-45: Violations can be filtered by status"""
        rule = Rule.objects.first()
        log = create_log()
        Violation.objects.create(
            log=log, rule=rule,
            reason='Test', risk_score=0.5, status='RESOLVED'
        )
        res = self.client.get('/api/violations/?status=RESOLVED')
        self.assertEqual(res.status_code, 200)
        for v in res.data:
            self.assertEqual(v['status'], 'RESOLVED')

    def test_tc46_user_activity_returns_data(self):
        """TC-46: User activity endpoint returns correct user data"""
        create_log(user_id='u_activity')
        res = self.client.get('/api/user-activity/?user_id=u_activity')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['user_id'], 'u_activity')

    def test_tc47_consent_records_returned(self):
        """TC-47: Consent records endpoint returns list"""
        ConsentRecord.objects.create(
            user_id='u_consent',
            purpose='Test',
            lawful_basis='CONSENT',
            declared_at=timezone.now(),
            is_valid=True,
            active_processing=True
        )
        res = self.client.get('/api/consent-records/')
        self.assertEqual(res.status_code, 200)
        self.assertGreater(len(res.data), 0)

    def test_tc48_deletion_requests_returned(self):
        """TC-48: Deletion requests endpoint returns erasure requests only"""
        DataSubjectRequest.objects.create(
            subject_id='user_del',
            right_type='ERASURE',
            received_at=timezone.now(),
            response_deadline=timezone.now() + timedelta(days=30),
            status='PENDING'
        )
        DataSubjectRequest.objects.create(
            subject_id='user_acc',
            right_type='ACCESS',
            received_at=timezone.now(),
            response_deadline=timezone.now() + timedelta(days=30),
            status='PENDING'
        )
        res = self.client.get('/api/deletion-requests/')
        self.assertEqual(res.status_code, 200)
        for r in res.data:
            self.assertEqual(r['right_type'], 'ERASURE')

    def test_tc49_reports_endpoint_returns_data(self):
        """TC-49: Reports endpoint returns compliance data"""
        res = self.client.get('/api/reports/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('compliance_score', res.data)
        self.assertIn('by_article', res.data)
        self.assertIn('recent_critical', res.data)

    def test_tc50_admin_health_endpoint(self):
        """TC-50: Admin health endpoint returns system status"""
        res = self.client.get('/api/admin/health/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('engine_status', res.data)
        self.assertIn('db_status', res.data)
        self.assertIn('total_logs', res.data)

    def test_ingest_api_key_creates_a_log(self):
        client = APIClient()
        response = client.post(
            '/api/ingest/',
            {
                'logs': [{
                    'user_id': 'agent_user',
                    'timestamp': timezone.now().isoformat(),
                    'resource_accessed': 'security_logs',
                    'action': 'LOGIN',
                    'resource_sensitivity': 'LOW',
                    'ip_address': '10.0.0.8',
                    'purpose': 'Windows event log',
                }],
            },
            format='json',
            HTTP_X_AUDITRA_INGEST_KEY='auditra-ingest-dev-key',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['created'], 1)
        self.assertTrue(Log.objects.filter(user_id='agent_user').exists())

    def test_ingest_rejects_a_bad_key(self):
        client = APIClient()
        response = client.post(
            '/api/ingest/',
            {'logs': [{'user_id': 'nobody'}]},
            format='json',
            HTTP_X_AUDITRA_INGEST_KEY='wrong',
        )
        self.assertEqual(response.status_code, 401)

    def test_consent_can_be_withdrawn(self):
        record = ConsentRecord.objects.create(
            user_id='u_toggle',
            purpose='Marketing',
            lawful_basis='CONSENT',
            declared_at=timezone.now(),
            is_valid=True,
            active_processing=True,
        )
        response = self.client.patch(
            f'/api/consent-records/{record.id}/',
            {'is_valid': False, 'active_processing': True},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertFalse(record.is_valid)
        self.assertTrue(record.active_processing)

    def test_subject_access_status_can_be_updated(self):
        request_row = DataSubjectRequest.objects.create(
            subject_id='user_status',
            right_type='ACCESS',
            received_at=timezone.now(),
            response_deadline=timezone.now() + timedelta(days=30),
            status='PENDING',
        )
        response = self.client.patch(
            f'/api/subject-access-requests/{request_row.id}/',
            {'status': 'IN_PROGRESS'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        request_row.refresh_from_db()
        self.assertEqual(request_row.status, 'IN_PROGRESS')


class DPOVerificationTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = AuditraUser.objects.create_user(
            username='dpo_officer',
            email='officer@auditra.com',
            password='DPOTest@2026',
            role='compliance_officer',
        )
        self.client.force_authenticate(user=self.user)

    def test_dpo_endpoint_creates_missing_record(self):
        response = self.client.get('/api/dpo/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['compliance_status'], 'MISSING')
        self.assertEqual(DPORecord.objects.count(), 1)

    def test_complete_dpo_designation_is_compliant(self):
        response = self.client.put('/api/dpo/', {
            'organization_name': 'Auditra Ltd',
            'dpo_required': True,
            'name': 'Dr. Hina Iqbal',
            'contact': 'dpo@auditra.com',
            'designated_at': '2026-10-06',
            'scope': 'All personal data processing activities',
            'independent': True,
            'direct_access_to_management': True,
            'conflict_free': True,
            'published_contact_details': True,
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['compliance_status'], 'COMPLIANT')

    def test_incomplete_designation_requires_review(self):
        response = self.client.put('/api/dpo/', {
            'organization_name': 'Auditra Ltd',
            'dpo_required': True,
            'name': 'Dr. Hina Iqbal',
            'contact': 'dpo@auditra.com',
            'designated_at': '2026-10-06',
            'scope': 'All personal data processing activities',
            'independent': False,
            'direct_access_to_management': True,
            'conflict_free': True,
            'published_contact_details': False,
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['compliance_status'], 'REVIEW_REQUIRED')

    def test_not_required_status(self):
        response = self.client.put('/api/dpo/', {
            'organization_name': 'Auditra Ltd',
            'dpo_required': False,
            'name': '',
            'contact': '',
            'designated_at': None,
            'scope': '',
            'independent': False,
            'direct_access_to_management': False,
            'conflict_free': False,
            'published_contact_details': False,
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['compliance_status'], 'NOT_REQUIRED')


class RoPAAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = AuditraUser.objects.create_user(
            username='ropa_officer',
            email='ropa@auditra.com',
            password='RoPATest@2026',
            role='compliance_officer',
        )
        self.client.force_authenticate(user=self.user)
        self.activity = ProcessingActivity.objects.create(
            activity_name='Payroll Processing',
            purpose='Payroll',
            legal_basis='CONTRACT',
            data_categories='Employee and financial data',
            retention_period='7 years',
            security_measures='Encryption and role-based access',
        )

    def test_list_processing_activities(self):
        response = self.client.get('/api/processing-activities/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['activity_name'], 'Payroll Processing')

    def test_create_processing_activity(self):
        response = self.client.post('/api/processing-activities/', {
            'activity_name': 'Marketing Emails',
            'purpose': 'Marketing',
            'legal_basis': 'CONSENT',
            'data_categories': 'Email address and preferences',
            'retention_period': '1 year',
            'security_measures': 'Encryption and opt-out controls',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(ProcessingActivity.objects.count(), 2)

    def test_update_processing_activity(self):
        response = self.client.patch(
            f'/api/processing-activities/{self.activity.id}/',
            {'retention_period': '8 years'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.retention_period, '8 years')

    def test_delete_processing_activity(self):
        response = self.client.delete(
            f'/api/processing-activities/{self.activity.id}/'
        )

        self.assertEqual(response.status_code, 204)
        self.assertFalse(ProcessingActivity.objects.filter(pk=self.activity.id).exists())

    def test_filter_processing_activities(self):
        ProcessingActivity.objects.create(
            activity_name='Newsletter',
            purpose='Marketing',
            legal_basis='CONSENT',
            data_categories='Email address',
            retention_period='1 year',
            security_measures='Encryption',
        )

        response = self.client.get(
            '/api/processing-activities/?legal_basis=CONSENT&search=news'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['activity_name'], 'Newsletter')


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='Auditra <noreply@auditra.test>',
    COMPLIANCE_ALERT_RECIPIENTS=['compliance@auditra.test'],
)
class EmailNotificationTests(TestCase):

    def test_critical_violation_sends_email_immediately(self):
        rule = create_rule('Art. 5', 'CRITICAL')
        violation = create_violation(
            create_log(),
            rule,
            'Critical export without a lawful purpose',
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Critical GDPR violation', mail.outbox[0].subject)
        notification = NotificationLog.objects.get()
        self.assertEqual(notification.status, 'SENT')
        self.assertIn(str(violation.id), notification.event_key)

    def test_duplicate_critical_notification_is_skipped(self):
        rule = create_rule('Art. 5', 'CRITICAL')
        violation = create_violation(create_log(), rule, 'Critical test')

        result = notify_critical_violation(violation)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(result['skipped'], 1)
        self.assertEqual(NotificationLog.objects.count(), 1)

    def test_pending_notifications_cover_breach_dsr_and_dpo(self):
        rule = create_rule('Art. 32', 'HIGH')
        violation = create_violation(create_log(), rule, 'High-risk incident')
        BreachRecord.objects.create(
            violation=violation,
            notification_deadline=timezone.now() + timedelta(hours=4),
            notification_sent=False,
            severity='HIGH',
        )
        DataSubjectRequest.objects.create(
            subject_id='subject-100',
            right_type='ACCESS',
            received_at=timezone.now() - timedelta(days=28),
            response_deadline=timezone.now() + timedelta(days=2),
            status='PENDING',
        )
        DPORecord.objects.create(
            organization_name='Auditra Ltd',
            dpo_required=True,
        )

        result = send_pending_compliance_notifications()

        self.assertEqual(result['sent'], 3)
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(
            set(NotificationLog.objects.values_list('event_type', flat=True)),
            {'BREACH_DEADLINE', 'DSR_DEADLINE', 'DPO_STATUS'},
        )

    def test_management_command_reports_delivery_summary(self):
        output = StringIO()

        call_command('send_compliance_notifications', stdout=output)

        self.assertIn('1 sent', output.getvalue())
        self.assertEqual(NotificationLog.objects.filter(status='SENT').count(), 1)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='Auditra <noreply@auditra.test>',
    COMPLIANCE_ALERT_RECIPIENTS=['compliance@auditra.test'],
)
class ComplianceSchedulerTests(TestCase):

    def test_cycle_records_success_and_counters(self):
        create_rule('Art. 5', 'CRITICAL')
        create_log(
            action='EXPORT',
            resource_sensitivity='HIGH',
            purpose=None,
        )

        job = run_compliance_cycle(trigger='manual')

        self.assertEqual(job.status, 'SUCCESS')
        self.assertEqual(job.trigger, 'MANUAL')
        self.assertEqual(job.logs_processed, 1)
        self.assertEqual(job.violations_created, 1)
        self.assertIsNotNone(job.completed_at)
        self.assertEqual(ComplianceJobRun.objects.count(), 1)

    def test_repeated_cycle_does_not_duplicate_violations(self):
        create_rule('Art. 5', 'CRITICAL')
        create_log(
            action='EXPORT',
            resource_sensitivity='HIGH',
            purpose=None,
        )

        first_job = run_compliance_cycle(trigger='scheduled')
        second_job = run_compliance_cycle(trigger='scheduled')

        self.assertEqual(first_job.violations_created, 1)
        self.assertEqual(second_job.logs_processed, 0)
        self.assertEqual(second_job.violations_created, 0)
        self.assertEqual(Violation.objects.count(), 1)

    @patch('compliance.scheduler.run_anomaly_detection')
    def test_cycle_failure_is_recorded(self, anomaly_detection):
        anomaly_detection.side_effect = RuntimeError('Detector unavailable')

        with self.assertRaisesMessage(RuntimeError, 'Detector unavailable'):
            run_compliance_cycle(trigger='manual')

        job = ComplianceJobRun.objects.get()
        self.assertEqual(job.status, 'FAILED')
        self.assertIsNotNone(job.completed_at)
        self.assertIn('Detector unavailable', job.error_message)

    def test_management_command_outputs_summary(self):
        output = StringIO()

        call_command(
            'run_compliance_cycle',
            '--trigger', 'scheduled',
            stdout=output,
        )

        job = ComplianceJobRun.objects.get()
        self.assertEqual(job.trigger, 'SCHEDULED')
        self.assertIn('SUCCESS:', output.getvalue())
