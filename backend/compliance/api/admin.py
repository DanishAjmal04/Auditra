"""Administration: users, employees and accounts, catalogue, rules, agents, audit trail, reset."""
from django.db import transaction
from django.db.models import Count, Max
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from ..models import (
    Agent, AiDayScore, AuditEntry, AuditraUser, BreachRecord, CatalogueEntry, ComplianceJobRun, Employee,
    EmployeeAccount, Event, Incident, NotificationLog, Rule, normalize_account,
)
from ..permissions import IsAdminOrComplianceOfficer, IsAdminUser
from ..serializers import (
    AgentSerializer, AuditEntrySerializer, CatalogueEntrySerializer, EmployeeAccountSerializer, EmployeeSerializer,
    RuleSerializer, UserSerializer,
)
from .common import AuditedModelMixin, Pages, audit


class UserViewSet(AuditedModelMixin, viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    audit_label = 'user'
    serializer_class = UserSerializer
    queryset = AuditraUser.objects.order_by('username')

    def perform_destroy(self, instance):
        if instance == self.request.user:
            from rest_framework.exceptions import ValidationError
            raise ValidationError('You cannot delete your own account.')
        super().perform_destroy(instance)


class EmployeeViewSet(AuditedModelMixin, viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    audit_label = 'employee'
    serializer_class = EmployeeSerializer
    queryset = Employee.objects.prefetch_related('accounts')

    def perform_update(self, serializer):
        super().perform_update(serializer)
        _refresh_shift_flags(serializer.instance)

    @action(detail=True, methods=['post'], url_path='accounts')
    def add_account(self, request, pk=None):
        employee = self.get_object()
        account = normalize_account(request.data.get('account'))
        if not account:
            return Response({'error': 'account is required, e.g. MACBOOK\\bilal'}, status=status.HTTP_400_BAD_REQUEST)
        existing = EmployeeAccount.objects.filter(account=account).select_related('employee').first()
        if existing and existing.employee_id != employee.id:
            return Response({'error': f'{account} already belongs to {existing.employee.full_name}.'},
                            status=status.HTTP_400_BAD_REQUEST)
        link, _ = EmployeeAccount.objects.get_or_create(account=account, defaults={'employee': employee})
        relinked = _link_events(account, employee)
        audit(request, 'employee.account_link', account, employee=employee.full_name, events_relinked=relinked)
        return Response({**EmployeeAccountSerializer(link).data, 'events_relinked': relinked},
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path=r'accounts/(?P<account_id>[^/.]+)')
    def remove_account(self, request, pk=None, account_id=None):
        employee = self.get_object()
        link = EmployeeAccount.objects.filter(pk=account_id, employee=employee).first()
        if not link:
            return Response(status=status.HTTP_404_NOT_FOUND)
        Event.objects.filter(employee=employee, account__iexact=link.account).update(employee=None)
        audit(request, 'employee.account_unlink', link.account, employee=employee.full_name)
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _link_events(account, employee):
    username = account.split('\\')[-1]
    qs = Event.objects.filter(employee__isnull=True)
    if '\\' in account:
        qs = qs.filter(account__iexact=account)
    else:
        qs = qs.filter(account__iendswith='\\' + username)
    count = qs.update(employee=employee)
    _refresh_shift_flags(employee)
    Incident.objects.filter(employee__isnull=True, account__iexact=account).update(employee=employee)
    return count


def _refresh_shift_flags(employee):
    for event in Event.objects.filter(employee=employee).only('id', 'occurred_at', 'outside_shift'):
        outside = not employee.is_on_shift(event.occurred_at)
        if outside != event.outside_shift:
            Event.objects.filter(pk=event.pk).update(outside_shift=outside)


class CatalogueViewSet(AuditedModelMixin, viewsets.ModelViewSet):
    audit_label = 'catalogue'
    serializer_class = CatalogueEntrySerializer
    queryset = CatalogueEntry.objects.select_related('processing_activity')

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAdminOrComplianceOfficer()]
        return [IsAdminUser()]


class RuleViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = RuleSerializer
    queryset = Rule.objects.annotate(incident_count=Count('incidents')).order_by('source', 'code')

    def get_permissions(self):
        if self.action == 'list':
            return [IsAdminOrComplianceOfficer()]
        return [IsAdminUser()]

    def perform_update(self, serializer):
        rule = serializer.save()
        audit(self.request, 'rule.enable' if rule.enabled else 'rule.disable', rule.code)


class AgentViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = AgentSerializer
    queryset = Agent.objects.annotate(event_count=Count('events')).order_by('hostname')

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        agent = self.get_object()
        agent.revoked = not agent.revoked
        agent.save(update_fields=['revoked'])
        audit(request, 'agent.revoke' if agent.revoked else 'agent.restore', agent.hostname)
        return Response(AgentSerializer(agent).data)


class AuditViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = AuditEntrySerializer
    pagination_class = Pages
    queryset = AuditEntry.objects.select_related('actor')


@api_view(['GET'])
@permission_classes([IsAdminUser])
def unlinked_accounts(request):
    rows = (
        Event.objects.filter(employee__isnull=True)
        .exclude(event_type__in=['AUTOMATED_DECISION', 'RETENTION_EXCEEDED'])
        .values('account', 'machine')
        .annotate(events=Count('id'), last_seen=Max('occurred_at'))
        .order_by('-last_seen')
    )
    return Response(list(rows[:100]))


@api_view(['GET'])
@permission_classes([IsAdminUser])
def health(request):
    jobs = ComplianceJobRun.objects.order_by('-started_at')[:10]
    return Response({
        'agents': AgentSerializer(Agent.objects.annotate(event_count=Count('events')), many=True).data,
        'jobs': [{'started_at': j.started_at, 'status': j.status, 'incidents_created': j.incidents_created,
                  'error': j.error_message} for j in jobs],
        'counts': {
            'events': Event.objects.count(),
            'incidents': Incident.objects.count(),
            'employees': Employee.objects.count(),
            'catalogue': CatalogueEntry.objects.count(),
            'rules_enabled': Rule.objects.filter(enabled=True).count(),
            'rules_total': Rule.objects.count(),
        },
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def reset_monitoring(request):
    """Deletes recorded activity (events, incidents, AI scores, breaches opened from incidents). Configuration
    and GDPR records stay."""
    if request.data.get('confirm') != 'RESET':
        return Response({'error': 'Send {"confirm": "RESET"} to delete all recorded activity.'},
                        status=status.HTTP_400_BAD_REQUEST)
    with transaction.atomic():
        counts = {
            'breaches': BreachRecord.objects.filter(incident__isnull=False).delete()[0],
            'incidents': Incident.objects.all().delete()[0],
            'events': Event.objects.all().delete()[0],
            'ai_scores': AiDayScore.objects.all().delete()[0],
            'notifications': NotificationLog.objects.all().delete()[0],
        }
    audit(request, 'monitoring.reset', 'all activity', **counts)
    return Response(counts)
