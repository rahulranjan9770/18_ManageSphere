"""
Final upload verification test
"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("="*70)
print("MULTIMODAL RAG SYSTEM - UPLOAD VERIFICATION TEST")
print("="*70)

# Get current database stats
print("\n[1] Current Database State:")
print("-"*70)
stats = requests.get(f"{BASE_URL}/stats").json()
print(f"Total chunks: {stats['total_chunks']}")
print(f"Collection: {stats['collection']}")
print(f"Models: {json.dumps(stats['models'], indent=2)}")

# Query for text content
print("\n[2] Testing Text File Retrieval (Photosynthesis):")
print("-"*70)
response = requests.post(f"{BASE_URL}/query", json={"query": "What is photosynthesis?"})
if response.status_code == 200:
    result = response.json()
    evidence = result.get('evidence', [])
    print(f"Found {len(evidence)} evidence chunks")
    
    if evidence:
        for i, ev in enumerate(evidence, 1):
            print(f"\n  Chunk {i}:")
            print(f"    Type: {ev.get('type')}")
            print(f"    Source: {ev.get('source')}")
            print(f"    Score: {ev.get('score'):.4f}")
            text = ev.get('text', '')
            print(f"    Text: {text}")
else:
    print(f"Error: {response.text}")

# Query for audio content
print("\n[3] Testing Audio File Retrieval:")
print("-"*70)
response = requests.post(f"{BASE_URL}/query", json={"query": "What does the recording discuss?"})
if response.status_code == 200:
    result = response.json()
    evidence = result.get('evidence', [])
    print(f"Found {len(evidence)} evidence chunks")
    
    if evidence:
        for i, ev in enumerate(evidence, 1):
            print(f"\n  Chunk {i}:")
            print(f"    Type: {ev.get('type')}")
            print(f"    Source: {ev.get('source')}")
            print(f"    Score: {ev.get('score'):.4f}")
            text = ev.get('text', '')
            # Handle potential encoding issues
            try:
                print(f"    Text Length: {len(text)} characters")
                if len(text) < 500:
                    print(f"    Text: {text}")
                else:
                    print(f"    Text (truncated): {text[:500]}...")
            except Exception as e:
                print(f"    (Text display error: {e})")
                
            # Show metadata
            meta = ev.get('metadata', {})
            if meta:
                print(f"    Metadata:")
                for key, val in meta.items():
                    print(f"      {key}: {val}")
    else:
        print("No evidence found for audio query")
else:
    print(f"Error: {response.text}")

print("\n" + "="*70)
print("TEST SUMMARY")
print("="*70)
print(f"Total chunks in database: {stats['total_chunks']}")
print("\nConclusion:")
print("- Text file extraction: Check evidence count above")
print("- Audio file extraction: Check evidence count above")  
print("="*70)
