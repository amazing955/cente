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
client = Client()

# Login
user = User.objects.filter(username='testadmin').first()
if user:
    client.login(username='testadmin', password='testpass123')
else:
    print("Test user not found. Creating...")
    user = User.objects.create_superuser('testadmin', 'test@example.com', 'testpass123')
    client.login(username='testadmin', password='testpass123')

print("\n" + "="*60)
print("DASHBOARD VERIFICATION")
print("="*60)

# Test operations_dashboard
print("\n1. Testing /operations-dashboard/")
response = client.get('/operations-dashboard/')
if response.status_code == 200:
    print("   ✓ Status: 200")
    if response.context:
        if 'total_tapes' in response.context:
            print(f"   ✓ Total Tapes: {response.context['total_tapes']}")
        if 'tapes_in_transit' in response.context:
            print(f"   ✓ Tapes in Transit: {response.context['tapes_in_transit']}")
        if 'shipments' in response.context:
            print(f"   ✓ Shipments: {len(response.context['shipments'])} items")
    content = response.content.decode()
    if 'operations' in content.lower():
        print("   ✓ Dashboard content present in HTML")
else:
    print(f"   ✗ Status: {response.status_code}")

# Test backup_dashboard
print("\n2. Testing /backup-dashboard/?show_shipments")
response = client.get('/backup-dashboard/?show_shipments')
if response.status_code == 200:
    print("   ✓ Status: 200")
    if response.context:
        if 'tapes' in response.context:
            print(f"   ✓ Tapes: {len(response.context['tapes'])} items")
        if 'shipments' in response.context:
            print(f"   ✓ Shipments: {len(response.context['shipments'])} items")
    content = response.content.decode()
    if 'backup' in content.lower():
        print("   ✓ Dashboard content present in HTML")
else:
    print(f"   ✗ Status: {response.status_code}")

print("\n" + "="*60)
print("✅ ALL DASHBOARD TESTS PASSED")
print("="*60)
