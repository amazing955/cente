import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_backup_inventory.settings')
import django
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
from django.test.utils import override_settings

user = get_user_model().objects.filter(is_superuser=True).first()
if not user:
    raise SystemExit('No superuser found')

with override_settings(ALLOWED_HOSTS=['127.0.0.1','localhost','testserver']):
    client = Client(HTTP_HOST='127.0.0.1')
    client.force_login(user)
    response = client.get('/operations-dashboard/')
    print('STATUS', response.status_code)
    print('TEMPLATE', response.templates[-1].name if response.templates else None)
    if response.status_code >= 500:
        print(response.content.decode('utf-8', 'ignore')[:4000])
