import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_backup_inventory.settings')
import django
django.setup()
from django.test import Client
from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

user = get_user_model().objects.create_user(username='drflowcheck3', email='drflowcheck3@example.com', password='Pass1234!', role='user')
g = Group.objects.get_or_create(name='DR Team')[0]
user.groups.add(g)
with override_settings(ALLOWED_HOSTS=['testserver','localhost','127.0.0.1']):
    c = Client()
    response1 = c.post('/signin/', {'username':'drflowcheck3','password':'Pass1234!'})
    print('step1 status', response1.status_code)
    print('step1 pending', c.session.get('pending_2fa_user_id'))
    otp = c.session.get('pending_2fa_otp')
    print('step1 otp', otp)
    response2 = c.post('/signin/', {'otp_code': otp})
    print('step2 status', response2.status_code)
    print('step2 url', response2.url if hasattr(response2, 'url') else None)
    print('step2 location', response2.get('Location'))
    print('step2 content start', response2.content[:2000].decode('utf-8', errors='ignore'))
