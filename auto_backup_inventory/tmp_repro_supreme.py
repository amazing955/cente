import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_backup_inventory.settings')
import django
django.setup()
from django.test import Client
from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

User = get_user_model()
u = User.objects.create_user(username='dbg-supreme3', email='dbg-supreme3@example.com', password='StrongPass123!')
g = Group.objects.get_or_create(name='Supreme Approver')[0]
u.groups.add(g)

with override_settings(ALLOWED_HOSTS=['127.0.0.1','localhost','testserver']):
    c = Client(HTTP_HOST='127.0.0.1')
    c.force_login(u)
    response = c.get(reverse('supreme-approver-dashboard'))
    print('STATUS', response.status_code)
    print(response.content[:8000].decode('utf-8', errors='ignore'))
