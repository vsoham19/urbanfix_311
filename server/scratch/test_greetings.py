import requests
import json

url = "http://127.0.0.1:8000/iot/chat"

print("=========================================")
print("TESTING FRIENDLY GREETINGS & METADATA INQUIRY...")
payload_greeting = {
    "mode": "general",
    "message": "Hi, hello! What is this sewerage chatbot and what can you do?",
    "history": []
}
try:
    r = requests.post(url, json=payload_greeting, timeout=15)
    print("Status Code:", r.status_code)
    data = r.json()
    print("Source:", data.get("source"))
    print("Message:")
    print(data.get("message"))
except Exception as e:
    print("FAILED:", e)
