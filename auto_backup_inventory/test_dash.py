import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_backup_inventory.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.conf import settings

# Add testserver to ALLOWED_HOSTS for testing
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

User = get_user_model()

# Test authenticated request
client = Client()
print("Attempting login...")
logged_in = client.login(username='testadmin', password='testpass123')
print(f"Login successful: {logged_in}")

try:
    print("Requesting /operations-dashboard/...")
    response = client.get('/operations-dashboard/')
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Response content: {response.content[:500]}")
    else:
        print(f"Response length: {len(response.content)}")
except Exception as e:
    import traceback
    print(f"Exception: {type(e).__name__}")
    traceback.print_exc()

# Also test backup-dashboard
try:
    print("\nRequesting /backup-dashboard/?show_shipments...")
    response = client.get('/backup-dashboard/?show_shipments')
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Response content: {response.content[:500]}")
    else:
        print(f"Response length: {len(response.content)}")
except Exception as e:
    import traceback
    print(f"Exception: {type(e).__name__}")
    traceback.print_exc()
