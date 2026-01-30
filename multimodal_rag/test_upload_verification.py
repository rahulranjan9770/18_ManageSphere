"""
Test script to upload recording.m4a and test_document.txt
and verify text extraction and chunk generation
"""
import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"

def upload_file(file_path: str):
    """Upload a file to the RAG system"""
    print(f"\n{'='*60}")
    print(f"Uploading: {Path(file_path).name}")
    print(f"{'='*60}")
    
    url = f"{BASE_URL}/upload"
    
    with open(file_path, 'rb') as f:
        files = {'file': (Path(file_path).name, f)}
        response = requests.post(url, files=files)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Upload successful!")
        print(f"\nResponse Data:")
        print(json.dumps(result, indent=2))
        
        # Extract and display key information
        print(f"\n{'='*60}")
        print(f"UPLOAD SUMMARY")
        print(f"{'='*60}")
        print(f"Document ID: {result.get('doc_id')}")
        print(f"Filename: {result.get('filename')}")
        print(f"Modalities Detected: {', '.join(result.get('modalities_detected', []))}")
        print(f"Total Chunks Created: {result.get('chunks_created', 0)}")
        print(f"Message: {result.get('message')}")
        
        return result
    else:
        print(f"✗ Upload failed!")
        print(f"Error: {response.text}")
        return None

def inspect_database():
    """Get current database stats"""
    try:
        response = requests.get(f"{BASE_URL}/stats")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error getting stats: {e}")
    return None

def test_query(query_text: str):
    """Test querying the uploaded content"""
    print(f"\n{'='*60}")
    print(f"TESTING QUERY: '{query_text}'")
    print(f"{'='*60}")
    
    url = f"{BASE_URL}/query"
    payload = {"query": query_text}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Query successful!")
            
            # Show evidence chunks
            if 'evidence' in result and result['evidence']:
                print(f"\nFound {len(result['evidence'])} evidence chunks:\n")
                for i, evidence in enumerate(result['evidence'][:3], 1):
                    print(f"Evidence {i}:")
                    print(f"  Type: {evidence.get('type', 'N/A')}")
                    print(f"  Score: {evidence.get('score', 0):.4f}")
                    text = evidence.get('text', '')
                    preview = text[:300] + "..." if len(text) > 300 else text
                    print(f"  Text: {preview}")
                    print()
            else:
                print("No evidence found")
            
            # Show answer
            if 'answer' in result:
                print(f"Answer: {result['answer']}")
            
            return result
        else:
            print(f"✗ Query failed: {response.text}")
            return None
    except Exception as e:
        print(f"Error during query: {e}")
        return None


def main():
    print("\n" + "="*60)
    print("MULTIMODAL RAG UPLOAD TEST")
    print("="*60)
    
    # Wait for server to be ready
    print("\nChecking if server is ready...")
    max_attempts = 10
    for i in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}/stats", timeout=2)
            if response.status_code == 200:
                print("✓ Server is ready!")
                print(f"Server stats: {response.json()}")
                break
        except Exception as e:
            print(f"Waiting for server... ({i+1}/{max_attempts})")
            time.sleep(2)
    else:
        print("✗ Server is not responding. Please start the backend.")
        return
    
    # Get initial database state
    print("\n" + "="*60)
    print("INITIAL DATABASE STATE")
    print("="*60)
    initial_stats = inspect_database()
    if initial_stats:
        print(json.dumps(initial_stats, indent=2))
    
    # Test files
    test_files = [
        "test_document.txt",
        "Recording.m4a"
    ]
    
    results = {}
    
    for file_name in test_files:
        file_path = Path(__file__).parent / file_name
        
        if not file_path.exists():
            print(f"\n✗ File not found: {file_path}")
            continue
        
        result = upload_file(str(file_path))
        results[file_name] = result
        
        # Small delay between uploads
        time.sleep(1)
    
    # Get final database state
    print("\n" + "="*60)
    print("FINAL DATABASE STATE")
    print("="*60)
    final_stats = inspect_database()
    if final_stats:
        print(json.dumps(final_stats, indent=2))
    
    # Test queries
    print("\n" + "="*60)
    print("TESTING RETRIEVAL")
    print("="*60)
    
    # Query for text content
    print("\n--- Testing text file query ---")
    test_query("What is photosynthesis?")
    
    # Query for audio content
    print("\n--- Testing audio file query ---")
    test_query("What does the audio talk about?")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for file_name, result in results.items():
        if result:
            chunks = result.get('chunks_created', 0)
            modalities = ', '.join(result.get('modalities_detected', []))
            print(f"✓ {file_name}")
            print(f"    Modalities: {modalities}")
            print(f"    Chunks: {chunks}")
        else:
            print(f"✗ {file_name}: Upload failed")
    
    if initial_stats and final_stats:
        print(f"\nTotal chunks before: {initial_stats.get('total_chunks', 0)}")
        print(f"Total chunks after: {final_stats.get('total_chunks', 0)}")
        print(f"New chunks added: {final_stats.get('total_chunks', 0) - initial_stats.get('total_chunks', 0)}")


if __name__ == "__main__":
    main()
