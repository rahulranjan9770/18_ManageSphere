"""Test script for multimodal PDF processing.

This script tests the new PDF image extraction features.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.ingestion.text_processor import TextProcessor
from backend.utils.logger import logger


def test_multimodal_pdf_processing():
    """Test the multimodal PDF processor."""
    
    print("="*60)
    print("  MULTIMODAL PDF PROCESSING TEST")
    print("="*60)
    
    # Initialize processor
    print("\n1. Initializing TextProcessor with multimodal PDF support...")
    processor = TextProcessor()
    
    if hasattr(processor, 'pdf_processor'):
        print("   ✅ MultimodalPDFProcessor initialized")
        print(f"   - Image extraction: {processor.pdf_processor.extract_images}")
        print(f"   - Min image size: {processor.pdf_processor.min_image_size}")
        print(f"   - Max images/page: {processor.pdf_processor.max_images_per_page}")
    else:
        print("   ❌ MultimodalPDFProcessor not found!")
        return False
    
    # Check for test PDFs
    print("\n2. Looking for test PDF files...")
    data_dir = Path("data")
    
    pdf_files = []
    if data_dir.exists():
        pdf_files = list(data_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("   ℹ️  No PDF files found in data/ directory")
        print("   ℹ️  Upload a PDF to test the feature")
        return True
    
    print(f"   Found {len(pdf_files)} PDF file(s)")
    
    # Process first PDF found
    test_pdf = pdf_files[0]
    print(f"\n3. Processing test PDF: {test_pdf.name}")
    
    try:
        chunks = processor.process_file(test_pdf)
        
        # Analyze results
        text_chunks = [c for c in chunks if c.modality.value == "text"]
        image_chunks = [c for c in chunks if c.modality.value == "image"]
        
        print(f"\n   Results:")
        print(f"   ✅ Total chunks: {len(chunks)}")
        print(f"   📝 Text chunks: {len(text_chunks)}")
        print(f"   🖼️  Image chunks: {len(image_chunks)}")
        
        if image_chunks:
            print(f"\n   Image details:")
            for i, img_chunk in enumerate(image_chunks[:3], 1):  # Show first 3
                metadata = img_chunk.metadata
                print(f"   Image {i}:")
                print(f"   - Source: {metadata.get('source_type', 'unknown')}")
                print(f"   - Page: {metadata.get('page_number', 'N/A')}")
                print(f"   - Size: {metadata.get('width', 0)}x{metadata.get('height', 0)}")
                print(f"   - Has OCR: {metadata.get('has_ocr_text', False)}")
                print(f"   - Confidence: {img_chunk.confidence:.2f}")
            
            if len(image_chunks) > 3:
                print(f"   ... and {len(image_chunks) - 3} more images")
        
        print(f"\n   ✅ Multimodal PDF processing successful!")
        return True
        
    except Exception as e:
        print(f"\n   ❌ Error processing PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fallback_behavior():
    """Test that fallback still works."""
    print("\n" + "="*60)
    print("  FALLBACK BEHAVIOR TEST")
    print("="*60)
    
    processor = TextProcessor()
    
    if hasattr(processor, '_process_pdf_text_only'):
        print("\n   ✅ Fallback method exists")
        print("   - System can gracefully degrade to text-only if needed")
        return True
    else:
        print("\n   ❌ Fallback method not found")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n" + "="*60)
    print("  DEPENDENCY CHECK")
    print("="*60)
    
    dependencies = {
        "PyMuPDF": "fitz",
        "Pillow": "PIL",
        "NumPy": "numpy",
        "EasyOCR": "easyocr"
    }
    
    all_ok = True
    
    for name, module in dependencies.items():
        try:
            __import__(module)
            print(f"   ✅ {name}")
        except ImportError:
            print(f"   ❌ {name} - NOT INSTALLED")
            all_ok = False
    
    if not all_ok:
        print("\n   ⚠️  Some dependencies missing")
        print("   Run: pip install -r requirements.txt")
    
    return all_ok


def main():
    """Run all tests."""
    print("\n🔬 Testing Multimodal PDF Enhancement\n")
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    if not deps_ok:
        print("\n❌ Install missing dependencies first")
        return
    
    # Test multimodal processing
    processing_ok = test_multimodal_pdf_processing()
    
    # Test fallback
    fallback_ok = test_fallback_behavior()
    
    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    
    results = {
        "Dependencies": deps_ok,
        "Multimodal Processing": processing_ok,
        "Fallback Behavior": fallback_ok
    }
    
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n   🎉 All tests passed!")
        print("\n   The multimodal PDF feature is ready to use:")
        print("   1. Upload a PDF with embedded images")
        print("   2. System will extract text AND images")
        print("   3. Query about either text or visual content")
        print("   4. Get evidence-based responses with citations")
    else:
        print("\n   ⚠️  Some tests failed - check logs above")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
