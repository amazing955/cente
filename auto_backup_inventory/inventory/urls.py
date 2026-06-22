from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('signin/', views.signin, name='signin'),
    path('signout/', views.signout, name='signout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('backup-dashboard/', views.backup_dashboard, name='backup-dashboard'),
    path('operations-dashboard/', views.operations_dashboard, name='operations-dashboard'),
    path('reconciliation-reports/', views.reconciliation_reports, name='reconciliation-reports'),
    path('reconciliation-reports/<int:pk>/', views.reconciliation_report_detail, name='reconciliation-report-detail'),
    path('tapes/add/', views.add_tape, name='add-tape'),
]
