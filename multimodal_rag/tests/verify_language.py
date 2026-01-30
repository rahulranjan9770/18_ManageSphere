
import requests
import json
import time
import sys

def test_language_enforcement(base_url):
    print("\n🧪 Testing Language Enforcement (Marathi)...")
    url = f"{base_url}/query"
    
    payload = {
        "query": "What is machine learning?",
        "target_language": "mr",
        "persona": "standard",
        "enable_web_search": False
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        answer = data.get("answer", "")
        
        print(f"📝 Response received ({len(answer)} chars)")
        print(f"Preview: {answer[:100]}...")
        
        # Simple heuristic: Check for Devanagari characters
        devanagari_range = range(0x0900, 0x097F)
        has_devanagari = any(ord(c) in devanagari_range for c in answer)
        
        if has_devanagari:
            print("✅ SUCCESS: Response contains Devanagari characters.")
            return True
        else:
            print("❌ FAILURE: Response appears to be in English (no Devanagari found).")
            return False
        
    except Exception as e:
        print(f"❌ Error during language test: {e}")
        return False

def test_regression_standard(base_url):
    print("\n🧪 Regression Test: Standard Query (No Force)...")
    url = f"{base_url}/query"
    payload = {
        "query": "What is AI?",
        "enable_auto_translate": True 
    }
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            print("✅ SUCCESS: Standard query works.")
            return True
        else:
            print(f"❌ FAILURE: Standard query returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error during regression test: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = 8005
        
    base_url = f"http://localhost:{port}"
    print(f"Running verification on {base_url}...")
    
    # Wait for server to be ready
    for i in range(10):
        try:
            requests.get(base_url, timeout=1)
            print("Server is ready.")
            break
        except:
            print("Waiting for server...")
            time.sleep(2)
    else:
        print("❌ Server unreachable after 20s.")
        sys.exit(1)

    results = []
    results.append(test_language_enforcement(base_url))
    results.append(test_regression_standard(base_url))
    
    if all(results):
        print("\n✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED")
        sys.exit(1)
