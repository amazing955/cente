from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('signin/', views.signin, name='signin'),
    path('signout/', views.signout, name='signout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('backup-dashboard/', views.backup_dashboard, name='backup-dashboard'),
    path('operations-dashboard/', views.operations_dashboard, name='operations-dashboard'),
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
]
