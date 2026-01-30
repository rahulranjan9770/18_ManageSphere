"""
Check what text was transcribed from the audio files
"""
import requests
import json

print("="*70)
print("EXTRACTING ALL AUDIO TRANSCRIPTIONS FROM DATABASE")
print("="*70)

# Use a broad query to get all content
response = requests.post("http://localhost:8000/query", json={
    "query": "everything in the database audio recording meeting machine voltage"
})

if response.status_code == 200:
    result = response.json()
    evidence = result.get('evidence', [])
    
    # Filter for audio chunks
    audio_chunks = [ev for ev in evidence if ev.get('type') == 'audio']
    
    print(f"\nTotal evidence chunks found: {len(evidence)}")
    print(f"Audio chunks: {len(audio_chunks)}")
    print(f"Text chunks: {len([ev for ev in evidence if ev.get('type') == 'text'])}")
    
    if audio_chunks:
        print("\n" + "="*70)
        print("AUDIO TRANSCRIPTIONS:")
        print("="*70)
        
        for i, chunk in enumerate(audio_chunks, 1):
            print(f"\n--- Audio Chunk {i} ---")
            print(f"Source File: {chunk.get('source', 'Unknown')}")
            print(f"Score: {chunk.get('score', 0):.4f}")
            print(f"\nTranscribed Text:")
            print(chunk.get('text', '[No text]'))
            
            metadata = chunk.get('metadata', {})
            if metadata:
                print(f"\nMetadata:")
                for key, value in metadata.items():
                    print(f"  {key}: {value}")
    else:
        print("\n⚠ No audio chunks found!")
        print("\nAll evidence chunks:")
        for i, ev in enumerate(evidence[:5], 1):
            print(f"\n{i}. Type: {ev.get('type')}, Source: {ev.get('source')}")
            print(f"   Text: {ev.get('text', '')[:100]}...")
else:
    print(f"Query failed: {response.text}")

# Also check database stats
print("\n" + "="*70)
print("DATABASE STATISTICS")
print("="*70)
stats = requests.get("http://localhost:8000/stats").json()
print(json.dumps(stats, indent=2))
