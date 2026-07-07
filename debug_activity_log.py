import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_backup_inventory.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from inventory.models import Shipment, ShipmentTransportEvent, CourierProfile

User = get_user_model()

print('Starting activity log debug')

courier_group, _ = Group.objects.get_or_create(name='Courier')
user, created = User.objects.get_or_create(
    username='debug_activity_log_courier',
    defaults={
        'email': 'debug_activity_log_courier@example.com',
        'first_name': 'Debug',
        'last_name': 'Courier',
    }
)
if created:
    user.set_password('pass1234')
    user.save()
    user.groups.add(courier_group)
else:
    if not user.groups.filter(name='Courier').exists():
        user.groups.add(courier_group)

profile, _ = CourierProfile.objects.get_or_create(
    user=user,
    defaults={
        'courier_id': 'CR-DEBUG-001',
        'full_name': 'Debug Courier',
        'phone_number': '0000000000',
        'email': 'debug_activity_log_courier@example.com',
        'vehicle_number': 'V-DEBUG',
        'active_status': True,
    }
)

shipment, _ = Shipment.objects.get_or_create(
    shipment_type='Off-Site Transfer',
    source_location='Nairobi Branch',
    destination_location='Kampala Branch',
    status='Approved',
    releasing_custodian='Ops User',
)

ShipmentTransportEvent.objects.get_or_create(
    shipment=shipment,
    courier=profile,
    event_type='Picked Up',
    defaults={'comments': 'Picked up for debug'},
)

client = Client()
logged_in = client.login(username='debug_activity_log_courier', password='pass1234')
print('Logged in:', logged_in)
response = client.get('/courier/activity-log/')
print('Status code:', response.status_code)
print('Content length:', len(response.content))
print('Rendered content snippet:\n', response.content[:400].decode('utf-8', errors='replace'))

if response.status_code >= 500:
    print('Server error.')
    print(response.content.decode('utf-8', errors='replace'))
