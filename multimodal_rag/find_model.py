
"""Find working OpenRouter model."""
import httpx

API_KEY = "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"

models = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "qwen/qwen-2-7b-instruct:free"
]

for model in models:
    print(f"\nTesting: {model}...")
    try:
        r = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10
            },
            timeout=20.0
        )
        if r.status_code == 200:
            print(f"✓✓✓ WORKS: {model}")
            print(f"Response: {r.json()['choices'][0]['message']['content']}")
            with open('working_model.txt', 'w') as f:
                f.write(model)
            break
        else:
            print(f"✗ Failed: {r.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")
