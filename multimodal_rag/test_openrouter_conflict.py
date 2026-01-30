"""Test OpenRouter with a conflict-aware prompt like the actual app uses."""
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

async def test_openrouter_conflict():
    """Test OpenRouter with conflict prompt."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    # Simulated conflict prompt (shorter version)
    prompt = """You are a research assistant analyzing conflicting evidence.

Evidence:
[Source 1] (New Text Document.txt - TEXT)
Operating Voltage: The standard operating voltage of the machine is 220V

[Source 2] (label.png - IMAGE)
MACHINE LABEL Voltage: 110V Manufactured: 2022

CONFLICTS DETECTED:
- New Text Document.txt: Operating Voltage is 220V
- label.png: Voltage is 110V

Query: what is the operating voltage?

Instructions:
1. Present BOTH/ALL perspectives found in the evidence
2. Cite sources for each perspective using [Source X]
3. DO NOT choose one side - present all views objectively
4. Format: "According to [Source X], ... However, [Source Y] states..."
5. End with: "Note: Conflicting information detected. Please verify with original sources."

Response:"""
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Multimodal RAG System"
            }
            
            payload = {
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 200
            }
            
            print("🔄 Sending request to OpenRouter...")
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            print(f"Status: {response.status_code}")
            result = response.json()
            
            if response.is_success:
                answer = result['choices'][0]['message']['content']
                print(f"\n✅ SUCCESS!\nAnswer: {answer}\n")
            else:
                print(f"\n❌ ERROR\nResponse: {result}\n")
                
    except Exception as e:
        print(f"\n❌ EXCEPTION: {type(e).__name__}: {e}\n")

if __name__ == "__main__":
    asyncio.run(test_openrouter_conflict())
