from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('signin/', views.signin, name='signin'),
    path('signout/', views.signout, name='signout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('backup-dashboard/', views.backup_dashboard, name='backup-dashboard'),
    path('operations-dashboard/', views.operations_dashboard, name='operations-dashboard'),
    path('shipment-approvals/', views.shipment_approvals, name='shipment-approvals'),
    path('shipment-approvals/<uuid:shipment_pk>/', views.shipment_detail, name='shipment-detail'),
    path('shipment-approvals/<uuid:shipment_pk>/history/', views.approval_history, name='approval-history'),
    path('reconciliation-reports/', views.reconciliation_reports, name='reconciliation-reports'),
    path('reconciliation-reports/<uuid:pk>/', views.reconciliation_report_detail, name='reconciliation-report-detail'),
    path('tapes/add/', views.add_tape, name='add-tape'),
]
