import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_ENDPOINT = os.getenv("API_ENDPOINT")
API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")

def test_api_basic():
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 0.0
    }
    try:
        response = requests.post(
            f"{API_ENDPOINT}/chat/completions",
            headers=headers,
            json=payload,
            verify="ca.crt",
            timeout=30
        )
        response.raise_for_status()
        print("API Response:")
        print(response.json())
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api_basic()

