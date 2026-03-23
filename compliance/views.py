from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Count
from .models import Log, Violation, Rule
from .serializers import ViolationSerializer, LogSerializer

@api_view(['GET'])
def get_violations(request):
    severity = request.query_params.get('severity')
    anomaly = request.query_params.get('anomaly')

    qs = Violation.objects.select_related('log', 'rule').order_by('-detected_at')

    if severity:
        qs = qs.filter(rule__severity=severity)
    if anomaly == 'true':
        qs = qs.filter(is_anomaly=True)

    serializer = ViolationSerializer(qs[:100], many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_stats(request):
    total_logs = Log.objects.count()
    total_violations = Violation.objects.count()
    anomaly_count = Violation.objects.filter(is_anomaly=True).count()
    resolved_count = Violation.objects.filter(status='RESOLVED').count()

    compliance_score = 0
    if total_logs > 0:
        compliance_score = round((1 - total_violations / total_logs) * 100, 1)
        compliance_score = max(0, min(100, compliance_score))

    by_severity = (
        Violation.objects
        .values('rule__severity')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    by_article = (
        Violation.objects
        .values('rule__gdpr_article')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    return Response({
        'total_logs': total_logs,
        'total_violations': total_violations,
        'anomaly_count': anomaly_count,
        'resolved_count': resolved_count,
        'compliance_score': compliance_score,
        'by_severity': list(by_severity),
        'by_article': list(by_article),
    })


@api_view(['GET'])
def get_logs(request):
    logs = Log.objects.order_by('-timestamp')[:50]
    serializer = LogSerializer(logs, many=True)
    return Response(serializer.data)


@api_view(['PATCH'])
def update_violation_status(request, pk):
    try:
        violation = Violation.objects.get(pk=pk)
    except Violation.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

    status = request.data.get('status')
    if status in ['OPEN', 'REVIEWING', 'RESOLVED']:
        violation.status = status
        violation.save()
        return Response({'success': True, 'status': violation.status})
    return Response({'error': 'Invalid status'}, status=400)







from django.utils import timezone
import random

@api_view(['POST'])
def simulate_action(request):
    suspicious_log = Log.objects.create(
        user_id='u_tariq',
        role='intern',
        timestamp=timezone.now().replace(hour=2, minute=30),
        resource_accessed='patient_records',
        action='EXPORT',
        sensitivity='HIGH',
        ip_address='192.168.1.99',
        declared_purpose='',
    )

    from .engine import run_rule_engine
    run_rule_engine()

    from .anomaly import run_anomaly_detection
    run_anomaly_detection()

    new_violations = Violation.objects.filter(log=suspicious_log)

    return Response({
        'message': 'Suspicious action simulated successfully',
        'user': 'u_tariq (intern)',
        'action': 'EXPORT on patient_records at 2:30 AM',
        'violations_triggered': new_violations.count(),
        'rules_fired': [v.rule.rule_id + ' — ' + v.rule.gdpr_article for v in new_violations],
    })