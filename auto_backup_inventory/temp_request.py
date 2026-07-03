import urllib.request, urllib.error
import traceback
url = 'http://127.0.0.1:8000/operations-dashboard/'
try:
    with urllib.request.urlopen(url) as r:
        print(r.read().decode('utf-8')[:2000])
except urllib.error.HTTPError as e:
    print(e.code)
    print(e.read().decode('utf-8')[:2000])
except Exception:
    traceback.print_exc()
