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


##  Key Features
- **Config-Driven Provider Management**
  - Providers defined in `providers.yaml` for easy management.
  - Customize API keys, costs, timeouts, and retries from one central location.
- **Smart Routing & Fallback Logic**
  - Prioritizes providers based on the lowest cost per 1K tokens.
  - Automatically falls back to the next cheapest available provider upon encountering an error, timeout, or rate limit.
- **Circuit Breaker with Penalty Duration**
  - Providers temporarily disabled after 3 consecutive failures.
  - Circuit breaker cooldown period is set to 60 seconds.
  - Providers with recent failures (within 5 minutes) are penalized, decreasing their selection priority.
  - Clearly Defined Circuit Breaker States:
    - Closed: Provider is operating normally; requests are routed without restrictions.
    - Open: Provider disabled after consecutive failures; temporarily stops sending requests for the cooldown period.
    - Half-Open: After the cooldown period, the provider is tested with a limited number of trial requests. If successful, the state returns to Closed, if unsuccessful, the state reverts to Open.
    
- **Real-Time Comprehensive Token & Cost Tracking**
  - Logs detailed usage statistics including - Prompt tokens, Completion tokens, Total tokens, Cost per request, Success/failure status
  - Usage data stored in `logs/usage.logs`




## How Each File Works
* **app.py** - Main FastAPI app, loads configuration, exposes API endpoints (/generate).
* **providers.yaml** - Defines available LLM providers, their API keys, and cost per 1K tokens.
* **config_loader.py** - Loads and validates provider configurations from providers.yaml.
* **router.py** - Routes requests intelligently, prioritizing providers based on cost, reliability, and recent performance.
* **request_handler.py** - Handles API calls, responses, error handling, and retries per provider.
* **cost_tracker.py** - Logs and calculates token usage & cost per request.
* **index.html, script.js, styles.css** - Simple UI for testing prompts.


