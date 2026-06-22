from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('signin/', views.signin, name='signin'),
    path('signout/', views.signout, name='signout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('backup-dashboard/', views.backup_dashboard, name='backup-dashboard'),
    path('tapes/add/', views.add_tape, name='add-tape'),
]
