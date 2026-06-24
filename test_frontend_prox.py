import requests

BASE = "http://localhost:5173"

try:
    r = requests.post(f"{BASE}/api/sessions/start", json={"session_type": "booking", "channel": "simulated"})
    print("Status:", r.status_code)
    print("Body:", r.text[:200])
except Exception as e:
    print("Error:", e)