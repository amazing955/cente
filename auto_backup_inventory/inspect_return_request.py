import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_backup_inventory.settings')
django.setup()

from django.contrib.auth import get_user_model
from inventory.models import Shipment, CourierProfile
from django.test import Client
from django.conf import settings
from django.urls import reverse

if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

User = get_user_model()
client = Client()

user = User.objects.filter(username='testadmin').first()
if not user:
    user = User.objects.create_superuser('testadmin', 'test@example.com', 'testpass123')
client.login(username='testadmin', password='testpass123')

print('=== Courier profiles ===')
for profile in CourierProfile.objects.all():
    print(profile.pk, profile.full_name, profile.active_status, profile.user_id)

courier_group = None
from django.contrib.auth.models import Group
courier_group = Group.objects.filter(name__iexact='Courier').first()
print('Courier group exists:', bool(courier_group))
if courier_group:
    print('Courier users in group:', list(get_user_model().objects.filter(groups=courier_group).values_list('username', flat=True)))

shipment = Shipment.objects.exclude(status__in=['Cancelled', 'Rejected', 'Completed']).first()
print('Eligible shipment:', shipment and shipment.pk, shipment and shipment.status)
if shipment:
    url = reverse('request-return-shipment', args=[shipment.pk])
    print('URL:', url)
    response = client.get(url)
    print('GET status:', response.status_code)
    print('Has form errors:', hasattr(response, 'context') and response.context and response.context['return_form'].errors)
    print('HTML snippet:', response.content.decode()[:1200])

    print('Submitting empty form...')
    response2 = client.post(url, {'courier': '', 'comments': ''})
    print('POST status:', response2.status_code)
    print('Form errors after POST:', response2.context and response2.context['return_form'].errors)
    print('POST HTML snippet:', response2.content.decode()[:1200])
