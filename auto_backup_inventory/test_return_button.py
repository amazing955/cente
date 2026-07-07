import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_backup_inventory.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse

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
print("TESTING 'RETURN TAPE' BUTTON")
print("="*60)

# Get operations dashboard to see if there are shipments
response = client.get('/operations-dashboard/')
if response.status_code == 200:
    print("\n✓ Operations Dashboard loaded successfully")
    
    # Try to find a shipment in the custody governance section
    from inventory.models import Shipment
    shipments = Shipment.objects.all()
    
    if shipments.exists():
        shipment = shipments.first()
        print(f"\n✓ Found shipment: {shipment.shipment_id} (pk={shipment.pk})")
        
        # Get the correct URL using reverse
        correct_url = reverse('shipment-detail', args=[shipment.pk])
        partial_url = f"{correct_url}?partial=1"
        
        print(f"\nCorrect URL: {correct_url}")
        print(f"Partial URL: {partial_url}")
        
        # Test the Return Tape link (shipment-detail with partial=1)
        print(f"\nTesting {partial_url}")
        try:
            response = client.get(partial_url)
            print(f"✓ Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"\n✗ Error Response:")
                print(response.content.decode()[:1000])
        except Exception as e:
            print(f"✗ Exception: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("\n✗ No shipments found in database")
else:
    print(f"\n✗ Dashboard load failed: {response.status_code}")
