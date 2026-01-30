import asyncio
from pathlib import Path
from backend.ingestion.image_processor import ImageProcessor
from backend.storage.vector_store import VectorStore
from backend.config import settings

async def verify_ocr():
    print("🔍 Verifying OCR and Indexing...")
    
    # 1. Test Image Processor directly
    processor = ImageProcessor()
    image_path = Path("chakravyuh_poster.jpg")
    
    if not image_path.exists():
        print(f"❌ Image not found: {image_path}")
        return

    print(f"📄 Processing {image_path}...")
    chunks = processor.process_file(image_path)
    
    if not chunks:
        print("❌ No chunks created!")
        return
        
    chunk = chunks[0]
    print(f"✅ Chunk Created!")
    print(f"   Modality: {chunk.modality}")
    print(f"   Has OCR Text: {chunk.metadata.get('has_ocr_text')}")
    print("\n--- Extracted Content Preview ---")
    print(chunk.content[:500] + "..." if len(chunk.content) > 500 else chunk.content)
    print("---------------------------------\n")

    # 2. Check Retrieval
    print("🔎 Testing Retrieval for 'prize pool'...")
    store = VectorStore()
    
    # Need an embedding for the query. In a real scenario, the Embedder does this.
    # For this test, we'll confirm OCR first. 
    # To test full retrieval, we should use the retriever, not the store directly,
    # or mock the embedding.
    
    # Let's verify OCR content first which is the main goal
    print("Skipping direct vector search in this unit test to avoid dependency complexity.")
    print("Focusing on OCR verification...")
    
    # We can inspect the chunks created in step 1 directly
    if "prize" in chunk.content.lower() or "1,00,000" in chunk.content or "lakh" in chunk.content.lower():
        print("✅ OCR SUCCESS! 'Prize' or amount found in text.")
    else:
        print("❌ OCR WARNING: Key terms not found in extracted text.")


if __name__ == "__main__":
    asyncio.run(verify_ocr())
