from django.urls import path, include, re_path, reverse_lazy
from django.contrib.auth import views as auth_views
from rest_framework_simplejwt.views import TokenBlacklistView, TokenObtainPairView, TokenRefreshView

from . import views
from .forms import CustomPasswordResetForm
#urlpatterns for the inventory app, including API endpoints, user authentication, and dashboard views
#some features are not yet usin api but will be in the future, so we are keeping the api endpoints for now
urlpatterns = [
    # API endpoints for dashboard summary and inventory lookups
    path('', views.index, name='index'),
    path('api/dashboard-summary/', views.api_dashboard_summary, name='api-dashboard-summary'),
    path('api/tapes/', views.api_tape_list, name='api-tapes'),
    path('api/shipments/', views.api_shipment_list, name='api-shipments'),
    path('api/audit-logs/', views.api_audit_log_list, name='api-audit-logs'),
    re_path(r'^(?:api/)?investigation/(?P<exception_id>[^/]+)/?$', views.exception_investigation_view, name='exception-investigation'),
    re_path(r'^investigation-dashboard/(?:(?P<exception_id>[^/]+)/)?$', views.investigation_dashboard_page, name='investigation-dashboard'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('api/features/<str:feature_key>/', views.api_feature_navigation, name='api-feature-navigation'),
    path('features/<str:feature_key>/', views.feature_module, name='feature-module'),
    path('apis/dashboard-summary/', views.api_dashboard_summary, name='apis-dashboard-summary'),
    path('apis/tapes/', views.api_tape_list, name='apis-tapes'),
    path('apis/shipments/', views.api_shipment_list, name='apis-shipments'),
    path('apis/audit-logs/', views.api_audit_log_list, name='apis-audit-logs'),
    # User authentication and dashboard views
    path('signin/', views.signin, name='signin'),
    path('signout/', views.signout, name='signout'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        form_class=CustomPasswordResetForm,
        template_name='password_reset.html',
        email_template_name='password_reset_email.html',
        subject_template_name='password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done')
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete')
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),
    path('initiated-reconciliation-request/', views.initiate_reconciliation_request, name='initiate-reconciliation-request'),
    path('close-exception/', views.close_exception, name='close-exception'),
    path('approve-close-exception/<uuid:close_request_id>/', views.approve_close_exception, name='approve-close-exception'),
    # Dashboard and feature-specific views
    path('dashboard/', views.dashboard, name='dashboard'),
    path('backup-dashboard/nav/<str:signed_token>/', views.backup_dashboard_navigation, name='backup-dashboard-navigation'),
    path('operations-dashboard/nav/<str:signed_token>/', views.operations_dashboard_navigation, name='operations-dashboard-navigation'),
    path('backup-dashboard/', views.backup_dashboard, name='backup-dashboard'),
    path('operations-dashboard/', views.operations_dashboard, name='operations-dashboard'),
    path('warehouse-operations-dashboard/', views.warehouse_operations_dashboard, name='warehouse-operations-dashboard'),
    path('supreme-approver-dashboard/', views.supreme_approver_dashboard, name='supreme-approver-dashboard'),
    path('approvals/<uuid:approval_id>/review/', views.approval_review, name='approval-review'),
    path('operations-dashboard/start-shipment-request/', views.start_shipment_request, name='start-shipment-request'),
    # Additional operations dashboard views
    path('operations-dashboard/exception/<uuid:pk>/', views.exception_detail, name='exception-detail'),
    path('shipment-approvals/', views.shipment_approvals, name='shipment-approvals'),
    path('shipment-approvals/<uuid:shipment_pk>/', views.shipment_detail, name='shipment-detail'),
    path('shipment-approvals/<uuid:shipment_pk>/request-return/', views.request_return_shipment, name='request-return-shipment'),
    path('shipment-approvals/<uuid:shipment_pk>/courier-response/', views.courier_return_response, name='courier-return-response'),
    path('shipment-approvals/<uuid:shipment_pk>/receive-return/', views.receive_return_shipment, name='receive-return-shipment'),
    path('shipment-approvals/<uuid:shipment_pk>/history/', views.approval_history, name='approval-history'),
    path('courier-dashboard/', views.courier_dashboard, name='courier-dashboard'),
    path('courier/assigned-shipments/', views.assigned_shipments, name='assigned-shipments'),
    path('courier/manifest/<uuid:shipment_pk>/', views.manifest_detail, name='manifest-detail'),
    path('courier/pickup-confirmation/<uuid:shipment_pk>/', views.pickup_confirmation, name='pickup-confirmation'),
    path('courier/delivery-confirmation/<uuid:shipment_pk>/', views.delivery_confirmation, name='delivery-confirmation'),
    path('courier/return-shipments/', views.return_shipments, name='return-shipments'),
    path('courier/incident-management/', views.incident_management, name='incident-management'),
    path('courier/activity-log/', views.activity_log, name='activity-log'),
    path('reconciliation-reports/', views.reconciliation_reports, name='reconciliation-reports'),
    path('reconciliation-reports/<uuid:pk>/', views.reconciliation_report_detail, name='reconciliation-report-detail'),
    path('tapes/add/', views.add_tape, name='add-tape'),
    path('auditor-dashboard/', views.auditor_dashboard, name='auditor-dashboard'),
    path('auditor-dashboard/audit-logs/', views.audit_logs_view, name='auditor-audit-logs'),
    path('auditor-dashboard/reports/', views.compliance_reports_view, name='auditor-reports'),
    path('auditor-dashboard/exceptions/', views.exception_review_view, name='auditor-exceptions'),
    path('auditor-dashboard/shipments/', views.shipment_compliance_view, name='auditor-shipments'),
    path('auditor-dashboard/retention/', views.retention_compliance_view, name='auditor-retention'),
    path('auditor-dashboard/reconciliation/', views.reconciliation_review_view, name='auditor-reconciliation'),
    path('approval-form-preview/<uuid:shipment_pk>/', views.approval_form_preview, name='approval-form-preview'),
    path('backup-dashboard/awaiting-release/', views.awaiting_release, name='awaiting-release'),
    path('reports/', include('inventory.reports_urls')),
]
