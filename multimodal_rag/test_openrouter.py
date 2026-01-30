"""Test OpenRouter with different models."""
import httpx
import time

API_KEY = "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"

# Try different model names
models_to_try = [
    "google/gemini-flash-1.5",
    "google/gemini-flash-1.5-8b",
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "qwen/qwen-2-7b-instruct:free"
]

print("=== Testing OpenRouter API with different models ===\n")

for model in models_to_try:
    print(f"Testing model: {model}")
    try:
        start = time.time()
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Multimodal RAG"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 20
            },
            timeout=15.0
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content']
            print(f"  ✓ SUCCESS in {elapsed:.2f}s: {answer[:50]}\n")
            print(f"✓✓✓ WORKING MODEL FOUND: {model} ✓✓✓\n")
            break
        else:
            print(f"  ✗ Failed ({response.status_code}): {response.text[:100]}\n")
            
    except Exception as e:
        print(f"  ✗ Error: {str(e)[:100]}\n")

print("\nRecommendation: Update .env with the working model name")
