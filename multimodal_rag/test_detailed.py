"""
Test to see what's in the actual response
"""
import requests
import json

print("="*70)
print("DETAILED UPLOAD TEST")
print("="*70)

# Reset
print("\n1. Resetting database...")
r = requests.delete("http://localhost:8000/reset")
print(f"   Reset: {r.status_code}")

# Upload audio
print("\n2. Uploading Recording.m4a...")
with open('Recording.m4a', 'rb') as f:
    r = requests.post('http://localhost:8000/upload', files={'file': f})
    print(f"   Status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print("\n   Full Response:")
        for key, value in data.items():
            print(f"     {key}: {value}")
    else:
        print(f"   Error: {r.text}")

# Check stats
print("\n3. Database stats:")
stats = requests.get("http://localhost:8000/stats").json()
print(f"   Total chunks: {stats['total_chunks']}")

print("\n" + "="*70)
