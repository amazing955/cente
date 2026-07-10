import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_backup_inventory.settings')
import django
django.setup()
from django.test import Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()
username = 'dbg-backup-admin2'
email = 'dbg-backup-admin2@example.com'
User.objects.filter(username=username).delete()
u = User.objects.create_superuser(username=username, email=email, password='StrongPass123!')
with override_settings(ALLOWED_HOSTS=['127.0.0.1','localhost','testserver']):
    client = Client(HTTP_HOST='127.0.0.1')
    client.force_login(u)
    response = client.get(reverse('backup-dashboard'))
    print('status', response.status_code)
    print(response.content.decode('utf-8', errors='ignore')[:4000])
