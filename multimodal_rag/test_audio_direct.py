"""
Test audio processing directly
"""
from pathlib import Path
import sys
sys.path.append('.')

from backend.ingestion.audio_processor import AudioProcessor

print("="*70)
print("TESTING AUDIO PROCESSOR DIRECTLY")
print("="*70)

processor = AudioProcessor()
audio_file = Path("Recording.m4a")

if not audio_file.exists():
    print(f"ERROR: {audio_file} not found!")
    sys.exit(1)

print(f"\nProcessing: {audio_file}")
print(f"File size: {audio_file.stat().st_size / 1024:.2f} KB")

try:
    chunks = processor.process_file(audio_file)
    
    print(f"\nResult: {len(chunks)} chunks created")
    
    for i, chunk in enumerate(chunks, 1):
        print(f"\nChunk {i}:")
        print(f"  ID: {chunk.chunk_id}")
        print(f"  Source: {chunk.source_file}")
        print(f"  Modality: {chunk.modality}")
        print(f"  Confidence: {chunk.confidence}")
        print(f"  Content length: {len(chunk.content)} chars")
        print(f"  Content: {chunk.content[:200]}")
        print(f"  Metadata: {chunk.metadata}")
        
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
