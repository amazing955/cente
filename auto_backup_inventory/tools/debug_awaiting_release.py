from django.test import RequestFactory
from django.contrib.auth import get_user_model
from inventory import views
from django.db import transaction

User = get_user_model()

# Ensure we have a valid superuser object
u = User.objects.filter(is_superuser=True).first()
if not u:
    # create minimal user with required fields
    u = User(username='__tmp_admin__', is_superuser=True, is_staff=True)
    u.set_password('password')
    u.save()

req = RequestFactory().get('/backup-dashboard/awaiting-release/')
req.user = u

try:
    resp = views.awaiting_release(req)
    print('Response:', type(resp))
except Exception:
    import traceback, sys
    traceback.print_exc()
    sys.exit(1)
