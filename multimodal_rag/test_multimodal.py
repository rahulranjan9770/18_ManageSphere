"""Test image and audio processing directly."""
from PIL import Image
import sys

# Test 1: Image Processing
print("="*60)
print("TEST 1: Image Processing")
print("="*60)

try:
    from backend.ingestion.image_processor import ImageProcessor
    from pathlib import Path
    
    processor = ImageProcessor()
    img_path = Path("chakravyuh_poster.jpg")
    
    if img_path.exists():
        print(f"✅ Image file found: {img_path}")
        print(f"   Size: {img_path.stat().st_size} bytes")
        
        # Try to process
        chunks = processor.process_file(img_path)
        print(f"✅ Processing successful!")
        print(f"   Chunks created: {len(chunks)}")
        for i, chunk in enumerate(chunks):
            print(f"   Chunk {i+1}: {chunk.chunk_id[:20]}... | {chunk.modality}")
    else:
        print(f"❌ Image file not found at: {img_path.absolute()}")
except Exception as e:
    print(f"❌ Image processing failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Audio Processing
print("\n" + "="*60)
print("TEST 2: Audio Processing")
print("="*60)

try:
    from backend.ingestion.audio_processor import AudioProcessor
    from pathlib import Path
    
    processor = AudioProcessor()
    
    # Create a minimal WAV file for testing
    import wave
    import struct
    
    test_audio = Path("test_audio.wav")
    
    # Create a 1-second silent audio file
    sample_rate = 16000
    duration = 1  # seconds
    num_samples = sample_rate * duration
    
    with wave.open(str(test_audio), 'w') as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        # Write silent audio (all zeros)
        for _ in range(num_samples):
            wav_file.writeframes(struct.pack('<h', 0))
    
    print(f"✅ Test audio file created: {test_audio}")
    print(f"   Size: {test_audio.stat().st_size} bytes")
    
    # Try to process
    chunks = processor.process_file(test_audio)
    print(f"✅ Processing successful!")
    print(f"   Chunks created: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"   Chunk {i+1}: {chunk.chunk_id[:20]}... | {chunk.modality}")
        print(f"   Content preview: {chunk.content[:100]}...")
        
except Exception as e:
    print(f"❌ Audio processing failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
