"""Direct test of Ollama LLM generation."""
import asyncio
import httpx

async def test_ollama():
    """Test Ollama with actual generation."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2:3b",
                    "prompt": "What is 2+2? Answer in one sentence.",
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 50}
                }
            )
            print(f"Status: {response.status_code}")
            result = response.json()
            print(f"Response: {result.get('response', 'NO RESPONSE')}")
            print(f"Done: {result.get('done', False)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ollama())
