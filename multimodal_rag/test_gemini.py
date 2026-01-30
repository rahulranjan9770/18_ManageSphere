"""Test Gemini 1.5 Flash API."""
import httpx
import time

API_KEY = "AIzaSyBVVwmeaMfR_0qdZEGfFAEjLkkfnT-REmE"

print("=== Testing Gemini 1.5 Flash ===\n")

start = time.time()
try:
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{
                "parts": [{"text": "Say hi"}]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 20
            }
        },
        timeout=15.0
    )
    elapsed = time.time() - start
    
    print(f"Response time: {elapsed:.2f} seconds")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        answer = result['candidates'][0]['content']['parts'][0]['text']
        print(f"Answer: {answer}")
        print(f"\n✓✓✓ SUCCESS! Gemini 1.5 Flash works! ✓✓✓")
    else:
        print(f"Error: {response.text[:500]}")
        
except Exception as e:
    print(f"Failed: {e}")
