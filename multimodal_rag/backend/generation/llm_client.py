"""LLM client for Ollama with fallback support."""
import httpx
from typing import Optional, Dict, Any
import json

from backend.config import settings
from backend.utils.logger import logger


class LLMClient:
    """Client for LLM inference with Ollama and API fallback."""
    
    def __init__(self):
        self.ollama_url = f"{settings.ollama_base_url}/api/generate"
        self.timeout = 300.0  # 5 minutes timeout for Ollama (local model can be slow)
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> str:
        """
        Generate text using LLM with automatic fallback.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (lower = more deterministic)
            max_tokens: Maximum response length
        
        Returns:
            Generated text
        """
        errors = []
        
        # ⚡ ULTRA FAST MODE: Try Gemini FIRST (2-3 second responses!)
        if settings.gemini_api_key:
            try:
                logger.logger.info("⚡ Trying Gemini API (PRIMARY - Ultra Fast!)...")
                response = await self._generate_gemini(prompt, temperature, max_tokens)
                if response and not response.startswith("Error:"):
                    logger.logger.info("✅ Generated response using Gemini API (ULTRA FAST)")
                    return response
            except Exception as e:
                error_msg = f"Gemini: {type(e).__name__}: {str(e)[:150]}"
                errors.append(error_msg)
                logger.logger.warning(f"Gemini API failed: {error_msg}")
        
        # Fallback to OpenRouter API
        if settings.openrouter_api_key:
            try:
                logger.logger.info("🔄 Falling back to OpenRouter API...")
                response = await self._generate_openrouter(prompt, temperature, max_tokens)
                if response and not response.startswith("Error:"):
                    logger.logger.info("✅ Generated response using OpenRouter API")
                    return response
            except Exception as e:
                error_msg = f"OpenRouter: {type(e).__name__}: {str(e)[:150]}"
                errors.append(error_msg)
                logger.logger.warning(f"OpenRouter API failed: {error_msg}")
        
        # Last resort: Ollama (local model - slower but keeps features working)
        try:
            logger.logger.info("🔄 Falling back to Ollama (local)...")
            response = await self._generate_ollama(prompt, temperature, max_tokens)
            if response and not response.startswith("Error:"):
                logger.logger.info("✅ Generated response using Ollama (local)")
                return response
        except Exception as e:
            error_msg = f"Ollama: {type(e).__name__}: {str(e)[:200]}"
            errors.append(error_msg)
            logger.logger.warning(f"Ollama failed: {error_msg}")
        
        # All methods failed - return detailed error
        all_errors = " | ".join(errors) if errors else "All backends unavailable"
        logger.logger.error(f"🚨 All LLM methods failed: {all_errors}")
        return f"Error: Unable to generate response. {all_errors}"
    
    async def _generate_ollama(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using local Ollama instance."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "model": settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            response = await client.post(self.ollama_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '').strip()
    
    async def _generate_openrouter(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using OpenRouter API (FAST cloud LLM)."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            headers = {
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000",  # Required by OpenRouter
                "X-Title": "Multimodal RAG System"  # Optional
            }
            
            payload = {
                "model": settings.fallback_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
    
    async def _generate_gemini(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using Google Gemini API (ULTRA FAST - 1-2 seconds with 2.0 Flash!)."""
        import asyncio
        
        # Models to try in order of speed (2.0 Flash is fastest)
        models = ["gemini-2.0-flash", "gemini-1.5-flash"]
        
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": 0.8,
                "topK": 10
            }
        }
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            for model in models:
                # Try with retry logic for rate limits
                for retry in range(3):
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.gemini_api_key}"
                        
                        response = await client.post(url, headers=headers, json=payload)
                        
                        # Check for rate limit (429)
                        if response.status_code == 429:
                            retry_after = min(2 ** retry, 8)  # Max 8 seconds
                            logger.logger.warning(f"⏳ Rate limited on {model}, retrying in {retry_after}s...")
                            await asyncio.sleep(retry_after)
                            continue
                        
                        response.raise_for_status()
                        result = response.json()
                        return result['candidates'][0]['content']['parts'][0]['text'].strip()
                        
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 429 and retry < 2:
                            await asyncio.sleep(2 ** retry)
                            continue
                        # Try next model
                        logger.logger.warning(f"⚠️ {model} failed: {e.response.status_code}, trying next model...")
                        break
                    except Exception as e:
                        logger.logger.warning(f"⚠️ {model} error: {str(e)[:100]}")
                        break
        
        # All models failed
        raise Exception("All Gemini models failed after retries")
    
    def generate_sync(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> str:
        """Synchronous version of generate (for testing)."""
        import asyncio
        return asyncio.run(self.generate(prompt, temperature, max_tokens))
