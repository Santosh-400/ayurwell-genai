import requests
import json
import time

url = "http://127.0.0.1:5000/chat"
headers = {"Content-Type": "application/json"}

def send_msg(msg):
    print(f"\nUser: {msg}")
    data = {"message": msg}
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            print(f"AyurWell: {result.get('response')[:100]}...")
            return result.get('response')
        else:
            print(f"Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None

# 1. Set context
send_msg("Hi, I have a Vata imbalance.")
time.sleep(1)

# 2. Ask follow-up that relies on context
response = send_msg("What foods should I avoid for this?")

if response and "Vata" in response:
    print("\nSUCCESS: Bot remembered the context (Vata).")
else:
    print("\nFAILURE: Bot did not explicitly mention Vata in follow-up.")
