import os, sys
# ensure project root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE','auto_backup_inventory.settings')
import django
django.setup()
from django.test import Client

c=Client()
resp=c.get('/operations-dashboard/')
print('STATUS', resp.status_code)
print(resp.content.decode('utf-8'))
