import curl_cffi
from curl_cffi import requests

url = "https://www.idealista.com/inmueble/104278456/"
try:
    print(f"curl_cffi version: {curl_cffi.__version__}")
    r = requests.get(url, impersonate="chrome110", timeout=15)
    print("Status:", r.status_code)
    print("Title in HTML:", "<title>" in r.text, r.text[:200])
except Exception as e:
    print("Error:", e)
