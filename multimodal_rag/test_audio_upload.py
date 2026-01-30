import requests
import json

print("Uploading Recording.m4a...")
with open('Recording.m4a', 'rb') as f:
    r = requests.post('http://localhost:8000/upload', files={'file': f})
    result = r.json()
    print("\nUpload Result:")
    print(json.dumps(result, indent=2))
    
print("\n" + "="*60)
print("Database stats:")
stats = requests.get('http://localhost:8000/stats').json()
print(json.dumps(stats, indent=2))
