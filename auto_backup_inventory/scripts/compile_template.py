import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','auto_backup_inventory.settings')
import django
django.setup()
from django.template import loader, TemplateSyntaxError
try:
    tpl = loader.get_template('operations_dashboard.html')
    print('Template compiled OK')
except TemplateSyntaxError as e:
    print('TemplateSyntaxError:', e)
except Exception as e:
    print('Other error:', type(e), e)
