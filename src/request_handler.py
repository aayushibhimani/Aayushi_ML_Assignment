# src/request_handler.py
import aiohttp
import logging
import json
import asyncio
from typing import Dict, Any
import google.generativeai as genai

logger = logging.getLogger(__name__)

class RequestHandler:
   
    async def call_provider(self, provider: Dict[str, Any], prompt: str, 
                           max_tokens: int, temperature: float) -> Dict[str, Any]:
        
        provider_type = provider["type"].lower()
        
        if provider_type == "google_gemini":
            return await self._call_google_gemini(provider, prompt, max_tokens, temperature)
        elif provider_type == "mistral":
            return await self._call_mistral(provider, prompt, max_tokens, temperature)  
        elif provider_type == "deepseek":
            return await self._call_deepseek(provider, prompt, max_tokens, temperature)
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

    async def _call_mistral(self, provider: Dict[str, Any], prompt: str, 
                            max_tokens: int, temperature: float) -> Dict[str, Any]:
        endpoint = provider["endpoint"]
        api_key = provider["api_key"]
        model = provider["model"]

        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"  
            }

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            timeout = aiohttp.ClientTimeout(total=provider.get("timeout", 30))
            max_retries = provider.get("max_retries", 1)

            for attempt in range(max_retries + 1):
                try:
                    async with session.post(endpoint, headers=headers, json=payload, timeout=timeout) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Mistral API error: {error_text}")
                            raise Exception(f"Mistral API returned {response.status}: {error_text}")

                        result = await response.json()

                        text = result["choices"][0]["message"]["content"]
                        prompt_tokens = result["usage"]["prompt_tokens"]
                        completion_tokens = result["usage"]["completion_tokens"]
                        total_tokens = result["usage"]["total_tokens"]

                        return {
                            "text": text,
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens
                        }

                except asyncio.TimeoutError:
                    if attempt < max_retries:
                        logger.warning(f"Timeout for Mistral API, attempt {attempt+1}/{max_retries+1}")
                        continue
                    raise Exception("Mistral API timeout")

                except Exception as e:
                    if attempt < max_retries:
                        logger.warning(f"Error calling Mistral API, attempt {attempt+1}/{max_retries+1}: {str(e)}")
                        await asyncio.sleep(1) 
                        continue
                    raise

    async def _call_deepseek(self, provider: Dict[str, Any], prompt: str, 
                         max_tokens: int, temperature: float) -> Dict[str, Any]:
   
        endpoint = provider["endpoint"]
        api_key = provider["api_key"]
        model = provider["model"]

        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False  
            }

            timeout = aiohttp.ClientTimeout(total=provider.get("timeout", 30))
            max_retries = provider.get("max_retries", 2)

            for attempt in range(max_retries + 1):
                try:
                    async with session.post(endpoint, headers=headers, json=payload, timeout=timeout) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"DeepSeek API error: {error_text}")
                            raise Exception(f"DeepSeek API returned {response.status}: {error_text}")

                        result = await response.json()

                        text = result["choices"][0]["message"]["content"]
                        prompt_tokens = result.get("usage", {}).get("prompt_tokens", 0)
                        completion_tokens = result.get("usage", {}).get("completion_tokens", 0)
                        total_tokens = prompt_tokens + completion_tokens

                        return {
                            "text": text,
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens
                        }

                except asyncio.TimeoutError:
                    if attempt < max_retries:
                        logger.warning(f"Timeout for DeepSeek API, attempt {attempt+1}/{max_retries+1}")
                        continue
                    raise Exception("DeepSeek API timeout")

                except Exception as e:
                    if attempt < max_retries:
                        logger.warning(f"Error calling DeepSeek API, attempt {attempt+1}/{max_retries+1}: {str(e)}")
                        await asyncio.sleep(1) 
                        continue
                    raise


    async def _call_google_gemini(self, provider: Dict[str, Any], prompt: str,
                                    max_tokens: int, temperature: float) -> Dict[str, Any]:
        base_endpoint = "https://generativelanguage.googleapis.com/v1beta/models/"
        model_name = provider["model"]
        endpoint = f"{base_endpoint}{model_name}:generateContent"

        api_key = provider.get("api_key", "").strip()
        if not api_key:
            logger.error("Google Gemini API key is missing")
            raise Exception("Google Gemini API key is missing")

        headers = {
            "Content-Type": "application/json"
        }
        params = {"key": api_key}

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature
            }
        }

        timeout = aiohttp.ClientTimeout(total=provider.get("timeout", 30))
        max_retries = provider.get("max_retries", 2)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for attempt in range(max_retries + 1):
                try:
                    async with session.post(endpoint, headers=headers, json=payload, params=params) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Gemini API error: {error_text}")
                            raise Exception(f"Gemini API returned {response.status}: {error_text}")

                        result = await response.json()

                        if "candidates" not in result or not result["candidates"]:
                            raise Exception("Empty response from Gemini API")

                        text = result["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if not text:
                            raise Exception("No text output in Gemini API response")

                        usage = result.get("usageMetadata", {})
                        prompt_tokens = usage.get("promptTokenCount", 0)
                        completion_tokens = usage.get("candidatesTokenCount", 0)
                        total_tokens = prompt_tokens + completion_tokens

                        logger.debug("Gemini call succeeded on attempt %d", attempt + 1)
                        return {
                            "text": text,
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                            "total_tokens": total_tokens
                        }
                except asyncio.TimeoutError:
                    logger.warning("Timeout for Gemini API, attempt %d/%d", attempt + 1, max_retries + 1)
                    if attempt == max_retries:
                        raise Exception("Gemini API timeout")
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.warning("Error calling Gemini API, attempt %d/%d: %s", attempt + 1, max_retries + 1, str(e))
                    if attempt == max_retries:
                        raise
                    await asyncio.sleep(1)