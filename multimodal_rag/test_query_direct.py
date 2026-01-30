"""Test direct query to see what's happening."""
import httpx
import time

print("Testing query directly...")

start = time.time()
try:
    response = httpx.post(
        'http://localhost:8000/query',
        json={'query': 'What is the voltage?'},
        timeout=90.0
    )
    elapsed = time.time() - start
    
    print(f"\nQuery completed in {elapsed:.2f} seconds")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\nAnswer: {result.get('answer', '')[:200]}")
        print(f"Confidence: {result.get('confidence')}")
        print(f"Processing time: {result.get('processing_time')}")
    else:
        print(f"Error: {response.text}")
        
except httpx.ReadTimeout:
    elapsed = time.time() - start
    print(f"\n✗ TIMEOUT after {elapsed:.1f} seconds")
    print("The OpenRouter API is too slow or not working correctly.")
except Exception as e:
    print(f"\n✗ Error: {e}")
