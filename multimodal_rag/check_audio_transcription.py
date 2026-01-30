import requests
import json

# Query for machine/voltage content
print("="*70)
print("SEARCHING FOR MACHINE/VOLTAGE CONTENT")
print("="*70)

response = requests.post("http://localhost:8000/query", json={
    "query": "What are the voltage limits for machine operation?"
})

if response.status_code == 200:
    result = response.json()
    print(f"\nAnswer:\n{result.get('answer', 'No answer')}\n")
    
    evidence = result.get('evidence', [])
    print(f"Found {len(evidence)} evidence chunks:\n")
    
    for i, ev in enumerate(evidence, 1):
        print(f"\n--- Evidence {i} ---")
        print(f"Type: {ev.get('type')}")
        print(f"Source: {ev.get('source')}")
        print(f"Score: {ev.get('score', 0):.4f}")
        print(f"Text: {ev.get('text', '')}")
        if 'metadata' in ev:
            print(f"Metadata: {json.dumps(ev.get('metadata'), indent=2)}")
else:
    print(f"Error: {response.text}")

# Also try a more general query to see all audio content
print("\n" + "="*70)
print("SEARCHING FOR ANY AUDIO CONTENT")
print("="*70)

response2 = requests.post("http://localhost:8000/query", json={
    "query": "recording audio transcript"
})

if response2.status_code == 200:
    result2 = response2.json()
    evidence2 = result2.get('evidence', [])
    
    audio_evidence = [ev for ev in evidence2 if ev.get('type') == 'audio']
    print(f"\nFound {len(audio_evidence)} audio chunks:\n")
    
    for i, ev in enumerate(audio_evidence, 1):
        print(f"\n--- Audio Chunk {i} ---")
        print(f"Source: {ev.get('source')}")
        print(f"Text: {ev.get('text', '')}")
