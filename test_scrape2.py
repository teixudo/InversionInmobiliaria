import curl_cffi
from curl_cffi import requests

url = "https://www.idealista.com/inmueble/104278456/"
try:
    for imp in ["chrome120", "safari15_5", "chrome116"]:
        r = requests.get(url, impersonate=imp, timeout=10)
        print(f"{imp} Status: {r.status_code}")
except Exception as e:
    print("Error:", e)
