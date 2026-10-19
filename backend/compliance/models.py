from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser


class Log(models.Model):
    ACTION_CHOICES = [
        ('READ', 'Read'),
        ('WRITE', 'Write'),
        ('DELETE', 'Delete'),
        ('EXPORT', 'Export'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
    ]
    SENSITIVITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=100)
    timestamp = models.DateTimeField()
    resource_accessed = models.CharField(max_length=200)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource_sensitivity = models.CharField(max_length=10, choices=SENSITIVITY_CHOICES)
    ip_address = models.CharField(max_length=50)
    purpose = models.CharField(max_length=200, null=True, blank=True)
    is_outside_hours = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_id} - {self.action} - {self.resource_accessed}"

    class Meta:
        db_table = 'logs'
        ordering = ['-timestamp']


class Rule(models.Model):
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gdpr_article = models.CharField(max_length=20)
    description = models.TextField()
    logic_definition = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.gdpr_article} - {self.severity}"

    class Meta:
        db_table = 'rules'


class Violation(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('REVIEWING', 'Reviewing'),
        ('RESOLVED', 'Resolved'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    log = models.ForeignKey(Log, on_delete=models.CASCADE, related_name='violations')
    rule = models.ForeignKey(Rule, on_delete=models.CASCADE, related_name='violations')
    detected_at = models.DateTimeField(auto_now_add=True)
    is_anomaly = models.BooleanField(default=False)
    risk_score = models.FloatField(default=0.0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='OPEN')
    reason = models.TextField()

    def __str__(self):
        return f"Violation - {self.rule.gdpr_article} - {self.status}"

    class Meta:
        db_table = 'violations'
        ordering = ['-detected_at']


class ConsentRecord(models.Model):
    LAWFUL_BASIS_CHOICES = [
        ('CONSENT', 'Consent'),
        ('CONTRACT', 'Contract'),
        ('LEGAL_OBLIGATION', 'Legal Obligation'),
        ('VITAL_INTEREST', 'Vital Interest'),
        ('PUBLIC_TASK', 'Public Task'),
        ('LEGITIMATE_INTEREST', 'Legitimate Interest'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=100)
    purpose = models.CharField(max_length=200)
    lawful_basis = models.CharField(max_length=30, choices=LAWFUL_BASIS_CHOICES)
    declared_at = models.DateTimeField()
    is_valid = models.BooleanField(default=True)
    active_processing = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user_id} - {self.purpose} - {self.lawful_basis}"

    class Meta:
        db_table = 'consent_records'


class DataSubjectRequest(models.Model):
    RIGHT_TYPE_CHOICES = [
        ('ACCESS', 'Access'),
        ('ERASURE', 'Erasure'),
        ('RECTIFICATION', 'Rectification'),
        ('RESTRICTION', 'Restriction'),
        ('PORTABILITY', 'Portability'),
        ('OBJECTION', 'Objection'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject_id = models.CharField(max_length=100)
    right_type = models.CharField(max_length=20, choices=RIGHT_TYPE_CHOICES)
    received_at = models.DateTimeField()
    response_deadline = models.DateTimeField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')

    def __str__(self):
        return f"{self.subject_id} - {self.right_type} - {self.status}"

    class Meta:
        db_table = 'data_subject_requests'


class BreachRecord(models.Model):
    SEVERITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    violation = models.ForeignKey(Violation, on_delete=models.CASCADE, related_name='breaches')
    detected_at = models.DateTimeField(auto_now_add=True)
    notification_deadline = models.DateTimeField()
    notification_sent = models.BooleanField(default=False)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)

    def __str__(self):
        return f"Breach - {self.severity} - {self.detected_at}"

    class Meta:
        db_table = 'breach_records'


class ProcessingActivity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity_name = models.CharField(max_length=200)
    purpose = models.CharField(max_length=200)
    legal_basis = models.CharField(max_length=30)
    data_categories = models.TextField()
    retention_period = models.CharField(max_length=100)
    security_measures = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.activity_name

    class Meta:
        db_table = 'processing_activities'


class DPORecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_name = models.CharField(max_length=200, default='Auditra Organization')
    dpo_required = models.BooleanField(default=True)
    name = models.CharField(max_length=100, blank=True)
    contact = models.EmailField(blank=True)
    designated_at = models.DateField(null=True, blank=True)
    scope = models.TextField(blank=True)
    independent = models.BooleanField(default=False)
    direct_access_to_management = models.BooleanField(default=False)
    conflict_free = models.BooleanField(default=False)
    published_contact_details = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def compliance_status(self):
        if not self.dpo_required:
            return 'NOT_REQUIRED'

        required_details = [
            self.name.strip(),
            self.contact.strip(),
            self.designated_at,
            self.scope.strip(),
            self.independent,
            self.direct_access_to_management,
            self.conflict_free,
            self.published_contact_details,
        ]
        if all(required_details):
            return 'COMPLIANT'
        if not self.name.strip() or not self.designated_at:
            return 'MISSING'
        return 'REVIEW_REQUIRED'

    def __str__(self):
        return f"DPO - {self.name or 'Not designated'} - {self.compliance_status}"

    class Meta:
        db_table = 'dpo_records'


class Report(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    generated_at = models.DateTimeField(auto_now_add=True)
    period_covered = models.CharField(max_length=100)
    violation_summary = models.TextField()
    export_reference = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f"Report - {self.period_covered} - {self.generated_at}"

    class Meta:
        db_table = 'reports'


class NotificationLog(models.Model):
    EVENT_CHOICES = [
        ('CRITICAL_VIOLATION', 'Critical violation'),
        ('BREACH_DEADLINE', 'Breach deadline'),
        ('DSR_DEADLINE', 'Data-subject request deadline'),
        ('DPO_STATUS', 'DPO status'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    event_key = models.CharField(max_length=255, unique=True)
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.event_type} - {self.recipient} - {self.status}"

    class Meta:
        db_table = 'notification_logs'
        ordering = ['-created_at']


class ComplianceJobRun(models.Model):
    TRIGGER_CHOICES = [
        ('MANUAL', 'Manual'),
        ('SCHEDULED', 'Scheduled'),
    ]
    STATUS_CHOICES = [
        ('RUNNING', 'Running'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('SKIPPED', 'Skipped'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trigger = models.CharField(max_length=10, choices=TRIGGER_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='RUNNING')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    logs_processed = models.PositiveIntegerField(default=0)
    violations_created = models.PositiveIntegerField(default=0)
    anomalies_flagged = models.PositiveIntegerField(default=0)
    notifications_sent = models.PositiveIntegerField(default=0)
    notifications_skipped = models.PositiveIntegerField(default=0)
    notifications_failed = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f'{self.trigger} compliance run - {self.status} - {self.started_at}'

    class Meta:
        db_table = 'compliance_job_runs'
        ordering = ['-started_at']


class AuditraUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('compliance_officer', 'Compliance Officer'),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='compliance_officer'
    )

    def is_admin(self):
        return self.role == 'admin'

    def is_compliance_officer(self):
        return self.role == 'compliance_officer'
