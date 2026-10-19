from django.contrib import admin

from .models import ComplianceJobRun, DPORecord, NotificationLog


@admin.register(DPORecord)
class DPORecordAdmin(admin.ModelAdmin):
    list_display = [
        'organization_name', 'name', 'contact', 'dpo_required',
        'status', 'updated_at'
    ]

    @admin.display(description='Compliance status')
    def status(self, obj):
        return obj.compliance_status


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = [
        'event_type', 'recipient', 'subject', 'status', 'created_at', 'sent_at'
    ]
    list_filter = ['event_type', 'status', 'created_at']
    search_fields = ['recipient', 'subject', 'event_key']
    readonly_fields = [
        'event_type', 'event_key', 'recipient', 'subject', 'message',
        'status', 'error_message', 'created_at', 'sent_at'
    ]


@admin.register(ComplianceJobRun)
class ComplianceJobRunAdmin(admin.ModelAdmin):
    list_display = [
        'started_at', 'trigger', 'status', 'logs_processed',
        'violations_created', 'anomalies_flagged', 'notifications_sent',
    ]
    list_filter = ['trigger', 'status', 'started_at']
    readonly_fields = [
        'trigger', 'status', 'started_at', 'completed_at', 'logs_processed',
        'violations_created', 'anomalies_flagged', 'notifications_sent',
        'notifications_skipped', 'notifications_failed', 'error_message',
    ]
