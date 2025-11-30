import requests
import json

url = "http://127.0.0.1:5000/chat"
headers = {"Content-Type": "application/json"}

# Query likely to be in an Ayurvedic text
data = {"message": "What are the symptoms of Vata imbalance?"}

print(f"Sending query: {data['message']}")
try:
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        print("\nResponse:")
        print(f"Source: {result.get('source')}")
        print(f"Answer: {result.get('response')[:200]}...") # Print first 200 chars
    else:
        print(f"Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
