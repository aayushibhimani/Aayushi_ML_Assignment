# app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import logging
import os
from src.router import LLMRouter
from src.config_loader import ConfigLoader
from src.cost_tracker import CostTracker
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/usage.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

os.makedirs("logs", exist_ok=True)

app = FastAPI(title="MultiLLM Cost-Optimized API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config_loader = ConfigLoader("providers.yaml")
providers_config = config_loader.load_config()

cost_tracker = CostTracker()
router = LLMRouter(providers_config, cost_tracker)

class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 1000
    temperature: float = 0.7

class GenerateResponse(BaseModel):
    provider_used: str
    cost: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    response: str

@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    try:
        result = await router.generate(
            prompt=request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        return result
    except Exception as e:
        logger.error(f"Error in generate endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    return cost_tracker.get_stats()

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
