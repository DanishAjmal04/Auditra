from rest_framework import serializers
from .models import (
    AuditraUser, Log, Rule, Violation,
    ConsentRecord, DataSubjectRequest,
    BreachRecord, ProcessingActivity,
    DPORecord, Report
)


class AuditraUserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source='date_joined', read_only=True)

    class Meta:
        model = AuditraUser
        fields = ['id', 'name', 'email', 'role', 'status', 'created_at']

    def get_name(self, obj):
        return obj.get_full_name().strip() or obj.username

    def get_role(self, obj):
        return obj.role.upper()

    def get_status(self, obj):
        return 'ACTIVE' if obj.is_active else 'INACTIVE'


class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Log
        fields = [
            'id', 'user_id', 'timestamp', 'resource_accessed',
            'action', 'resource_sensitivity', 'ip_address',
            'purpose', 'is_outside_hours', 'created_at'
        ]


class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rule
        fields = [
            'id', 'gdpr_article', 'description',
            'logic_definition', 'severity', 'enabled', 'created_at'
        ]


class ViolationSerializer(serializers.ModelSerializer):
    log = LogSerializer(read_only=True)
    rule = RuleSerializer(read_only=True)

    class Meta:
        model = Violation
        fields = [
            'id', 'log', 'rule', 'detected_at',
            'is_anomaly', 'risk_score', 'status', 'reason'
        ]


class ConsentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = [
            'id', 'user_id', 'purpose', 'lawful_basis',
            'declared_at', 'is_valid', 'active_processing'
        ]


class DataSubjectRequestSerializer(serializers.ModelSerializer):
    deadline = serializers.SerializerMethodField()
    received_at_date = serializers.SerializerMethodField()

    class Meta:
        model = DataSubjectRequest
        fields = [
            'id', 'subject_id', 'right_type',
            'received_at', 'received_at_date',
            'response_deadline', 'deadline', 'status'
        ]

    def get_deadline(self, obj):
        return obj.response_deadline.strftime('%Y-%m-%d')

    def get_received_at_date(self, obj):
        return obj.received_at.strftime('%Y-%m-%d')


class BreachRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BreachRecord
        fields = [
            'id', 'violation', 'detected_at',
            'notification_deadline', 'notification_sent', 'severity'
        ]


class ProcessingActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingActivity
        fields = [
            'id', 'activity_name', 'purpose', 'legal_basis',
            'data_categories', 'retention_period',
            'security_measures', 'created_at'
        ]


class DPORecordSerializer(serializers.ModelSerializer):
    compliance_status = serializers.ReadOnlyField()

    class Meta:
        model = DPORecord
        fields = [
            'id', 'organization_name', 'dpo_required', 'name', 'contact',
            'designated_at', 'scope', 'independent',
            'direct_access_to_management', 'conflict_free',
            'published_contact_details', 'compliance_status', 'updated_at'
        ]


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            'id', 'generated_at', 'period_covered',
            'violation_summary', 'export_reference'
        ]


class StatsSerializer(serializers.Serializer):
    total_violations = serializers.IntegerField()
    anomaly_count = serializers.IntegerField()
    compliance_score = serializers.IntegerField()
    total_logs = serializers.IntegerField()
    critical_open = serializers.IntegerField()
    high_open = serializers.IntegerField()
    resolved = serializers.IntegerField()
    by_article = serializers.ListField()


class SimulateSerializer(serializers.Serializer):
    user = serializers.CharField()
    action = serializers.CharField()
    resource = serializers.CharField()
    violations_triggered = serializers.IntegerField()
    rules_fired = serializers.ListField(child=serializers.CharField())
