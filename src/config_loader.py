# src/config_loader.py
import yaml
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ConfigLoader:
    
    def __init__(self, config_path: str = "providers.yaml"):
        self.config_path = config_path
    
    def load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file {self.config_path} not found!")

        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)

        self._validate_config(config)
        return config

    def _validate_config(self, config: Dict[str, Any]):
        
        if "providers" not in config or not isinstance(config["providers"], list):
            raise ValueError("Config file must contain a 'providers' list")

        required_fields = ["name", "type", "endpoint", "model", "cost_per_1k_tokens"]

        valid_types = ["google_gemini", "mistral", "deepseek"]  

        for provider in config["providers"]:
            for field in required_fields:
                if field not in provider:
                    raise ValueError(f"Provider missing required field: {field}")

            if provider["type"] not in valid_types:
                raise ValueError(f"Invalid provider type: {provider['type']}")

        logger.info(f"Loaded configuration with {len(config['providers'])} providers")
