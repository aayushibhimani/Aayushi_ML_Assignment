import logging
import json
from datetime import datetime
from typing import Dict, Any
import os

logger = logging.getLogger(__name__)

class CostTracker:
    
    def __init__(self, log_file: str = "logs/usage.log"):
        self.log_file = log_file
        self.usage_history = []
        self.provider_stats = {}

        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        logger.info("Initialized CostTracker")
    
    def record_usage(self, provider_name: str, prompt_tokens: int, completion_tokens: int,
                     cost: float, success: bool, duration: float):
        timestamp = datetime.now().isoformat()

        usage_data = {
            "timestamp": timestamp,
            "provider": provider_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost": cost,
            "success": success,
            "duration_seconds": round(duration, 4)
        }

        self.usage_history.append(usage_data)
        if len(self.usage_history) > 100:
            self.usage_history.pop(0)

        if provider_name not in self.provider_stats:
            self.provider_stats[provider_name] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_cost": 0.0,
                "total_latency": 0.0,
            }
        
        stats = self.provider_stats[provider_name]
        stats["total_requests"] += 1

        if success:
            stats["successful_requests"] += 1
            stats["total_prompt_tokens"] += prompt_tokens
            stats["total_completion_tokens"] += completion_tokens
            stats["total_cost"] += cost
            stats["total_latency"] += duration  
        else:
            stats["failed_requests"] += 1

        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(usage_data) + "\n")
        except Exception as e:
            logger.error(f"Error writing to usage log: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        total_cost = sum(stats["total_cost"] for stats in self.provider_stats.values())
        total_tokens = sum(stats["total_prompt_tokens"] + stats["total_completion_tokens"] 
                          for stats in self.provider_stats.values())

        for provider in self.provider_stats:
            provider_data = self.provider_stats[provider]
            if provider_data["successful_requests"] > 0:
                avg_latency = provider_data["total_latency"] / provider_data["successful_requests"]
            else:
                avg_latency = None
            provider_data["avg_latency"] = round(avg_latency, 4) if avg_latency else "N/A"

        return {
            "overall": {
                "total_cost": round(total_cost, 6),
                "total_tokens": total_tokens,
                "total_requests": sum(stats["total_requests"] for stats in self.provider_stats.values())
            },
            "providers": self.provider_stats,
            "recent_requests": self.usage_history[-10:]
        }

