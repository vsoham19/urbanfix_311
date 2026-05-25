import os
from dotenv import load_dotenv
from groq import Groq

# Load root .env
print("--- Loading root .env ---")
load_dotenv(dotenv_path="../.env")
root_key = os.getenv("groq_api") or os.getenv("GROQ_API_KEY")
print("Root key:", root_key[:20] if root_key else "None")

# Reset environment
os.environ.pop("GROQ_API_KEY", None)
os.environ.pop("groq_api", None)

# Load server .env
print("\n--- Loading server .env ---")
load_dotenv(dotenv_path=".env")
server_key = os.getenv("GROQ_API_KEY")
print("Server key:", server_key[:20] if server_key else "None")

def test_key(key, name):
    if not key:
        print(f"Skipping {name}: key is None")
        return False
    try:
        client = Groq(api_key=key)
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": "Say hello!"}],
            model="llama-3.3-70b-versatile",
            max_tokens=10
        )
        print(f"[SUCCESS] {name} worked! Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"[FAILED] {name} failed: {e}")
        return False

print("\n--- Testing Root Key ---")
test_key(root_key, "Root Key")

print("\n--- Testing Server Key ---")
test_key(server_key, "Server Key")
