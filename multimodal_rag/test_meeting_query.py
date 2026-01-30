import requests
import json
import time

print("="*70)
print("TESTING MEETING QUERY")
print("="*70)

query = "what was discussed in the meeting regarding machine safety?"
print(f"Query: {query}")

# Wait for server to reload
time.sleep(2)

try:
    response = requests.post("http://localhost:8000/query", json={
        "query": query
    })
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response Keys: {list(result.keys())}")
        
        print(f"\nAnswer:\n{result.get('answer', 'No answer')}")
        
        # Check 'sources' instead of 'evidence'
        sources = result.get('sources', [])
        print(f"\nFound {len(sources)} sources")
        
        for i, ev in enumerate(sources, 1):
            if i > 5: break
            print(f"\n--- Source {i} ---")
            print(f"Source: {ev.get('source_file')}")
            print(f"Modality: {ev.get('modality')}")
            print(f"Text: {ev.get('text', ev.get('content', ''))}")
    else:
        print(f"Error: {response.text}")

except Exception as e:
    print(f"Connection error: {e}")
