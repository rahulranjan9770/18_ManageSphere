"""Test Ollama connection."""
import httpx
import asyncio


async def test_ollama():
    """Test Ollama API."""
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "llama3.2:3b",
        "prompt": "Say hello in one word",
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 50
        }
    }
    
    print("Testing Ollama connection...")
    print(f"URL: {url}")
    print(f"Model: llama3.2:3b")
    print("Sending request...")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ SUCCESS!")
                print(f"Generated text: {result.get('response', 'N/A')}")
                return True
            else:
                print(f"\n❌ FAILED: {response.status_code}")
                return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_ollama())
    exit(0 if success else 1)
