import requests
import json

# Test 1: Upload text file
print("="*60)
print("TEST 1: Uploading test_document.txt")
print("="*60)

with open("test_document.txt", "rb") as f:
    response = requests.post("http://localhost:8000/upload", files={"file": f})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.text}")

print("\n" + "="*60)
print("TEST 2: Uploading Recording.m4a")
print("="*60)

with open("Recording.m4a", "rb") as f:
    response = requests.post("http://localhost:8000/upload", files={"file": f})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.text}")

print("\n" + "="*60)
print("TEST 3: Query for photosynthesis")
print("="*60)

response = requests.post("http://localhost:8000/query", json={"query": "What is photosynthesis?"})
print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"\nAnswer: {result.get('answer', 'No answer')}")
    print(f"\nEvidence count: {len(result.get('evidence', []))}")
    for i, ev in enumerate(result.get('evidence', [])[:3], 1):
        print(f"\nEvidence {i}:")
        print(f"  Type: {ev.get('type')}")
        print(f"  Score: {ev.get('score')}")
        print(f"  Text: {ev.get('text', '')[:200]}...")
else:
    print(f"Error: {response.text}")

print("\n" + "="*60)
print("TEST 4: Query for audio content")
print("="*60)

response = requests.post("http://localhost:8000/query", json={"query": "What does the recording say?"})
print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"\nAnswer: {result.get('answer', 'No answer')}")
    print(f"\nEvidence count: {len(result.get('evidence', []))}")
    for i, ev in enumerate(result.get('evidence', [])[:3], 1):
        print(f"\nEvidence {i}:")
        print(f"  Type: {ev.get('type')}")
        print(f"  Score: {ev.get('score')}")
        print(f"  Text: {ev.get('text', '')[:200]}...")
else:
    print(f"Error: {response.text}")

print("\n" + "="*60)
print("DATABASE STATS")
print("="*60)

response = requests.get("http://localhost:8000/stats")
if response.status_code == 200:
    print(json.dumps(response.json(), indent=2))
