import os, sys, traceback
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE','auto_backup_inventory.settings')
import django
django.setup()
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

from inventory import views

User = get_user_model()
user = User.objects.filter(is_superuser=True).first()
created_temp = False
if not user:
    user = User.objects.create_superuser('tempadmin', 'tempadmin@example.com', 'TempPass123')
    created_temp = True

rf = RequestFactory()
req = rf.get('/operations-dashboard/')
req.user = user

try:
    resp = views.operations_dashboard(req)
    print('RESPONSE TYPE:', type(resp))
    if hasattr(resp, 'status_code'):
        print('STATUS CODE:', resp.status_code)
    if hasattr(resp, 'content'):
        print(resp.content.decode('utf-8')[:2000])
except Exception:
    traceback.print_exc()
finally:
    if created_temp:
        try:
            user.delete()
        except Exception:
            pass
