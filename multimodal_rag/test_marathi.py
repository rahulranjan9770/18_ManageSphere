import requests
import json

# Test 1: Query with Marathi language selected
print("=" * 60)
print("TEST 1: Force Marathi Output")
print("=" * 60)

url = "http://localhost:8000/query"
payload = {
    "query": "What is machine learning?",
    "target_language": "mr",  # Force Marathi
    "persona": "standard"
}

try:
    response = requests.post(url, json=payload, timeout=60)
    data = response.json()
    answer = data.get("answer", "")
    
    print("\n📝 Query: What is machine learning?")
    print(f"🎯 Target Language: Marathi (mr)")
    print(f"\n💬 Response ({len(answer)} chars):")
    print(answer)
    print("\n" + "=" * 60)
    
    # Check for Devanagari
    devanagari_range = range(0x0900, 0x097F)
    has_devanagari = any(ord(c) in devanagari_range for c in answer)
    
    if has_devanagari:
        print("✅ SUCCESS: Response contains Devanagari script (Marathi/Hindi)")
    else:
        print("❌ FAILED: Response is in English (no Devanagari found)")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Query without language specified (should default to English)
print("\n" + "=" * 60)
print("TEST 2: Default (No Language Specified - Should be English)")
print("=" * 60)

payload2 = {
    "query": "What is artificial intelligence?",
    "persona": "standard"
}

try:
    response = requests.post(url, json=payload2, timeout=60)
    data = response.json()
    answer = data.get("answer", "")
    
    print("\n📝 Query: What is artificial intelligence?")
    print(f"🎯 Target Language: None (auto-detect/default)")
    print(f"\n💬 Response ({len(answer)} chars):")
    print(answer[:200] + "..." if len(answer) > 200 else answer)
    print("\n" + "=" * 60)
    
    # Should be English
    has_latin = any(ord('a') <= ord(c.lower()) <= ord('z') for c in answer[:100])
    if has_latin:
        print("✅ SUCCESS: Response appears to be in English")
    else:
        print("⚠️  WARNING: Response might not be in English")
        
except Exception as e:
    print(f"❌ Error: {e}")
