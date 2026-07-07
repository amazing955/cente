import os
import django
from django.db.models import Q

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_backup_inventory.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from inventory.models import Shipment, ShipmentTransportEvent, ShipmentException, CourierProfile

User = get_user_model()

print('project root:', os.getcwd())

courier_group, _ = Group.objects.get_or_create(name='Courier')
user, created = User.objects.get_or_create(
    username='debug_act_courier',
    defaults={
        'email': 'debug_act_courier@example.com',
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
        'email': 'debug_act_courier@example.com',
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

# inspect current existing transport events with null fields
null_date_count = ShipmentTransportEvent.objects.filter(event_date__isnull=True).count()
null_time_count = ShipmentTransportEvent.objects.filter(event_time__isnull=True).count()
print('null event_date count:', null_date_count)
print('null event_time count:', null_time_count)

# inspect any record with missing date/time values
for e in ShipmentTransportEvent.objects.filter(Q(event_date__isnull=True) | Q(event_time__isnull=True))[:10]:
    print('event', e.id, e.shipment_id, e.event_type, e.event_date, e.event_time)

# Now try to get activity log via Client with correct host
client = Client(HTTP_HOST='127.0.0.1')
logged_in = client.login(username='debug_act_courier', password='pass1234')
print('logged_in', logged_in)
response = client.get('/courier/activity-log/')
print('status code', response.status_code)
print('content snippet:', response.content[:400].decode('utf-8', errors='replace'))
