from datetime import timedelta
import os
import random
import time

from django.db.models import Avg, Count, Q
from django.http import HttpResponse
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

from .models import (
    AuditraUser,
    Log,
    Rule,
    Violation,
    ConsentRecord,
    DataSubjectRequest,
    BreachRecord,
    ProcessingActivity,
    DPORecord,
    Report,
    ComplianceJobRun,
)

from .serializers import (
    AuditraUserSerializer,
    LogSerializer,
    RuleSerializer,
    ViolationSerializer,
    ConsentRecordSerializer,
    DataSubjectRequestSerializer,
    DPORecordSerializer,
    ProcessingActivitySerializer,
    ReportSerializer,
)

from .log_generator import (
    generate_single_log,
    generate_scenario_log,
)

from .rule_engine import check_all_rules

from .anomaly_detector import (
    run_anomaly_detection,
    get_user_anomaly_score,
)

from .permissions import (
    IsAdminUser,
    IsComplianceOfficer,
    IsAdminOrComplianceOfficer,
)


# ============================================================
# AUTHENTICATION
# ============================================================

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')

            if not refresh_token:
                return Response(
                    {'error': 'Refresh token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {'message': 'Logged out successfully'},
                status=status.HTTP_200_OK
            )

        except Exception:
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_400_BAD_REQUEST
            )


# ============================================================
# DASHBOARD STATS
# ============================================================

@api_view(['GET'])
@permission_classes([IsAdminOrComplianceOfficer])
def stats(request):

    total_logs = Log.objects.count()

    total_violations = Violation.objects.count()

    anomaly_count = Violation.objects.filter(
        is_anomaly=True
    ).count()

    critical_open = Violation.objects.filter(
        rule__severity='CRITICAL',
        status='OPEN'
    ).count()

    high_open = Violation.objects.filter(
        rule__severity='HIGH',
        status='OPEN'
    ).count()

    resolved = Violation.objects.filter(
        status='RESOLVED'
    ).count()

    if total_logs > 0:
        violation_rate = total_violations / total_logs
        compliance_score = max(
            0,
            int((1 - violation_rate) * 100)
        )
    else:
        compliance_score = 100

    by_article = list(
        Violation.objects
        .values('rule__gdpr_article')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )

    return Response({
        'total_logs': total_logs,
        'total_violations': total_violations,
        'anomaly_count': anomaly_count,
        'compliance_score': compliance_score,
        'critical_open': critical_open,
        'high_open': high_open,
        'resolved': resolved,
        'by_article': by_article,
    })


# ============================================================
# LOGS
# ============================================================

@api_view(['GET'])
@permission_classes([IsAdminOrComplianceOfficer])
def logs_list(request):

    logs = Log.objects.all().order_by('-timestamp')[:200]

    serializer = LogSerializer(
        logs,
        many=True
    )

    return Response(serializer.data)


# ============================================================
# VIOLATIONS
# ============================================================

@api_view(['GET'])
@permission_classes([IsAdminOrComplianceOfficer])
def violations_list(request):

    violations = (
        Violation.objects
        .select_related('log', 'rule')
        .all()
    )

    severity = request.GET.get('severity')
    status_filter = request.GET.get('status')
    user_id = request.GET.get('user_id')

    if severity:
        violations = violations.filter(
            rule__severity=severity
        )

    if status_filter:
        violations = violations.filter(
            status=status_filter
        )

    if user_id:
        violations = violations.filter(
            log__user_id=user_id
        )

    serializer = ViolationSerializer(
        violations,
        many=True
    )

    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAdminOrComplianceOfficer])
