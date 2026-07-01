from django.urls import path, include
from . import views
#urlpatterns for the inventory app, including API endpoints, user authentication, and dashboard views
#some features are not yet usin api but will be in the future, so we are keeping the api endpoints for now
urlpatterns = [
    # API endpoints for dashboard summary and inventory lookups
    path('', views.index, name='index'),
    path('api/dashboard-summary/', views.api_dashboard_summary, name='api-dashboard-summary'),
    path('api/tapes/', views.api_tape_list, name='api-tapes'),
    path('api/shipments/', views.api_shipment_list, name='api-shipments'),
    path('api/audit-logs/', views.api_audit_log_list, name='api-audit-logs'),
    path('api/features/<str:feature_key>/', views.api_feature_navigation, name='api-feature-navigation'),
    path('apis/dashboard-summary/', views.api_dashboard_summary, name='apis-dashboard-summary'),
    path('apis/tapes/', views.api_tape_list, name='apis-tapes'),
    path('apis/shipments/', views.api_shipment_list, name='apis-shipments'),
    path('apis/audit-logs/', views.api_audit_log_list, name='apis-audit-logs'),
    # User authentication and dashboard views
    path('signin/', views.signin, name='signin'),
    path('signout/', views.signout, name='signout'),
    # Dashboard and feature-specific views
    path('dashboard/', views.dashboard, name='dashboard'),
    path('backup-dashboard/', views.backup_dashboard, name='backup-dashboard'),
    path('operations-dashboard/', views.operations_dashboard, name='operations-dashboard'),
    path('operations-dashboard/start-shipment-request/', views.start_shipment_request, name='start-shipment-request'),
    # Additional operations dashboard views
    path('operations-dashboard/exception/<uuid:pk>/', views.exception_detail, name='exception-detail'),
    path('shipment-approvals/', views.shipment_approvals, name='shipment-approvals'),
    path('shipment-approvals/<uuid:shipment_pk>/', views.shipment_detail, name='shipment-detail'),
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
    path('reports/', include('inventory.reports_urls')),
]
