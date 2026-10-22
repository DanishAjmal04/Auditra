from django.urls import path
from . import views

from compliance.views import LogoutView


urlpatterns = [

    # ==================================================
    # GENERAL
    # ==================================================

    path(
        'stats/',
        views.stats,
        name='stats'
    ),

    path(
        'logs/',
        views.logs_list,
        name='logs-list'
    ),

    path(
        'violations/',
        views.violations_list,
        name='violations-list'
    ),

    path(
        'violations/<uuid:pk>/status/',
        views.violation_update,
        name='violation-update'
    ),

    path(
        'simulate/',
        views.simulate,
        name='simulate'
    ),


    # ==================================================
    # RULES
    # ==================================================

    path(
        'rules/',
        views.rules_list,
        name='rules-list'
    ),

    path(
        'rules/create/',
        views.rule_create,
        name='rule-create'
    ),

    path(
        'rules/<uuid:pk>/',
        views.rule_update,
        name='rule-update'
    ),


    # ==================================================
    # USER ACTIVITY
    # ==================================================

    path(
        'users/',
        views.users_list,
        name='users-list'
    ),

    path(
        'user-activity/',
        views.user_activity,
        name='user-activity'
    ),


    # ==================================================
    # CONSENT
    # ==================================================

    path(
        'consent-records/',
        views.consent_records,
        name='consent-records'
    ),

    path(
        'consent-records/<uuid:pk>/',
        views.consent_record_update,
        name='consent-record-update'
    ),

    path(
        'dpo/',
        views.dpo_designation,
        name='dpo-designation'
    ),

    path(
        'processing-activities/',
        views.processing_activities,
        name='processing-activities'
    ),

    path(
        'processing-activities/<uuid:pk>/',
        views.processing_activity_detail,
        name='processing-activity-detail'
    ),


    # ==================================================
    # DATA SUBJECT RIGHTS
    # ==================================================

    path(
        'deletion-requests/',
        views.deletion_requests,
        name='deletion-requests'
    ),

    path(
        'deletion-requests/<uuid:pk>/',
        views.deletion_request_update,
        name='deletion-request-update'
    ),

    path(
        'subject-access-requests/',
        views.subject_access_requests,
        name='subject-access-requests'
    ),

    path(
        'subject-access-requests/<uuid:pk>/',
        views.subject_access_request_update,
        name='subject-access-request-update'
    ),


    # ==================================================
    # REPORTS
    # ==================================================

    path(
        'reports/',
        views.reports,
        name='reports'
    ),

    path(
        'generate-pdf/',
        views.generate_pdf,
        name='generate-pdf'
    ),

    path(
        'user-pdf/<str:user_id>/',
        views.generate_user_pdf,
        name='generate-user-pdf'
    ),

    path(
        'ingest/',
        views.ingest_logs,
        name='ingest-logs'
    ),


    # ==================================================
    # ADMIN
    # ==================================================

    path(
        'admin/stats/',
        views.admin_stats,
        name='admin-stats'
    ),

    path(
        'admin/users/',
        views.admin_users,
        name='admin-users'
    ),

    path(
        'admin/users/create/',
        views.admin_user_create,
        name='admin-user-create'
    ),

    path(
        'admin/users/<int:pk>/',
        views.admin_user_update,
        name='admin-user-update'
    ),

    path(
        'admin/health/',
        views.admin_health,
        name='admin-health'
    ),
]
