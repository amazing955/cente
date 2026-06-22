import sys
import os
print('sys.executable=', sys.executable)
print('cwd=', os.getcwd())
try:
    import django
    print('django version=', django.get_version())
except Exception as e:
    print('django import failed:', type(e).__name__, e)
