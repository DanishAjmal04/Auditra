from django.contrib import admin

from .models import (
    Agent, AuditraUser, BreachRecord, CatalogueEntry, ConsentRecord, DataSubject, DataSubjectRequest, DPORecord,
    Employee, EmployeeAccount, Event, Incident, ProcessingActivity, Rule,
)


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'severity', 'score', 'status', 'account', 'detected_at']
    list_filter = ['severity', 'status', 'kind']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['occurred_at', 'event_type', 'account', 'path', 'domain', 'device']
    list_filter = ['event_type']


admin.site.register([
    Agent, AuditraUser, BreachRecord, CatalogueEntry, ConsentRecord, DataSubject, DataSubjectRequest, DPORecord,
    Employee, EmployeeAccount, ProcessingActivity, Rule,
])
