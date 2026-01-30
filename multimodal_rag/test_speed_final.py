"""Quick speed test for uploads and queries."""
import httpx
import time
from pathlib import Path

print("=== SPEED TEST ===\n")

# Test text upload
print("1. Testing text file upload...")
file_path = Path('machine_manual.txt')
start = time.time()
with open(file_path, 'rb') as f:
    files = {'file': (file_path.name, f, 'text/plain')}
    response = httpx.post('http://localhost:8000/upload', files=files, timeout=30.0)
text_time = time.time() - start
print(f"   ✓ Text upload: {text_time:.2f} seconds")
print(f"   Status: {response.status_code}")

# Test query
print("\n2. Testing query...")
start = time.time()
response = httpx.post(
    'http://localhost:8000/query',
    json={'query': 'What is the operating voltage?'},
    timeout=60.0
)
query_time = time.time() - start
result = response.json()
print(f"   ✓ Query response: {query_time:.2f} seconds")
print(f"   Answer: {result.get('answer', '')[:100]}...")
print(f"   Confidence: {result.get('confidence')}")

# Summary
print(f"\n=== TOTAL TIME ===")
print(f"Upload + Query: {text_time + query_time:.2f} seconds")
print(f"\nTarget: <10 seconds ✓" if (text_time + query_time) < 10 else f"\nTarget: <10 seconds ✗")
