"""Find correct Gemini model name."""
import httpx

API_KEY = "AIzaSyBVVwmeaMfR_0qdZEGfFAEjLkkfnT-REmE"

models_to_try = [
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash-001",
    "gemini-pro",
    "gemini-1.5-pro-latest"
]

for model in models_to_try:
    print(f"\nTrying: {model}...")
    try:
        r = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": "hi"}]}],
                "generationConfig": {"maxOutputTokens": 10}
            },
            timeout=15.0
        )
        
        if r.status_code == 200:
            result = r.json()
            answer = result['candidates'][0]['content']['parts'][0]['text']
            print(f"✓ WORKS! Answer: {answer}")
            print(f"✓✓✓ Use this model: {model}")
            break
        else:
            print(f"✗ Failed: {r.status_code}")
            
    except Exception as e:
        print(f"✗ Error: {str(e)[:100]}")
