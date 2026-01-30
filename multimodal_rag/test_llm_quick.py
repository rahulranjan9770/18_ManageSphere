"""Quick test to check which LLM is working."""
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test_gemini():
    """Test Gemini API."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "❌ Gemini: No API key"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": "Say 'Hello World' in one word"}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 50}
            }
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            text = result['candidates'][0]['content']['parts'][0]['text']
            return f"✅ Gemini: {text[:50]}"
    except Exception as e:
        return f"❌ Gemini: {str(e)[:100]}"

async def test_openrouter():
    """Test OpenRouter API."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "❌ OpenRouter: No API key"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000",
            }
            payload = {
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": [{"role": "user", "content": "Say 'Hello World' in one word"}],
                "temperature": 0.3,
                "max_tokens": 50
            }
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            text = result['choices'][0]['message']['content']
            return f"✅ OpenRouter: {text[:50]}"
    except Exception as e:
        return f"❌ OpenRouter: {str(e)[:100]}"

async def test_ollama():
    """Test Ollama local instance."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2:3b",
                    "prompt": "Say 'Hello World' in one word",
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 10}
                }
            )
            response.raise_for_status()
            result = response.json()
            text = result.get('response', '')
            return f"✅ Ollama: {text[:50]}"
    except Exception as e:
        return f"❌ Ollama: {str(e)[:100]}"

async def main():
    print("\n🧪 Testing All LLM Endpoints...\n")
    
    gemini_result = await test_gemini()
    print(f"1. {gemini_result}")
    
    openrouter_result = await test_openrouter()
    print(f"2. {openrouter_result}")
    
    ollama_result = await test_ollama()
    print(f"3. {ollama_result}")
    
    print("\n✅ = Working | ❌ = Failed\n")

if __name__ == "__main__":
    asyncio.run(main())
