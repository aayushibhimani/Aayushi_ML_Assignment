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
        """Call Mistral AI API"""
        endpoint = provider["endpoint"]
        api_key = provider["api_key"]
        model = provider["model"]

        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"  # Mistral requires Bearer token
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

                        # Extract response text and token counts
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
                        await asyncio.sleep(1)  # Simple backoff
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
                "stream": False  # Non-streaming request
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


    async def _call_google_gemini(self, provider: Dict[str, Any], prompt: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        api_key = provider["api_key"]
        model = provider["model"]

        try:
            genai.configure(api_key=api_key)
            client = genai.GenerativeModel(model)

            token_count_response = client.count_tokens(prompt)
            prompt_tokens = token_count_response.total_tokens 

            # Generate response
            response = client.generate_content(
                prompt,
                generation_config={"max_output_tokens": max_tokens, "temperature": temperature}
            )

            if not response or not hasattr(response, "text"):
                raise ValueError("Empty response from Google Gemini")

            text = response.text

            completion_token_response = client.count_tokens(text)
            completion_tokens = completion_token_response.total_tokens

            total_tokens = prompt_tokens + completion_tokens

            return {
                "text": text,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            }

        except Exception as e:
            logger.error(f"Google Gemini API error: {str(e)}")
            raise

