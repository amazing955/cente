import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_backup_inventory.settings')
import django

django.setup()

from django.test import Client
from inventory.models import CustomUser

user = CustomUser.objects.filter(is_active=True).first()
print('USER', user and user.username, 'id', user and user.pk)
if not user:
    raise SystemExit('No active user found in the database')

client = Client()
client.force_login(user)
resp = client.get('/backup-dashboard/')
print('STATUS', resp.status_code)
print('TEMPLATE', getattr(resp, 'template_name', None))
print('CONTENT START')
print(resp.content[:3000].decode('utf-8', errors='replace'))
