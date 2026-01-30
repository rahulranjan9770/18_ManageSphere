"""
Comprehensive upload test with detailed output
"""
import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

# Reset database
print_section("RESETTING DATABASE")
requests.delete(f"{BASE_URL}/reset")
print("✓ Database reset")

# Get initial stats
print_section("INITIAL STATE")
stats = requests.get(f"{BASE_URL}/stats").json()
print(json.dumps(stats, indent=2))

# Upload text file
print_section("UPLOADING: test_document.txt")
with open("test_document.txt", "rb") as f:
    response = requests.post(f"{BASE_URL}/upload", files={"file": ("test_document.txt", f)})
    print(f"Status Code: {response.status_code}\n")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ SUCCESS!")
        print(f"  - Document ID: {data['doc_id']}")
        print(f"  - Filename: {data['filename']}")
        print(f"  - Modalities: {', '.join(data['modalities_detected'])}")
        print(f"  - Chunks Created: {data['chunks_created']}")
        print(f"  - Message: {data['message']}")
    else:
        print(f"✗ FAILED: {response.text}")

# Upload audio file
print_section("UPLOADING: Recording.m4a")
audio_file = Path("Recording.m4a")
if audio_file.exists():
    print(f"File size: {audio_file.stat().st_size / 1024:.2f} KB")
    with open(audio_file, "rb") as f:
        response = requests.post(f"{BASE_URL}/upload", files={"file": ("Recording.m4a", f)})
        print(f"\nStatus Code: {response.status_code}\n")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ SUCCESS!")
            print(f"  - Document ID: {data['doc_id']}")
            print(f"  - Filename: {data['filename']}")
            print(f"  - Modalities: {', '.join(data['modalities_detected'])}")
            print(f"  - Chunks Created: {data['chunks_created']}")
            print(f"  - Message: {data['message']}")
        else:
            print(f"✗ FAILED: {response.text}")
else:
    print("✗ File not found!")

# Get final stats
print_section("FINAL DATABASE STATE")
stats = requests.get(f"{BASE_URL}/stats").json()
print(json.dumps(stats, indent=2))
print(f"\n✓ Total chunks in database: {stats['total_chunks']}")

# Test query on text
print_section("QUERY TEST 1: Text Content (Photosynthesis)")
response = requests.post(f"{BASE_URL}/query", json={"query": "What is photosynthesis and why is it important?"})
if response.status_code == 200:
    result = response.json()
    print(f"Answer:\n{result.get('answer', 'No answer')}\n")
    
    evidence = result.get('evidence', [])
    print(f"Evidence Found: {len(evidence)} chunk(s)\n")
    
    for i, ev in enumerate(evidence, 1):
        print(f"Evidence {i}:")
        print(f"  Type: {ev.get('type')}")
        print(f"  Score: {ev.get('score'):.4f}")
        print(f"  Source: {ev.get('source')}")
        text = ev.get('text', '')
        print(f"  Text ({len(text)} chars): {text[:150]}{'...' if len(text) > 150 else ''}")
        print()
else:
    print(f"✗ Query failed: {response.text}")

# Test query on audio
print_section("QUERY TEST 2: Audio Content")
response = requests.post(f"{BASE_URL}/query", json={"query": "What is discussed in the audio recording?"})
if response.status_code == 200:
    result = response.json()
    print(f"Answer:\n{result.get('answer', 'No answer')}\n")
    
    evidence = result.get('evidence', [])
    print(f"Evidence Found: {len(evidence)} chunk(s)\n")
    
    for i, ev in enumerate(evidence, 1):
        print(f"Evidence {i}:")
        print(f"  Type: {ev.get('type')}")
        print(f"  Score: {ev.get('score'):.4f}")
        print(f"  Source: {ev.get('source')}")
        text = ev.get('text', '')
        print(f"  Text ({len(text)} chars): {text[:150]}{'...' if len(text) > 150 else ''}")
        
        # Show audio metadata if any
        meta = ev.get('metadata', {})
        if meta:
            print(f"  Metadata: {json.dumps(meta, indent=4)}")
        print()
else:
    print(f"✗ Query failed: {response.text}")

print_section("TEST COMPLETE")
print("✓ All tests executed")
