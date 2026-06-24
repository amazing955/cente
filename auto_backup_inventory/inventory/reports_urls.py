from django.urls import path
from . import reports_views as views

urlpatterns = [
    path('', views.reports_dashboard, name='reports-dashboard'),
    path('general/', views.general_report, name='general-report'),
    path('detail/<uuid:pk>/', views.report_detail, name='report-detail'),
    path('export/', views.report_export, name='report-export'),
]
