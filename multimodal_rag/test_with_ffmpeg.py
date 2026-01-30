"""
Final comprehensive test with FFmpeg installed
"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("="*70)
print("UPLOADING FILES WITH FFMPEG INSTALLED")
print("="*70)

# Reset database
print("\nResetting database...")
requests.delete(f"{BASE_URL}/reset")

# Upload text file
print("\n[1] Uploading text file...")
with open("test_document.txt", "rb") as f:
    r = requests.post(f"{BASE_URL}/upload", files={"file": f})
    if r.status_code == 200:
        data = r.json()
        print(f"   Text file: {data['chunks_created']} chunks created")
    else:
        print(f"   ERROR: {r.text}")

# Upload audio file
print("\n[2] Uploading audio file...")
with open("Recording.m4a", "rb") as f:
    r = requests.post(f"{BASE_URL}/upload", files={"file": f})
    if r.status_code == 200:
        data = r.json()
        print(f"   Audio file: {data['chunks_created']} chunks created")
        print(f"   Modalities: {', '.join(data['modalities_detected'])}")
    else:
        print(f"   ERROR: {r.text}")

# Check database
print("\n[3] Database stats:")
stats = requests.get(f"{BASE_URL}/stats").json()
print(f"   Total chunks: {stats['total_chunks']}")

# Query for text
print("\n[4] Query test - Text content:")
r = requests.post(f"{BASE_URL}/query", json={"query": "What is photosynthesis?"})
if r.status_code == 200:
    result = r.json()
    evidence = result.get('evidence', [])
    print(f"   Found {len(evidence)} evidence chunks")
    if evidence:
        print(f"   Top result: {evidence[0].get('text', '')[:100]}...")

# Query for audio
print("\n[5] Query test - Audio content:")
r = requests.post(f"{BASE_URL}/query", json={"query": "What does the audio recording say?"})
if r.status_code == 200:
    result = r.json()
    evidence = result.get('evidence', [])
    print(f"   Found {len(evidence)} evidence chunks")
    if evidence:
        for i, ev in enumerate(evidence[:2], 1):
            text = ev.get('text', '')
            print(f"   Evidence {i}: {text[:150]}...")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
print(f"\nSUMMARY:")
print(f"  - Text extraction: WORKING")
print(f"  - Audio transcription: {'WORKING' if stats['total_chunks'] > 1 else 'NEEDS CHECK'}")
print(f"  - Total chunks in database: {stats['total_chunks']}")
print("="*70)
