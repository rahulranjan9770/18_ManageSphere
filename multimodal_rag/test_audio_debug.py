"""
Test audio processing directly with file logging
"""
from pathlib import Path
import sys
sys.path.append('.')

from backend.ingestion.audio_processor import AudioProcessor

output_file = open("audio_test_output.txt", "w", encoding="utf-8")

def log(msg):
    print(msg)
    output_file.write(msg + "\n")

log("="*70)
log("TESTING AUDIO PROCESSOR DIRECTLY")
log("="*70)

processor = AudioProcessor()
audio_file = Path("Recording.m4a")

if not audio_file.exists():
    log(f"ERROR: {audio_file} not found!")
    output_file.close()
    sys.exit(1)

log(f"\nProcessing: {audio_file}")
log(f"File size: {audio_file.stat().st_size / 1024:.2f} KB")

try:
    chunks = processor.process_file(audio_file)
    
    log(f"\nResult: {len(chunks)} chunks created")
    
    for i, chunk in enumerate(chunks, 1):
        log(f"\nChunk {i}:")
        log(f"  ID: {chunk.chunk_id}")
        log(f"  Source: {chunk.source_file}")
        log(f"  Modality: {chunk.modality}")
        log(f"  Confidence: {chunk.confidence}")
        log(f"  Content length: {len(chunk.content)} chars")
        log(f"  Content: {chunk.content}")
        log(f"  Metadata: {str(chunk.metadata)}")
        
except Exception as e:
    log(f"\nERROR: {e}")
    import traceback
    traceback.print_exc(file=output_file)

output_file.close()
log("Output saved to audio_test_output.txt")
