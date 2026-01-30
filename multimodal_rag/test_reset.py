
import requests

print("Attempting to reset database...")
try:
    response = requests.delete("http://localhost:8000/reset")
    if response.status_code == 200:
        print("Success: Database reset")
    else:
        print(f"Failed: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Error: {e}")
