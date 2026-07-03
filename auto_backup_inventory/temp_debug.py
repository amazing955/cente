import os
import sys
import django

# ensure project root is on path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_backup_inventory.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.filter(username='debug-user').first() or User.objects.filter(is_superuser=True).first()
print('user', user)
if not user:
    raise SystemExit('No user available for auth')
client = Client()
client.force_login(user)
resp = client.get('/operations-dashboard/')
print('status', resp.status_code)
print('redirect', getattr(resp, 'url', None))
print(resp.content.decode('utf-8', errors='replace')[:8000])