def violation_update(request, pk):

    try:
        violation = Violation.objects.get(pk=pk)

    except Violation.DoesNotExist:
        return Response(
            {'error': 'Not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    new_status = request.data.get('status')

    if new_status in [
        'OPEN',
        'REVIEWING',
        'RESOLVED'
    ]:

        violation.status = new_status
        violation.save()

        return Response(
            ViolationSerializer(violation).data
        )

    return Response(
        {'error': 'Invalid status'},
        status=status.HTTP_400_BAD_REQUEST
    )


# ============================================================
# SIMULATION
# ============================================================

@api_view(['POST'])
@permission_classes([IsAdminOrComplianceOfficer])
def simulate(request):

    scenario = request.data.get(
        'scenario',
        'random'
    )

    log = generate_scenario_log(
        scenario
    )

    violations = check_all_rules(
        log
    )

    run_anomaly_detection()

    rules_fired = [
        f"{v.rule.gdpr_article} — "
        f"{v.rule.description[:50]}"
        for v in violations
    ]

    return Response({
        'user': log.user_id,
        'action': log.action,
        'resource': log.resource_accessed,
        'violations_triggered': len(violations),
        'rules_fired': rules_fired,
    })


# ============================================================
# RULES
# ============================================================

@api_view(['GET'])
@permission_classes([IsAdminOrComplianceOfficer])
def rules_list(request):

    rules = Rule.objects.all()

    serializer = RuleSerializer(
        rules,
        many=True
    )

    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def rule_update(request, pk):

    try:
        rule = Rule.objects.get(pk=pk)

    except Rule.DoesNotExist:
        return Response(
            {'error': 'Not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if 'enabled' in request.data:
        rule.enabled = request.data['enabled']

    if 'severity' in request.data:
        rule.severity = request.data['severity']

    if 'description' in request.data:
        rule.description = request.data['description']

    rule.save()

    return Response(
        RuleSerializer(rule).data
    )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def rule_create(request):

    serializer = RuleSerializer(
        data=request.data
    )

    if serializer.is_valid():
        serializer.save()

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


# ============================================================
# USER ACTIVITY
# ============================================================

@api_view(['GET'])
@permission_classes([IsAdminOrComplianceOfficer])
def users_list(request):

    users = (
        Log.objects
        .values_list(
            'user_id',
            flat=True
        )
        .distinct()
    )

    return Response(
        list(users)
    )


@api_view(['GET'])
@permission_classes([IsAdminOrComplianceOfficer])
def user_activity(request):

    user_id = request.GET.get(
        'user_id'
    )

    if not user_id:
        return Response(
            {'error': 'user_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    violations = (
        Violation.objects
        .filter(log__user_id=user_id)
        .select_related('log', 'rule')
    )

    total_violations = violations.count()

    avg_risk = violations.aggregate(
        avg=Avg('risk_score')
    )['avg'] or 0

    avg_risk = round(
        avg_risk,
        2
    )

    most_common = (
        violations
        .values('rule__gdpr_article')
        .annotate(count=Count('id'))
        .order_by('-count')
        .first()
    )

    most_common_article = (
        most_common['rule__gdpr_article']
        if most_common
        else 'N/A'
    )

    timeline_data = {}

    for violation in violations:

        date = violation.detected_at.strftime(
            '%b %d'
        )

        timeline_data[date] = (
            timeline_data.get(date, 0) + 1
        )

    timeline = [
        {
            'date': key,
            'count': value
        }
        for key, value in sorted(
            timeline_data.items()
        )
    ]

    anomaly_data = get_user_anomaly_score(
        user_id
    )

    return Response({
        'user_id': user_id,
        'total_violations': total_violations,
        'avg_risk_score': avg_risk,
        'most_common': most_common_article,
        'violations': ViolationSerializer(
            violations,
            many=True
        ).data,
        'timeline': timeline,
        'anomaly': anomaly_data,
    })


# ============================================================
# CONSENT RECORDS
# ============================================================

@api_view(['GET'])
@permission_classes([IsAdminOrComplianceOfficer])
def consent_records(request):

    records = ConsentRecord.objects.all()

    serializer = ConsentRecordSerializer(
        records,
        many=True
    )

    return Response(
        serializer.data
    )


# ============================================================
# DPO DESIGNATION VERIFICATION
# ============================================================

@api_view(['GET', 'PUT'])
@permission_classes([IsAdminOrComplianceOfficer])
def dpo_designation(request):
    designation = DPORecord.objects.order_by('-updated_at').first()

    if designation is None:
        designation = DPORecord.objects.create()

    if request.method == 'PUT':
        serializer = DPORecordSerializer(
            designation,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    return Response(DPORecordSerializer(designation).data)


# ============================================================
# RECORDS OF PROCESSING ACTIVITIES (RoPA)
# ============================================================

@api_view(['GET', 'POST'])
@permission_classes([IsAdminOrComplianceOfficer])
def processing_activities(request):
    if request.method == 'POST':
        serializer = ProcessingActivitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    activities = ProcessingActivity.objects.all().order_by('-created_at')
    search = request.query_params.get('search', '').strip()
    legal_basis = request.query_params.get('legal_basis', '').strip()

    if search:
        activities = activities.filter(
            Q(activity_name__icontains=search)
            | Q(purpose__icontains=search)
            | Q(data_categories__icontains=search)
        )
    if legal_basis:
        activities = activities.filter(legal_basis=legal_basis)

    return Response(ProcessingActivitySerializer(activities, many=True).data)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAdminOrComplianceOfficer])
def processing_activity_detail(request, pk):
    try:
        activity = ProcessingActivity.objects.get(pk=pk)
    except ProcessingActivity.DoesNotExist:
        return Response(
            {'error': 'Processing activity not found'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == 'PATCH':
        serializer = ProcessingActivitySerializer(
            activity,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    if request.method == 'DELETE':
        activity.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    return Response(ProcessingActivitySerializer(activity).data)


# ============================================================
# DELETION REQUESTS
# ============================================================

@api_view(['GET'])
@permission_classes([IsAdminOrComplianceOfficer])
def deletion_requests(request):

    requests_qs = (
        DataSubjectRequest.objects
        .filter(right_type='ERASURE')
        .order_by('response_deadline')
    )

    serializer = DataSubjectRequestSerializer(
        requests_qs,
        many=True
    )

    return Response(
        serializer.data
    )


@api_view(['PATCH'])
@permission_classes([IsAdminOrComplianceOfficer])
def deletion_request_update(request, pk):

    try:
        req = DataSubjectRequest.objects.get(
            pk=pk
        )

    except DataSubjectRequest.DoesNotExist:
        return Response(
            {'error': 'Not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    new_status = request.data.get(
        'status'
    )

    if new_status in [
        'PENDING',
        'IN_PROGRESS',
        'COMPLETED'
    ]:

        req.status = new_status
        req.save()

        return Response(
            DataSubjectRequestSerializer(
                req
            ).data
        )

    return Response(
        {'error': 'Invalid status'},
        status=status.HTTP_400_BAD_REQUEST
    )


# ============================================================
# SUBJECT ACCESS REQUESTS
# ============================================================

@api_view(['GET'])
@permission_classes([IsAdminOrComplianceOfficer])
def subject_access_requests(request):

    requests_qs = (
        DataSubjectRequest.objects
        .exclude(right_type='ERASURE')
        .order_by('response_deadline')
    )

    serializer = DataSubjectRequestSerializer(
        requests_qs,
        many=True
    )

    return Response(
        serializer.data
    )


# ============================================================
# REPORTS
# ============================================================

@api_view(['GET'])
@permission_classes([IsAdminOrComplianceOfficer])
def reports(request):

    total_logs = Log.objects.count()

    total_violations = Violation.objects.count()

    critical_open = Violation.objects.filter(
        rule__severity='CRITICAL',
        status='OPEN'
    ).count()

    high_open = Violation.objects.filter(
        rule__severity='HIGH',
        status='OPEN'
    ).count()

    resolved = Violation.objects.filter(
        status='RESOLVED'
    ).count()

    if total_logs > 0:
        compliance_score = max(
            0,
            int(
                (1 - total_violations / total_logs)
                * 100
            )
        )
    else:
        compliance_score = 100

    by_article = list(
        Violation.objects
        .values('rule__gdpr_article')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    critical_violations = (
        Violation.objects
        .filter(
            rule__severity='CRITICAL',
            status='OPEN'
        )
        .select_related('log', 'rule')[:5]
    )

    return Response({
        'compliance_score': compliance_score,
        'total_violations': total_violations,
        'critical_open': critical_open,
        'high_open': high_open,
        'resolved': resolved,
        'generated_at': timezone.now().strftime(
            '%Y-%m-%d %H:%M:%S'
        ),
        'by_article': [
            {
                'article': a['rule__gdpr_article'],
                'count': a['count']
            }
            for a in by_article
        ],
        'recent_critical': [
            {
                'id': str(v.id),
                'user': v.log.user_id,
                'article': v.rule.gdpr_article,
                'reason': v.reason,
                'risk': v.risk_score,
                'date': v.detected_at.strftime(
                    '%Y-%m-%d'
                ),
            }
            for v in critical_violations
        ],
    })


# ============================================================
# ADMIN — USERS
# ============================================================

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_users(request):
    users = AuditraUser.objects.all().order_by('-date_joined')

    serializer = AuditraUserSerializer(
        users,
        many=True
    )

    return Response(
        serializer.data
    )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def admin_user_create(request):
    name = request.data.get('name', '').strip()
    email = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')
    role = request.data.get('role', 'COMPLIANCE_OFFICER').lower()

    if role == 'compliance officer':
        role = 'compliance_officer'

    if not name or not email or not password:
        return Response(
            {'error': 'Name, email and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if role not in ['admin', 'compliance_officer']:
        return Response(
            {'error': 'Invalid role'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if AuditraUser.objects.filter(email__iexact=email).exists():
        return Response(
            {'email': ['A user with this email already exists.']},
            status=status.HTTP_400_BAD_REQUEST
        )

    base_username = email.split('@')[0]
    username = base_username
    suffix = 1
    while AuditraUser.objects.filter(username=username).exists():
        suffix += 1
        username = f'{base_username}{suffix}'

    name_parts = name.split(maxsplit=1)
    user = AuditraUser.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=name_parts[0],
        last_name=name_parts[1] if len(name_parts) > 1 else '',
        role=role,
        is_staff=role == 'admin',
    )

    return Response(
        AuditraUserSerializer(user).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAdminUser])
def admin_user_update(request, pk):
    try:
        user = AuditraUser.objects.get(
            pk=pk
        )

    except AuditraUser.DoesNotExist:
        return Response(
            {'error': 'Not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == 'DELETE':
        if user == request.user:
            return Response(
                {'error': 'You cannot delete your own account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.delete()

        return Response({
            'message': 'User deleted'
        })

    if 'status' in request.data:
        requested_status = request.data['status']
        if requested_status not in ['ACTIVE', 'INACTIVE']:
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if user == request.user and requested_status == 'INACTIVE':
            return Response(
                {'error': 'You cannot deactivate your own account'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.is_active = requested_status == 'ACTIVE'

    if 'role' in request.data:
        role = request.data['role'].lower()
        if role not in ['admin', 'compliance_officer']:
            return Response(
                {'error': 'Invalid role'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.role = role
        user.is_staff = role == 'admin'

    if (
        'password' in request.data
        and request.data['password']
    ):

        user.set_password(request.data['password'])

    user.save()

    return Response(
        AuditraUserSerializer(user).data
    )


# ============================================================
# ADMIN — STATS
# ============================================================

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_stats(request):

    total_users = AuditraUser.objects.count()

    total_rules = Rule.objects.count()

    active_rules = Rule.objects.filter(
        enabled=True
    ).count()

    total_logs = Log.objects.count()

    total_violations = Violation.objects.count()

    if total_logs > 0:
        compliance_score = max(
            0,
            int(
                (1 - total_violations / total_logs)
                * 100
            )
        )
    else:
        compliance_score = 100

    by_article = list(
        Violation.objects
        .values('rule__gdpr_article')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    recent_users = (
        AuditraUser.objects
        .order_by('-date_joined')[:3]
    )

    return Response({
        'total_users': total_users,
        'total_rules': total_rules,
        'active_rules': active_rules,
        'total_logs': total_logs,
        'total_violations': total_violations,
        'compliance_score': compliance_score,
        'by_article': [
            {
                'article': a['rule__gdpr_article'],
                'count': a['count']
            }
            for a in by_article
        ],
        'recent_users': AuditraUserSerializer(
            recent_users,
            many=True
        ).data,
    })


# ============================================================
# ADMIN — SYSTEM HEALTH
# ============================================================

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_health(request):

    total_logs = Log.objects.count()

    total_violations = Violation.objects.count()

    total_rules = Rule.objects.count()

    active_rules = Rule.objects.filter(
        enabled=True
    ).count()

    last_job = (
        ComplianceJobRun.objects
        .order_by('-started_at')
        .first()
    )

    last_log = (
        Log.objects
        .order_by('-created_at')
        .first()
    )

    start = time.time()

    Log.objects.count()

    api_ms = round(
        (time.time() - start) * 1000,
        2
    )

    # PostgreSQL is being used.
    db_size = 'PostgreSQL'

    return Response({
        'total_logs': total_logs,
        'total_violations': total_violations,
        'total_rules': total_rules,
        'active_rules': active_rules,
        'api_response_ms': api_ms,
        'db_size': db_size,
        'last_engine_run':
            (last_job.completed_at or last_job.started_at).strftime(
                '%Y-%m-%d %H:%M:%S'
            )
            if last_job
            else 'Never',

        'last_simulation':
            last_log.created_at.strftime(
                '%Y-%m-%d %H:%M:%S'
            )
            if last_log
            else 'Never',

        'uptime': '99.8%',
        'engine_status': last_job.status if last_job else 'NEVER_RUN',
        'last_job': {
            'id': str(last_job.id),
            'trigger': last_job.trigger,
            'status': last_job.status,
            'started_at': last_job.started_at.isoformat(),
            'completed_at': (
                last_job.completed_at.isoformat()
                if last_job.completed_at else None
            ),
            'logs_processed': last_job.logs_processed,
            'violations_created': last_job.violations_created,
            'anomalies_flagged': last_job.anomalies_flagged,
            'notifications_sent': last_job.notifications_sent,
            'notifications_skipped': last_job.notifications_skipped,
            'notifications_failed': last_job.notifications_failed,
            'error_message': last_job.error_message,
        } if last_job else None,
        'db_status': 'HEALTHY',
        'api_status': 'HEALTHY',
    })


# ============================================================
# GENERATE GENERAL PDF REPORT
# ============================================================

@api_view(['GET'])
@permission_classes([IsAdminOrComplianceOfficer])
def generate_pdf(request):

    response = HttpResponse(
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        f'attachment; filename="auditra-report-'
        f'{timezone.now().strftime("%Y-%m-%d")}.pdf"'
    )

    response['Access-Control-Expose-Headers'] = (
        'Content-Disposition'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()

    elements = []

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#8892b0'),
        spaceAfter=4
    )

    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#1a1a2e'),
        spaceBefore=16,
        spaceAfter=8,
        borderPad=4
    )

    elements.append(
        Paragraph('Auditra', title_style)
    )

    elements.append(
        Paragraph(
            'GDPR Compliance Monitoring Report',
            subtitle_style
        )
    )

    elements.append(
        Paragraph(
            f'Generated: '
            f'{timezone.now().strftime("%Y-%m-%d %H:%M:%S")} UTC',
            subtitle_style
        )
    )

    elements.append(
        Spacer(1, 0.5 * cm)
    )

    divider = Table(
        [['']],
        colWidths=[17 * cm],
        rowHeights=[2]
    )

    divider.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, -1),
                colors.HexColor('#1a1a2e')
            ),
        ])
    )

    elements.append(divider)

    elements.append(
        Spacer(1, 0.5 * cm)
    )

    # ---------------- STATS ----------------

    total_logs = Log.objects.count()

    total_violations = Violation.objects.count()

    critical_open = Violation.objects.filter(
        rule__severity='CRITICAL',
        status='OPEN'
    ).count()

    high_open = Violation.objects.filter(
        rule__severity='HIGH',
        status='OPEN'
    ).count()

    resolved = Violation.objects.filter(
        status='RESOLVED'
    ).count()

    compliance_score = (
        max(
            0,
            int(
                (
                    1 -
                    total_violations /
                    total_logs
                ) * 100
            )
        )
        if total_logs > 0
        else 100
    )

    elements.append(
        Paragraph(
            'Executive Summary',
            heading_style
        )
    )

    summary_data = [
        ['Metric', 'Value'],
        [
            'Compliance Score',
            f'{compliance_score}%'
        ],
        [
            'Total Logs Analyzed',
            str(total_logs)
        ],
        [
            'Total Violations Detected',
            str(total_violations)
        ],
        [
            'Critical Open Violations',
            str(critical_open)
        ],
        [
            'High Open Violations',
            str(high_open)
        ],
        [
            'Resolved Violations',
            str(resolved)
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[
            9 * cm,
            8 * cm
        ]
    )

    summary_table.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, 0),
                colors.HexColor('#1a1a2e')
            ),
            (
                'TEXTCOLOR',
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                'FONTNAME',
                (0, 0),
                (-1, 0),
                'Helvetica-Bold'
            ),
            (
                'FONTSIZE',
                (0, 0),
                (-1, 0),
                11
            ),
            (
                'ALIGN',
                (0, 0),
                (-1, -1),
                'LEFT'
            ),
            (
                'FONTNAME',
                (0, 1),
                (-1, -1),
                'Helvetica'
            ),
            (
                'FONTSIZE',
                (0, 1),
                (-1, -1),
                10
            ),
            (
                'ROWBACKGROUNDS',
                (0, 1),
                (-1, -1),
                [
                    colors.HexColor('#f8f9fa'),
                    colors.white
                ]
            ),
            (
                'GRID',
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor('#dee2e6')
            ),
            (
                'PADDING',
                (0, 0),
                (-1, -1),
                8
            ),
            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                10
            ),
            (
                'BOTTOMPADDING',
                (0, 0),
                (-1, -1),
                10
            ),
        ])
    )

    elements.append(summary_table)

    elements.append(
        Spacer(1, 0.5 * cm)
    )

    # ---------------- ARTICLES ----------------

    elements.append(
        Paragraph(
            'Violations by GDPR Article',
            heading_style
        )
    )

    by_article = list(
        Violation.objects
        .values(
            'rule__gdpr_article',
            'rule__severity'
        )
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    if by_article:

        article_data = [
            [
                'GDPR Article',
                'Severity',
                'Violation Count'
            ]
        ]

        for row in by_article:

            article_data.append([
                row['rule__gdpr_article'],
                row['rule__severity'],
                str(row['count'])
            ])

        article_table = Table(
            article_data,
            colWidths=[
                6 * cm,
                6 * cm,
                5 * cm
            ]
        )

        article_table.setStyle(
            TableStyle([
                (
                    'BACKGROUND',
                    (0, 0),
                    (-1, 0),
                    colors.HexColor('#1a1a2e')
                ),
                (
                    'TEXTCOLOR',
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),
                (
                    'FONTNAME',
                    (0, 0),
                    (-1, 0),
                    'Helvetica-Bold'
                ),
                (
                    'FONTSIZE',
                    (0, 0),
                    (-1, 0),
                    10
                ),
                (
                    'ALIGN',
                    (0, 0),
                    (-1, -1),
                    'LEFT'
                ),
                (
                    'FONTNAME',
                    (0, 1),
                    (-1, -1),
                    'Helvetica'
                ),
                (
                    'FONTSIZE',
                    (0, 1),
                    (-1, -1),
                    9
                ),
                (
                    'ROWBACKGROUNDS',
                    (0, 1),
                    (-1, -1),
                    [
                        colors.HexColor('#f8f9fa'),
                        colors.white
                    ]
                ),
                (
                    'GRID',
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor('#dee2e6')
                ),
                (
                    'PADDING',
                    (0, 0),
                    (-1, -1),
                    8
                ),
            ])
        )

        elements.append(article_table)

    else:

        elements.append(
            Paragraph(
                'No violations recorded.',
                styles['Normal']
            )
        )

    elements.append(
        Spacer(1, 0.5 * cm)
    )

    # ---------------- CRITICAL ----------------

    elements.append(
        Paragraph(
            'Open Critical Violations',
            heading_style
        )
    )

    critical = (
        Violation.objects
        .filter(
            rule__severity='CRITICAL',
            status='OPEN'
        )
        .select_related('log', 'rule')[:10]
    )

    if critical:

        crit_data = [[
            'User',
            'Article',
            'Risk Score',
            'Date',
            'Reason'
        ]]

        for v in critical:

            crit_data.append([
                v.log.user_id,
                v.rule.gdpr_article,
                str(round(v.risk_score, 2)),
                v.detected_at.strftime(
                    '%Y-%m-%d'
                ),
                Paragraph(
                    (
                        v.reason[:60] + '...'
                        if len(v.reason) > 60
                        else v.reason
                    ),
                    styles['Normal']
                )
            ])

        crit_table = Table(
            crit_data,
            colWidths=[
                3 * cm,
                2.5 * cm,
                2.5 * cm,
                2.5 * cm,
                6.5 * cm
            ]
        )

        crit_table.setStyle(
            TableStyle([
                (
                    'BACKGROUND',
                    (0, 0),
                    (-1, 0),
                    colors.HexColor('#e53e3e')
                ),
                (
                    'TEXTCOLOR',
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),
                (
                    'FONTNAME',
                    (0, 0),
                    (-1, 0),
                    'Helvetica-Bold'
                ),
                (
                    'FONTSIZE',
                    (0, 0),
                    (-1, 0),
                    9
                ),
                (
                    'ALIGN',
                    (0, 0),
                    (-1, -1),
                    'LEFT'
                ),
                (
                    'FONTNAME',
                    (0, 1),
                    (-1, -1),
                    'Helvetica'
                ),
                (
                    'FONTSIZE',
                    (0, 1),
                    (-1, -1),
                    8
                ),
                (
                    'ROWBACKGROUNDS',
                    (0, 1),
                    (-1, -1),
                    [
                        colors.HexColor('#fff0f0'),
                        colors.white
                    ]
                ),
                (
                    'GRID',
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor('#dee2e6')
                ),
                (
                    'PADDING',
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    'VALIGN',
                    (0, 0),
                    (-1, -1),
                    'TOP'
                ),
            ])
        )

        elements.append(crit_table)

    else:

        elements.append(
            Paragraph(
                'No critical violations open.',
                styles['Normal']
            )
        )

    elements.append(
        Spacer(1, 0.5 * cm)
    )

    elements.append(divider)

    elements.append(
        Spacer(1, 0.3 * cm)
    )

    elements.append(
        Paragraph(
            'This report was generated by Auditra — '
            'Automated GDPR Compliance Monitoring System.',
            subtitle_style
        )
    )

    elements.append(
        Paragraph(
            'Confidential — for internal use only.',
            subtitle_style
        )
    )

    doc.build(elements)

    return response


# ============================================================
# INGEST LOGS
# ============================================================

@api_view(['POST'])
@permission_classes([IsAdminOrComplianceOfficer])
def ingest_logs(request):

    logs_data = request.data.get(
        'logs',
        []
    )

    if not logs_data:

        return Response(
            {'error': 'No logs provided'},
            status=status.HTTP_400_BAD_REQUEST
        )

    created_logs = []

    total_violations = 0

    for entry in logs_data:

        try:

            from django.utils.dateparse import parse_datetime

            timestamp_raw = entry.get(
                'timestamp'
            )

            try:

                timestamp = parse_datetime(
                    timestamp_raw
                )

                if not timestamp:
                    timestamp = timezone.now()

                if timezone.is_naive(timestamp):
                    timestamp = timezone.make_aware(
                        timestamp
                    )

            except Exception:

                timestamp = timezone.now()

            hour = (
                timestamp.hour
                if timestamp
                else 12
            )

            outside_hours = (
                hour < 8 or hour > 18
            )

            log = Log.objects.create(
                user_id=entry.get(
                    'user_id',
                    'unknown'
                ),

                timestamp=(
                    timestamp
                    or timezone.now()
                ),

                resource_accessed=entry.get(
                    'resource_accessed',
                    'unknown'
                ),

                action=entry.get(
                    'action',
                    'READ'
                ),

                resource_sensitivity=entry.get(
                    'resource_sensitivity',
                    'MEDIUM'
                ),

                ip_address=entry.get(
                    'ip_address',
                    '0.0.0.0'
                ),

                purpose=entry.get(
                    'purpose',
                    None
                ),

                is_outside_hours=outside_hours
            )

            violations = check_all_rules(
                log
            )

            total_violations += len(
                violations
            )

            created_logs.append(
                str(log.id)
            )

        except Exception as e:

            print(
                f'[INGEST ERROR] {e}'
            )

            import traceback

            traceback.print_exc()

            continue

    if len(created_logs) >= 10:

        run_anomaly_detection()

    return Response({
        'received': len(logs_data),
        'created': len(created_logs),
        'violations_detected':
            total_violations,
        'message':
            f'{len(created_logs)} logs '
            f'ingested successfully'
    })


# ============================================================
# USER PDF REPORT
# ============================================================

@api_view(['GET'])
@permission_classes([IsAdminOrComplianceOfficer])
def generate_user_pdf(request, user_id):

    violations = (
        Violation.objects
        .filter(
            log__user_id=user_id
        )
        .select_related(
            'log',
            'rule'
        )
        .order_by(
            '-detected_at'
        )
    )

    total_violations = violations.count()

    avg_risk = violations.aggregate(
        avg=Avg('risk_score')
    )['avg'] or 0

    avg_risk_pct = int(
        avg_risk * 100
    )

    critical_count = violations.filter(
        rule__severity='CRITICAL'
    ).count()

    high_count = violations.filter(
        rule__severity='HIGH'
    ).count()

    medium_count = violations.filter(
        rule__severity='MEDIUM'
    ).count()

    low_count = violations.filter(
        rule__severity='LOW'
    ).count()

    open_count = violations.filter(
        status='OPEN'
    ).count()

    resolved_count = violations.filter(
        status='RESOLVED'
    ).count()

    anomaly_count = violations.filter(
        is_anomaly=True
    ).count()

    total_logs = Log.objects.filter(
        user_id=user_id
    ).count()

    if total_logs > 0:

        compliance_score = max(
            0,
            int(
                (
                    1 -
                    total_violations /
                    total_logs
                ) * 100
            )
        )

    else:

        compliance_score = 100

    if (
        critical_count >= 2
        or avg_risk > 0.75
    ):

        risk_level = 'HIGH'
        risk_color = colors.HexColor(
            '#e53e3e'
        )

    elif (
        critical_count >= 1
        or avg_risk > 0.5
    ):

        risk_level = 'MEDIUM'
        risk_color = colors.HexColor(
            '#dd6b20'
        )

    else:

        risk_level = 'LOW'
        risk_color = colors.HexColor(
            '#38a169'
        )

    report_id = (
        f'AUD-REP-'
        f'{timezone.now().year}-'
        f'{random.randint(100, 999)}'
    )

    now = timezone.now()

    period_start = (
        now - timedelta(days=14)
    ).strftime('%d %b %Y')

    period_end = now.strftime(
        '%d %b %Y'
    )

    response = HttpResponse(
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        f'attachment; filename='
        f'"auditra-user-{user_id}-'
        f'{timezone.now().strftime("%Y-%m-%d")}.pdf"'
    )

    response['Access-Control-Expose-Headers'] = (
        'Content-Disposition'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()

    elements = []

    # ========================================================
    # PDF STYLES
    # ========================================================

    title_style = ParagraphStyle(
        'T',
        parent=styles['Title'],
        fontSize=16,
        textColor=colors.HexColor(
            '#1a1a2e'
        ),
        spaceAfter=4,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'S',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor(
            '#8892b0'
        ),
        spaceAfter=2
    )

    section_style = ParagraphStyle(
        'SEC',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.white,
        fontName='Helvetica-Bold',
        spaceAfter=0
    )

    normal = ParagraphStyle(
        'N',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor(
            '#333333'
        ),
        spaceAfter=4
    )

    def section_header(text):

        table = Table(
            [[
                Paragraph(
                    text,
                    section_style
                )
            ]],
            colWidths=[17 * cm]
        )

        table.setStyle(
            TableStyle([
                (
                    'BACKGROUND',
                    (0, 0),
                    (-1, -1),
                    colors.HexColor('#1a1a2e')
                ),
                (
                    'PADDING',
                    (0, 0),
                    (-1, -1),
                    8
                ),
            ])
        )

        return table

    def info_table(
        data,
        col_widths=[6 * cm, 11 * cm]
    ):

        table = Table(
            data,
            colWidths=col_widths
        )

        table.setStyle(
            TableStyle([
                (
                    'FONTNAME',
                    (0, 0),
                    (0, -1),
                    'Helvetica-Bold'
                ),
                (
                    'FONTSIZE',
                    (0, 0),
                    (-1, -1),
                    9
                ),
                (
                    'TEXTCOLOR',
                    (0, 0),
                    (0, -1),
                    colors.HexColor('#555555')
                ),
                (
                    'TEXTCOLOR',
                    (1, 0),
                    (1, -1),
                    colors.HexColor('#1a1a2e')
                ),
                (
                    'ROWBACKGROUNDS',
                    (0, 0),
                    (-1, -1),
                    [
                        colors.HexColor('#f8f9fa'),
                        colors.white
                    ]
                ),
                (
                    'GRID',
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor('#dee2e6')
                ),
                (
                    'PADDING',
                    (0, 0),
                    (-1, -1),
                    7
                ),
                (
                    'VALIGN',
                    (0, 0),
                    (-1, -1),
                    'MIDDLE'
                ),
            ])
        )

        return table

    # ========================================================
    # HEADER
    # ========================================================

    elements.append(
        Paragraph(
            'AUDITRA',
            title_style
        )
    )

    elements.append(
        Paragraph(
            'User Compliance Assessment Report',
            ParagraphStyle(
                'ST',
                parent=styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor(
                    '#1a1a2e'
                ),
                fontName='Helvetica-Bold',
                spaceAfter=4
            )
        ))

    elements.append(
        HRFlowable(
            width='100%',
            thickness=2,
            color=colors.HexColor(
                '#1a1a2e'
            ),
            spaceAfter=10
        )
    )

    # ========================================================
    # REPORT INFORMATION
    # ========================================================

    elements.append(
        section_header(
            'Report Information'
        )
    )

    elements.append(
        Spacer(1, 0.2 * cm)
    )

    elements.append(
        info_table([
            ['Report ID', report_id],
            [
                'Generated On',
                now.strftime(
                    '%d %b %Y — %I:%M %p'
                )
            ],
            [
                'Reporting Period',
                f'{period_start} – {period_end}'
            ],
            [
                'Generated By',
                'Compliance Officer'
            ],
            [
                'System',
                'Auditra — Automated GDPR Compliance Monitor'
            ],
        ])
    )

    elements.append(
        Spacer(1, 0.4 * cm)
    )

    # ========================================================
    # USER INFORMATION
    # ========================================================

    elements.append(
        section_header(
            '1. User Information'
        )
    )

    elements.append(
        Spacer(1, 0.2 * cm)
    )

    elements.append(
        info_table([
            ['User ID', user_id],
            ['Account Status', 'Active'],
            [
                'Access Level',
                (
                    'High Sensitivity'
                    if total_violations > 0
                    else 'Standard'
                )
            ],
            [
                'Total Logs Recorded',
                str(total_logs)
            ],
        ])
    )

    elements.append(
        Spacer(1, 0.4 * cm)
    )

    # ========================================================
    # COMPLIANCE SUMMARY
    # ========================================================

    elements.append(
        section_header(
            '2. Compliance Summary'
        )
    )

    elements.append(
        Spacer(1, 0.2 * cm)
    )

    elements.append(
        info_table([
            [
                'Total Logs Analyzed',
                str(total_logs)
            ],
            [
                'Total Violations',
                str(total_violations)
            ],
            [
                'Critical Violations',
                str(critical_count)
            ],
            [
                'High Violations',
                str(high_count)
            ],
            [
                'Medium Violations',
                str(medium_count)
            ],
            [
                'Low Violations',
                str(low_count)
            ],
            [
                'AI Anomalies Detected',
                str(anomaly_count)
            ],
            [
                'Average Risk Score',
                f'{avg_risk_pct}%'
            ],
            [
                'Compliance Score',
                f'{compliance_score}%'
            ],
            [
                'Current Risk Level',
                risk_level
            ],
        ])
    )

    elements.append(
        Spacer(1, 0.4 * cm)
    )

    # ========================================================
    # VIOLATION BREAKDOWN
    # ========================================================

    elements.append(
        section_header(
            '3. Violation Breakdown'
        )
    )

    elements.append(
        Spacer(1, 0.2 * cm)
    )

    if violations.exists():

        viol_data = [[
            'Timestamp',
            'GDPR Article',
            'Violation Type',
            'Severity',
            'Risk Score',
            'Status'
        ]]

        for v in violations[:20]:

            sev = v.rule.severity

            sev_color = {
                'CRITICAL': '#e53e3e',
                'HIGH': '#dd6b20',
                'MEDIUM': '#d69e2e',
                'LOW': '#38a169'
            }.get(
                sev,
                '#888888'
            )

            viol_data.append([
                v.detected_at.strftime(
                    '%d %b %Y — %I:%M %p'
                ),

                v.rule.gdpr_article,

                Paragraph(
                    (
                        v.reason[:45] + '...'
                        if len(v.reason) > 45
                        else v.reason
                    ),
                    ParagraphStyle(
                        'VR',
                        parent=styles['Normal'],
                        fontSize=7
                    )
                ),

                Paragraph(
                    f'<font color="{sev_color}">'
                    f'<b>{sev}</b>'
                    f'</font>',
                    ParagraphStyle(
                        'VS',
                        parent=styles['Normal'],
                        fontSize=8
                    )
                ),

                f'{int(v.risk_score * 100)}',

                v.status,
            ])

        viol_table = Table(
            viol_data,
            colWidths=[
                3.5 * cm,
                2.2 * cm,
                4.5 * cm,
                2 * cm,
                1.8 * cm,
                2 * cm
            ]
        )

        viol_table.setStyle(
            TableStyle([
                (
                    'BACKGROUND',
                    (0, 0),
                    (-1, 0),
                    colors.HexColor('#1a1a2e')
                ),
                (
                    'TEXTCOLOR',
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),
                (
                    'FONTNAME',
                    (0, 0),
                    (-1, 0),
                    'Helvetica-Bold'
                ),
                (
                    'FONTSIZE',
                    (0, 0),
                    (-1, 0),
                    8
                ),
                (
                    'ALIGN',
                    (0, 0),
                    (-1, -1),
                    'LEFT'
                ),
                (
                    'FONTNAME',
                    (0, 1),
                    (-1, -1),
                    'Helvetica'
                ),
                (
                    'FONTSIZE',
                    (0, 1),
                    (-1, -1),
                    8
                ),
                (
                    'ROWBACKGROUNDS',
                    (0, 1),
                    (-1, -1),
                    [
                        colors.HexColor('#fff0f0'),
                        colors.white
                    ]
                ),
                (
                    'GRID',
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor('#dee2e6')
                ),
                (
                    'PADDING',
                    (0, 0),
                    (-1, -1),
                    5
                ),
                (
                    'VALIGN',
                    (0, 0),
                    (-1, -1),
                    'TOP'
                ),
            ])
        )

        elements.append(
            viol_table
        )

    else:

        elements.append(
            Paragraph(
                'No violations recorded for this user.',
                normal
            )
        )

    elements.append(
        Spacer(1, 0.4 * cm)
    )

    # ========================================================
    # BEHAVIORAL ANALYSIS
    # ========================================================

    elements.append(
        section_header(
            '4. Behavioral Analysis'
        )
    )

    elements.append(
        Spacer(1, 0.2 * cm)
    )

    outside_hours = violations.filter(
        log__is_outside_hours=True
    ).count()

    high_sens = violations.filter(
        log__resource_sensitivity='HIGH'
    ).count()

    if outside_hours > 0:

        elements.append(
            Paragraph(
                f'The system identified '
                f'<b>{outside_hours}</b> violation(s) '
                f'occurring outside normal working hours '
                f'(before 8 AM or after 6 PM). '
                f'This pattern suggests unusual access '
                f'activity that deviates from standard '
                f'operational behavior.',
                normal
            )
        )

    if high_sens > 0:

        elements.append(
            Paragraph(
                f'<b>{high_sens}</b> violation(s) involved '
                f'high-sensitivity resources. Repeated access '
                f'to sensitive data without proper authorization '
                f'indicates potential data minimization and '
                f'access control issues under GDPR.',
                normal
            )
        )

    if anomaly_count > 0:

        elements.append(
            Paragraph(
                f'AI-based behavioral analysis flagged '
                f'<b>{anomaly_count}</b> anomalous event(s). '
                f'These activities were statistically unusual '
                f'compared to the baseline behavior profile '
                f'and warrant manual investigation.',
                normal
            )
        )

    if (
        outside_hours == 0
        and high_sens == 0
        and anomaly_count == 0
    ):

        elements.append(
            Paragraph(
                'No significant behavioral anomalies '
                'detected during the reporting period.',
                normal
            )
        )

    elements.append(
        Spacer(1, 0.4 * cm)
    )

    # ========================================================
    # AI ANOMALY DETECTION
    # ========================================================

    elements.append(
        section_header(
            '5. AI Anomaly Detection Findings'
        )
    )

    elements.append(
        Spacer(1, 0.2 * cm)
    )

    anomalies = violations.filter(
        is_anomaly=True
    )

    if anomalies.exists():

        elements.append(
            Paragraph(
                f'The Isolation Forest anomaly detection '
                f'engine analyzed the user\'s activity logs '
                f'and identified <b>{anomaly_count}</b> '
                f'statistically unusual event(s). These events '
                f'were flagged based on irregular access timing, '
                f'unusual resource sensitivity levels, and '
                f'abnormal action patterns.',
                normal
            )
        )

        elements.append(
            Spacer(1, 0.2 * cm)
        )

        anom_data = [[
            'Timestamp',
            'Resource',
            'Action',
            'Risk Score',
            'Status'
        ]]

        for v in anomalies[:10]:

            anom_data.append([
                v.detected_at.strftime(
                    '%d %b %Y %I:%M %p'
                ),
                v.log.resource_accessed,
                v.log.action,
                f'{int(v.risk_score * 100)}%',
                v.status
            ])

        anom_table = Table(
            anom_data,
            colWidths=[
                4 * cm,
                3.5 * cm,
                2.5 * cm,
                2.5 * cm,
                2.5 * cm
            ]
        )

        anom_table.setStyle(
            TableStyle([
                (
                    'BACKGROUND',
                    (0, 0),
                    (-1, 0),
                    colors.HexColor('#dd6b20')
                ),
                (
                    'TEXTCOLOR',
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),
                (
                    'FONTNAME',
                    (0, 0),
                    (-1, 0),
                    'Helvetica-Bold'
                ),
                (
                    'FONTSIZE',
                    (0, 0),
                    (-1, 0),
                    8
                ),
                (
                    'FONTNAME',
                    (0, 1),
                    (-1, -1),
                    'Helvetica'
                ),
                (
                    'FONTSIZE',
                    (0, 1),
                    (-1, -1),
                    8
                ),
                (
                    'ROWBACKGROUNDS',
                    (0, 1),
                    (-1, -1),
                    [
                        colors.HexColor('#fff8e1'),
                        colors.white
                    ]
                ),
                (
                    'GRID',
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor('#dee2e6')
                ),
                (
                    'PADDING',
                    (0, 0),
                    (-1, -1),
                    5
                ),
                (
                    'ALIGN',
                    (0, 0),
                    (-1, -1),
                    'LEFT'
                ),
            ])
        )

        elements.append(
            anom_table
        )

    else:

        elements.append(
            Paragraph(
                'No AI anomalies detected for this user '
                'during the reporting period.',
                normal
            )
        )

    elements.append(
        Spacer(1, 0.4 * cm)
    )

    # ========================================================
    # GDPR COMPLIANCE CHECKS
    # ========================================================

    elements.append(
        section_header(
            '6. GDPR Compliance Checks'
        )
    )

    elements.append(
        Spacer(1, 0.2 * cm)
    )

    has_art6 = violations.filter(
        rule__gdpr_article='Art. 6'
    ).exists()

    has_art5 = violations.filter(
        rule__gdpr_article='Art. 5'
    ).exists()

    has_art33 = violations.filter(
        rule__gdpr_article='Art. 33'
    ).exists()

    has_art25 = violations.filter(
        rule__gdpr_article='Art. 25'
    ).exists()

    has_art30 = violations.filter(
        rule__gdpr_article='Art. 30'
    ).exists()

    has_art7 = violations.filter(
        rule__gdpr_article='Art. 7'
    ).exists()

    def status_para(ok):

        color = (
            '#38a169'
            if ok
            else '#e53e3e'
        )

        text = (
            'Yes ✓'
            if ok
            else 'No ✗'
        )

        return Paragraph(
            f'<font color="{color}">'
            f'<b>{text}</b>'
            f'</font>',
            ParagraphStyle(
                'SP',
                parent=styles['Normal'],
                fontSize=9
            )
        )

    checks_data = [
        [
            'Compliance Check',
            'Status'
        ],
        [
            'Valid Consent / Lawful Basis Available',
            status_para(not has_art6)
        ],
        [
            'Unauthorized Processing Detected',
            status_para(
                has_art6 or has_art5
            )
        ],
        [
            'Excessive Data Collection',
            status_para(has_art5)
        ],
        [
            'Data Minimization Followed',
            status_para(not has_art5)
        ],
        [
            'Breach Reporting Delay',
            status_para(has_art33)
        ],
        [
            'Access Control Compliance',
            status_para(not has_art25)
        ],
        [
            'Record of Processing Available',
            status_para(not has_art30)
        ],
        [
            'Consent Withdrawn & Processing Stopped',
            status_para(not has_art7)
        ],
    ]

    checks_table = Table(
        checks_data,
        colWidths=[
            12 * cm,
            5 * cm
        ]
    )

    checks_table.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, 0),
                colors.HexColor('#1a1a2e')
            ),
            (
                'TEXTCOLOR',
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                'FONTNAME',
                (0, 0),
                (-1, 0),
                'Helvetica-Bold'
            ),
            (
                'FONTSIZE',
                (0, 0),
                (-1, 0),
                9
            ),
            (
                'FONTNAME',
                (0, 1),
                (0, -1),
                'Helvetica'
            ),
            (
                'FONTSIZE',
                (0, 1),
                (-1, -1),
                9
            ),
            (
                'ROWBACKGROUNDS',
                (0, 1),
                (-1, -1),
                [
                    colors.HexColor('#f8f9fa'),
                    colors.white
                ]
            ),
            (
                'GRID',
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor('#dee2e6')
            ),
            (
                'PADDING',
                (0, 0),
                (-1, -1),
                7
            ),
            (
                'VALIGN',
                (0, 0),
                (-1, -1),
                'MIDDLE'
            ),
        ])
    )

    elements.append(
        checks_table
    )

    elements.append(
        Spacer(1, 0.4 * cm)
    )

    # ========================================================
    # RISK ASSESSMENT
    # ========================================================

    elements.append(
        section_header(
            '7. Risk Assessment'
        )
    )

    elements.append(
        Spacer(1, 0.2 * cm)
    )

    risk_bg = {
        'HIGH': '#fff0f0',
        'MEDIUM': '#fff8e1',
        'LOW': '#f0fff4'
    }.get(
        risk_level,
        '#f8f9fa'
    )

    risk_text_color = {
        'HIGH': '#e53e3e',
        'MEDIUM': '#dd6b20',
        'LOW': '#38a169'
    }.get(
        risk_level,
        '#333'
    )

    risk_box = Table(
        [[
            Paragraph(
                f'Overall Risk Level: '
                f'<font color="{risk_text_color}">'
                f'<b>{risk_level}</b>'
                f'</font> '
                f'— Compliance Score: '
                f'<b>{compliance_score}%</b> '
                f'— Average Risk Score: '
                f'<b>{avg_risk_pct}%</b>',
                ParagraphStyle(
                    'RB',
                    parent=styles['Normal'],
                    fontSize=10
                )
            )
        ]],
        colWidths=[17 * cm]
    )

    risk_box.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, -1),
                colors.HexColor(risk_bg)
            ),
            (
                'GRID',
                (0, 0),
                (-1, -1),
                1,
                colors.HexColor(risk_text_color)
            ),
            (
                'PADDING',
                (0, 0),
                (-1, -1),
                10
            ),
        ])
    )

    elements.append(
        risk_box
    )

    elements.append(
        Spacer(1, 0.3 * cm)
    )

    elements.append(
        Paragraph(
            f'Based on rule-based compliance analysis '
            f'and AI-assisted anomaly detection, the overall '
            f'compliance risk for user <b>{user_id}</b> is '
            f'classified as '
            f'<font color="{risk_text_color}">'
            f'<b>{risk_level}</b>'
            f'</font>. A total of '
            f'<b>{total_violations}</b> violation(s) were '
            f'detected across <b>{total_logs}</b> analyzed '
            f'log entries.',
            normal
        )
    )

    elements.append(
        Spacer(1, 0.4 * cm)
    )

    # ========================================================
    # RECOMMENDED ACTIONS
    # ========================================================

    elements.append(
        section_header(
            '8. Recommended Actions'
        )
    )

    elements.append(
        Spacer(1, 0.2 * cm)
    )

    recommendations = []

    if critical_count > 0:

        recommendations.append(
            'Conduct immediate manual investigation '
            'of critical violations'
        )

    if has_art25:

        recommendations.append(
            'Review and update user access permissions '
            'and role assignments'
        )

    if outside_hours > 0:

        recommendations.append(
            'Investigate after-hours access activity '
            'and enforce access time controls'
        )

    if anomaly_count > 0:

        recommendations.append(
            'Perform detailed audit review of '
            'AI-flagged anomalous activities'
        )

    if has_art33:

        recommendations.append(
            'Ensure breach notification procedures '
            'meet the 72-hour reporting requirement'
        )

    if has_art6:

        recommendations.append(
            'Establish valid lawful basis for '
            'all processing activities'
        )

    if has_art30:

        recommendations.append(
            'Update Records of Processing Activities '
            'to include all detected operations'
        )

    if not recommendations:

        recommendations.append(
            'Continue monitoring — no immediate '
            'actions required'
        )

    recommendations.append(
        'Provide GDPR compliance awareness training '
        'to the user'
    )

    recommendations.append(
        'Schedule follow-up compliance review '
        'in 30 days'
    )

    rec_data = [
        [f'{i + 1}. {r}']
        for i, r in enumerate(
            recommendations
        )
    ]

    rec_table = Table(
        rec_data,
        colWidths=[17 * cm]
    )

    rec_table.setStyle(
        TableStyle([
            (
                'FONTNAME',
                (0, 0),
                (-1, -1),
                'Helvetica'
            ),
            (
                'FONTSIZE',
                (0, 0),
                (-1, -1),
                9
            ),
            (
                'ROWBACKGROUNDS',
                (0, 0),
                (-1, -1),
                [
                    colors.HexColor('#f8f9fa'),
                    colors.white
                ]
            ),
            (
                'GRID',
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor('#dee2e6')
            ),
            (
                'PADDING',
                (0, 0),
                (-1, -1),
                7
            ),
            (
                'TEXTCOLOR',
                (0, 0),
                (-1, -1),
                colors.HexColor('#1a1a2e')
            ),
        ])
    )

    elements.append(
        rec_table
    )

    elements.append(
        Spacer(1, 0.4 * cm)
    )

    # ========================================================
    # AUDIT TRAIL
    # ========================================================

    elements.append(
        section_header(
            '9. Audit Trail Reference'
        )
    )

    elements.append(
        Spacer(1, 0.2 * cm)
    )

    audit_data = [[
        'Event ID',
        'Log Reference',
        'Article',
        'Timestamp',
        'Status'
    ]]

    for i, v in enumerate(
        violations[:10]
    ):

        audit_data.append([
            f'EVT-{8800 + i}',
            f'LOG-{10400 + i}',
            v.rule.gdpr_article,
            v.detected_at.strftime(
                '%d %b %Y — %I:%M %p'
            ),
            v.status
        ])

    audit_table = Table(
        audit_data,
        colWidths=[
            2.5 * cm,
            3 * cm,
            2.5 * cm,
            5.5 * cm,
            3 * cm
        ]
    )

    audit_table.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, 0),
                colors.HexColor('#1a1a2e')
            ),
            (
                'TEXTCOLOR',
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                'FONTNAME',
                (0, 0),
                (-1, 0),
                'Helvetica-Bold'
            ),
            (
                'FONTSIZE',
                (0, 0),
                (-1, 0),
                8
            ),
            (
                'FONTNAME',
                (0, 1),
                (-1, -1),
                'Helvetica'
            ),
            (
                'FONTSIZE',
                (0, 1),
                (-1, -1),
                8
            ),
            (
                'ROWBACKGROUNDS',
                (0, 1),
                (-1, -1),
                [
                    colors.HexColor('#f8f9fa'),
                    colors.white
                ]
            ),
            (
                'GRID',
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor('#dee2e6')
            ),
            (
                'PADDING',
                (0, 0),
                (-1, -1),
                5
            ),
            (
                'ALIGN',
                (0, 0),
                (-1, -1),
                'LEFT'
            ),
        ])
    )

    elements.append(
        audit_table
    )

    elements.append(
        Spacer(1, 0.4 * cm)
    )

    # ========================================================
    # FINAL DECISION
    # ========================================================

    elements.append(
        HRFlowable(
            width='100%',
            thickness=2,
            color=colors.HexColor(
                '#1a1a2e'
            ),
            spaceAfter=8
        )
    )

    final_bg = (
        '#fff0f0'
        if risk_level == 'HIGH'
        else '#fff8e1'
        if risk_level == 'MEDIUM'
        else '#f0fff4'
    )

    final_color = (
        '#e53e3e'
        if risk_level == 'HIGH'
        else '#dd6b20'
        if risk_level == 'MEDIUM'
        else '#38a169'
    )

    if risk_level == 'HIGH':

        decision_text = (
            'Immediate review and corrective actions '
            'are recommended to prevent potential '
            'GDPR violations.'
        )

    elif risk_level == 'MEDIUM':

        decision_text = (
            'Monitoring should continue with '
            'periodic reviews.'
        )

    else:

        decision_text = (
            'No immediate actions required. '
            'Continue standard monitoring.'
        )

    final_box = Table(
        [[
            Paragraph(
                f'<b>Final Compliance Decision</b>'
                f'<br/><br/>'
                f'The analyzed activity for user '
                f'<b>{user_id}</b> indicates '
                f'<font color="{final_color}">'
                f'<b>{risk_level} compliance and '
                f'security risk</b>'
                f'</font>. '
                f'{decision_text}',
                ParagraphStyle(
                    'FD',
                    parent=styles['Normal'],
                    fontSize=9,
                    textColor=colors.HexColor(
                        '#1a1a2e'
                    )
                )
            )
        ]],
        colWidths=[17 * cm]
    )

    final_box.setStyle(
        TableStyle([
            (
                'BACKGROUND',
                (0, 0),
                (-1, -1),
                colors.HexColor(final_bg)
            ),
            (
                'GRID',
                (0, 0),
                (-1, -1),
                1,
                colors.HexColor(final_color)
            ),
            (
                'PADDING',
                (0, 0),
                (-1, -1),
                12
            ),
        ])
    )

    elements.append(
        final_box
    )

    elements.append(
        Spacer(1, 0.3 * cm)
    )

    elements.append(
        Paragraph(
            'This report was generated by Auditra — '
            'Automated GDPR Compliance Monitoring System. '
            'Confidential — for internal use only.',
            subtitle_style
        )
    )

    doc.build(elements)

    return response
