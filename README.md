# MultiLLM Cost-Optimized API  

A plug-and-play microservice that intelligently routes user requests to multiple low-cost and reliable LLM providers, using fallback and token/cost tracking to ensure efficient and consistent text generation.

## Installation & Usage  
### 1️.Clone the Repository
git clone https://github.com/aayushibhimani/Aayushi_ML_Assignment.git  
cd Aayushi_ML_Assignment

### 2.Install Dependencies
pip install -r requirements.txt

### 3.Set API Keys in providers.yaml
Update the providers.yaml file with your API keys and provider configurations.

### 4.Run 
uvicorn app:app --host 127.0.0.1 --port 8000

### 5. Access the User Interface
Open the ui/index.html file in your web browser to test prompts and interact with the API. 


## Approach
* **Config-Driven Provider Selection:** Providers are defined in providers.yaml, making it easy to add/remove models.  
* **Routing & Fallback Logic:** The request first tries the cheapest provider. If it fails (error, timeout, rate limit), it automatically retries with the next provider.  
* **Token & Cost Tracking:** Logs token usage and estimated cost per request in logs/usage.log.  
* **Modular Structure:** Each component (routing, requests, tracking) is in a separate module for maintainability.  

## How Each File Works
* **app.py** - Main FastAPI app, loads configuration, exposes API endpoints (/generate).
* **providers.yaml** - Defines available LLM providers, their API keys, and cost per 1K tokens.
* **config_loader.py** - Reads and validates providers.yaml.
* **router.py** - Routes requests to the cheapest working LLM provider.
* **request_handler.py** - Calls the selected provider's API and handles errors.
* **cost_tracker.py** - Logs and calculates token usage & cost per request.
* **index.html, script.js, styles.css** - Simple UI for testing prompts.


