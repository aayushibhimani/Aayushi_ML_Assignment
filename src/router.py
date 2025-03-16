#src/router.py
import logging
import time
from typing import Dict, Any
from src.request_handler import RequestHandler
from src.cost_tracker import CostTracker

logger = logging.getLogger(__name__)

class LLMRouter:

    def __init__(self, providers_config: Dict[str, Any], cost_tracker: CostTracker):
        self.providers_by_priority = sorted(
            providers_config["providers"],
            key=lambda p: p["cost_per_1k_tokens"]
        )
        self.cost_tracker = cost_tracker
        self.request_handler = RequestHandler()

    async def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> Dict[str, Any]:
        start_time = time.time()
        errors = []

        for provider in self.providers_by_priority:
            provider_name = provider["name"]
            try:
                logger.info(f"Trying provider: {provider_name}")

                response = await self.request_handler.call_provider(
                    provider=provider,
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )

                if not response or "text" not in response:
                    raise ValueError(f"Empty response from {provider_name}")

                prompt_tokens = response.get("prompt_tokens", 0)
                completion_tokens = response.get("completion_tokens", 0)
                total_tokens = response.get("total_tokens", prompt_tokens + completion_tokens)
                cost = self._calculate_cost(provider, prompt_tokens, completion_tokens)

                self.cost_tracker.record_usage(provider_name, prompt_tokens, completion_tokens, cost, True, time.time() - start_time)

                return {
                    "provider_used": provider_name,
                    "cost": cost,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "response": response["text"]
                }

            except Exception as e:
                errors.append(f"{provider_name} failed: {str(e)}")
                self.cost_tracker.record_usage(provider_name, 0, 0, 0, False, time.time() - start_time)

        raise Exception(f"All providers failed. Errors: {'; '.join(errors)}")

    def _calculate_cost(self, provider, prompt_tokens, completion_tokens):
        """Calculates cost separately for prompt & completion tokens"""
        prompt_cost_rate = provider.get("prompt_cost_per_1k_tokens", provider["cost_per_1k_tokens"])
        completion_cost_rate = provider.get("completion_cost_per_1k_tokens", provider["cost_per_1k_tokens"])

        prompt_cost = (prompt_tokens / 1000) * prompt_cost_rate
        completion_cost = (completion_tokens / 1000) * completion_cost_rate

        return round(prompt_cost + completion_cost, 6)
