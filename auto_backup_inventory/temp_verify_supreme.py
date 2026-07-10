import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_backup_inventory.settings')
import django
django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()
username = 'dbg-supreme5'
email = 'dbg-supreme5@example.com'
User.objects.filter(username=username).delete()
u = User.objects.create_superuser(username=username, email=email, password='StrongPass123!')
client = Client()
client.force_login(u)
response = client.get(reverse('supreme-approver-dashboard'))
print('status=', response.status_code)
print('contains_title=', 'Enterprise Banking Approval Center' in response.content.decode('utf-8', errors='ignore'))
