from django.contrib import admin
from .models import Rule, Log, Violation

@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ['rule_id', 'gdpr_article', 'severity', 'description']

@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'role', 'action', 'resource_accessed', 'sensitivity', 'timestamp']
    list_filter = ['role', 'action', 'sensitivity']

@admin.register(Violation)
class ViolationAdmin(admin.ModelAdmin):
    list_display = ['log', 'rule', 'risk_score', 'is_anomaly', 'status', 'detected_at']
    list_filter = ['status', 'is_anomaly', 'rule__severity']