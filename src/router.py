# src/router.py
import logging
import time
from typing import Dict, Any, List
from src.request_handler import RequestHandler
from src.cost_tracker import CostTracker

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, threshold: int = 3, cooldown: int = 60):
        self.threshold = threshold
        self.cooldown = cooldown  
        self.failure_timestamps = []  
        self.state = "closed"  # states = closed, open, half-open
        self.last_failure_time = 0
        self.half_open_attempts = 0  # Allow one test attempt in half-open state

    def record_success(self):
        self.failure_timestamps = []
        if self.state != "closed":
            logger.info("Circuit breaker: Provider recovered, closing circuit.")
        self.state = "closed"
        self.half_open_attempts = 0

    def record_failure(self):
        now = time.time()
        self.failure_timestamps.append(now)
        self.failure_timestamps = [ts for ts in self.failure_timestamps if now - ts < self.cooldown]
        if len(self.failure_timestamps) >= self.threshold:
            self.state = "open"
            self.last_failure_time = now
            self.half_open_attempts = 0
            logger.warning(f"Circuit breaker OPENED: Provider unavailable. Cooling down for {self.cooldown} seconds.")

    def can_attempt(self) -> bool:
        now = time.time()
        if self.state == "closed":
            return True
        elif self.state == "open":
            time_remaining = self.cooldown - (now - self.last_failure_time)
            if time_remaining <= 0:
                self.state = "half-open"
                self.half_open_attempts = 0
                logger.info("Circuit breaker HALF-OPEN: Allowing one test request.")
                return True
            else:
                logger.warning(f"Circuit breaker BLOCKED: Cooling down for {round(time_remaining, 2)} more seconds.")
                return False
        elif self.state == "half-open":
            if self.half_open_attempts < 1:
                self.half_open_attempts += 1
                logger.info("Circuit breaker HALF-OPEN: Test request allowed.")
                return True
            else:
                logger.warning("Circuit breaker HALF-OPEN: Test already attempted; blocking further requests.")
                return False
        return True

class LLMRouter:
    def __init__(self, providers_config: Dict[str, Any], cost_tracker: CostTracker):
        self.providers_config = providers_config["providers"]
        self.cost_tracker = cost_tracker
        self.request_handler = RequestHandler()
        self.circuit_breakers = {
            provider["name"]: CircuitBreaker(threshold=3, cooldown=60)
            for provider in self.providers_config
        }

    def _compute_dynamic_score(self, provider: Dict[str, Any]) -> float:
        base_cost = provider["cost_per_1k_tokens"]
        provider_name = provider["name"]
        stats = self.cost_tracker.provider_stats.get(provider_name, {})
        total_requests = stats.get("total_requests", 0)
        failed_requests = stats.get("failed_requests", 0)
        failure_ratio = (failed_requests / total_requests) if total_requests > 0 else 0

        #Penalizing recent failures which are within 5 minutes
        cb = self.circuit_breakers.get(provider_name)
        recency_factor = 1.0
        if cb and time.time() - cb.last_failure_time < 5 * 60:
            recency_factor = 1.5

        avg_latency = stats.get("avg_latency", None)
        latency_factor = 1.0
        if avg_latency and avg_latency > 5:
            latency_factor = 1.2

        score = base_cost * (1 + failure_ratio * recency_factor) * latency_factor
        logger.debug(f"Provider {provider_name} dynamic score: {score:.6f} "
                     f"(Cost: {base_cost}, Fail Ratio: {failure_ratio:.2f}, Latency: {avg_latency}, Recency Factor: {recency_factor}, Latency Factor: {latency_factor})")
        return score

    def _get_sorted_providers(self) -> List[Dict[str, Any]]:
        
        available_providers = []
        for provider in self.providers_config:
            cb = self.circuit_breakers.get(provider["name"])
            if cb and not cb.can_attempt():
                logger.info(f"Skipping {provider['name']} due to circuit breaker OPEN.")
            else:
                available_providers.append(provider)
        sorted_providers = sorted(available_providers, key=self._compute_dynamic_score)
        logger.info(f"Provider selection order: {[p['name'] for p in sorted_providers]}")
        return sorted_providers

    async def generate(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> Dict[str, Any]:
        
        overall_start = time.time()
        errors = []
        sorted_providers = self._get_sorted_providers()
        if not sorted_providers:
            raise Exception("No available providers due to circuit breaker restrictions.")

        for provider in sorted_providers:
            provider_name = provider["name"]
            circuit_breaker = self.circuit_breakers.get(provider_name)
            attempt_start = time.time()
            try:
                logger.info(f"Attempting provider: {provider_name}")
                response = await self.request_handler.call_provider(
                    provider=provider,
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                if not response or "text" not in response:
                    logger.warning(f"Empty response from {provider_name}")
                    raise ValueError(f"Empty response from {provider_name}")

                attempt_duration = time.time() - attempt_start
                logger.info(f"Provider {provider_name} responded in {round(attempt_duration, 2)}s.")

                prompt_tokens = response.get("prompt_tokens", 0)
                completion_tokens = response.get("completion_tokens", 0)
                total_tokens = response.get("total_tokens", prompt_tokens + completion_tokens)
                cost = self._calculate_cost(provider, prompt_tokens, completion_tokens)

                self.cost_tracker.record_usage(provider_name, prompt_tokens, completion_tokens, cost, True, time.time() - overall_start)

                if circuit_breaker:
                    circuit_breaker.record_success()

                logger.info(f"Success: {provider_name} used with cost {cost} and response time {round(attempt_duration, 2)}s.")
                return {
                    "provider_used": provider_name,
                    "cost": cost,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "response": response["text"]
                }

            except Exception as e:
                attempt_duration = time.time() - attempt_start
                logger.error(f"Provider {provider_name} failed in {round(attempt_duration,2)}s: {str(e)}. Attempting fallback...")
                errors.append(f"{provider_name} failed: {str(e)}")
                self.cost_tracker.record_usage(provider_name, 0, 0, 0, False, time.time() - overall_start)
                if circuit_breaker:
                    circuit_breaker.record_failure()

        logger.error("All providers failed")
        raise Exception(f"All providers failed. Errors: {'; '.join(errors)}")

    def _calculate_cost(self, provider: Dict[str, Any], prompt_tokens: int, completion_tokens: int) -> float:

        prompt_cost_rate = provider.get("prompt_cost_per_1k_tokens", provider["cost_per_1k_tokens"])
        completion_cost_rate = provider.get("completion_cost_per_1k_tokens", provider["cost_per_1k_tokens"])
        prompt_cost = (prompt_tokens / 1000) * prompt_cost_rate
        completion_cost = (completion_tokens / 1000) * completion_cost_rate
        return round(prompt_cost + completion_cost, 6)
