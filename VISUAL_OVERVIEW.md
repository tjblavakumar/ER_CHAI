# LiteLLM Integration - Visual Overview

## Configuration Switch

```
┌─────────────────────────────────────────────────────────────┐
│                    config.yaml                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  llm_provider: "bedrock"  ─OR─  llm_provider: "litellm"   │
│         │                              │                   │
│         ↓                              ↓                   │
│  ┌─────────────────┐          ┌─────────────────────────┐ │
│  │ AWS Bedrock     │          │ LiteLLM (Internal API)  │ │
│  ├─────────────────┤          ├─────────────────────────┤ │
│  │ aws_region      │          │ litellm_api_base        │ │
│  │ aws_access_key  │          │ litellm_api_key         │ │
│  │ bedrock_model   │          │ litellm_model_id        │ │
│  └─────────────────┘          └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Application Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                    ER_CHAI Application                           │
│                      (FastAPI Backend)                           │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               │ Startup: load_config()
                               ↓
┌──────────────────────────────────────────────────────────────────┐
│                create_llm_client(config)                         │
│              (Factory Function - NEW)                            │
│                                                                  │
│  if config.llm_provider == "bedrock":                           │
│      return BedrockClient(...)                                  │
│  elif config.llm_provider == "litellm":                         │
│      return LiteLLMClient(...)                                  │
└──────────────────┬───────────────────────┬───────────────────────┘
                   │                       │
      ┌────────────┘                       └──────────┐
      ↓                                               ↓
┌─────────────────────┐                  ┌──────────────────────────┐
│   BedrockClient     │                  │    LiteLLMClient         │
│   (AWS Bedrock)     │                  │    (Internal API)        │
├─────────────────────┤                  ├──────────────────────────┤
│ - Uses boto3        │                  │ - Uses httpx             │
│ - invoke_model()    │                  │ - POST to /v1/chat/...   │
│ - Anthropic format  │                  │ - OpenAI-compatible      │
└─────────────────────┘                  └──────────────────────────┘
           │                                         │
           └──────────────┬──────────────────────────┘
                          │
           Both implement: LLMClient.invoke(prompt)
                          │
                          ↓
┌──────────────────────────────────────────────────────────────────┐
│                    Application Services                          │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐  ┌───────────────────────────────┐   │
│  │  AIAssistantHandler  │  │    SummaryGenerator           │   │
│  │                      │  │                               │   │
│  │  - Chart Q&A         │  │  - Executive summaries        │   │
│  │  - Modifications     │  │  - Trend analysis             │   │
│  │  - Suggestions       │  │                               │   │
│  └──────────────────────┘  └───────────────────────────────┘   │
│                                                                  │
│  Both use: await self._llm_client.invoke(prompt)                │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow Example

### User Request: "Change the chart to a bar chart"

```
1. Frontend
   │
   │ HTTP POST /api/ai/chat
   ↓
2. Backend API Endpoint
   │
   │ ai_assistant.handle_message(session_id, message, context)
   ↓
3. AIAssistantHandler
   │
   │ await self._llm_client.invoke(prompt)
   ↓
4. LLM Client (Bedrock OR LiteLLM)
   │
   ├─ If Bedrock:
   │  └→ boto3.client.invoke_model()
   │     └→ AWS Bedrock API
   │
   └─ If LiteLLM:
      └→ httpx.AsyncClient.post()
         └→ https://martinai-preview-api.frb.gov/v1/chat/completions
   │
   ↓
5. LLM Response (JSON with chart delta)
   │
   ↓
6. Parse Response → ChartConfigDelta
   │
   ↓
7. Return to Frontend → Update Chart
```

## Key Abstraction Points

### Before Integration (Bedrock Only)

```python
# main.py
bedrock_client = boto3.client("bedrock-runtime", ...)

# ai_assistant.py
class AIAssistantHandler:
    def __init__(self, bedrock_client, model_id):
        self._bedrock = bedrock_client
        self._model_id = model_id
    
    async def _invoke_bedrock(self, prompt):
        # Bedrock-specific code
        response = self._bedrock.invoke_model(...)
        return response_body["content"][0]["text"]
```

### After Integration (Provider-Agnostic)

```python
# main.py
from backend.services.llm_client import create_llm_client

llm_client = create_llm_client(config)  # Auto-selects provider

# ai_assistant.py  
class AIAssistantHandler:
    def __init__(self, llm_client: LLMClient):
        self._llm_client = llm_client
    
    # Just call the abstraction - provider doesn't matter!
    response = await self._llm_client.invoke(prompt)
```

## Configuration File Comparison

### config.yaml (Bedrock)

```yaml
fred_api_key: "abc123"
llm_provider: "bedrock"          # ← Provider selection
aws_region: "us-east-1"
aws_access_key_id: "AKIA..."
bedrock_model_id: "us.anthropic.claude-sonnet-4-5..."
```

### config.yaml (LiteLLM)

```yaml
fred_api_key: "abc123"
llm_provider: "litellm"          # ← Provider selection  
litellm_api_base: "https://martinai-preview-api.frb.gov"
litellm_api_key: "xyz789"
litellm_model_id: "claude-3-5-sonnet-20241022"
```

## API Request Format

### Bedrock Request

```python
# boto3.client("bedrock-runtime").invoke_model()
{
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 8192,
    "messages": [
        {"role": "user", "content": "prompt here"}
    ]
}
```

### LiteLLM Request (OpenAI-Compatible)

```python
# POST https://martinai-preview-api.frb.gov/v1/chat/completions
{
    "model": "claude-3-5-sonnet-20241022",
    "messages": [
        {"role": "user", "content": "prompt here"}
    ],
    "max_tokens": 8192
}

Headers:
    Authorization: Bearer {api_key}
    Content-Type: application/json
```

## File Structure

```
ER_CHAI/
├── backend/
│   ├── models/
│   │   └── schemas.py           # ✏️ MODIFIED: Added LiteLLM config
│   ├── services/
│   │   ├── llm_client.py        # 🆕 NEW: LLM abstraction layer
│   │   ├── ai_assistant.py      # ✏️ MODIFIED: Uses LLMClient
│   │   ├── summary_generator.py # ✏️ MODIFIED: Uses LLMClient
│   │   └── ...
│   └── main.py                  # ✏️ MODIFIED: Creates LLM clients
│
├── config.yaml.example          # ✏️ MODIFIED: Both providers
├── config.yaml.litellm.example  # 🆕 NEW: LiteLLM-specific
│
├── LLM_INTEGRATION_GUIDE.md     # 🆕 NEW: Technical guide
├── LLM_INTEGRATION_SUMMARY.md   # 🆕 NEW: Change summary
└── README_LITELLM_INTEGRATION.md # 🆕 NEW: Quick start guide
```

## Benefits Visualization

```
┌─────────────────────────────────────────────────────────────┐
│                    BEFORE                                   │
├─────────────────────────────────────────────────────────────┤
│  Services → Bedrock Client (boto3) → AWS Bedrock           │
│                                                             │
│  ❌ Tightly coupled to AWS                                 │
│  ❌ Can't use internal API                                 │
│  ❌ Hard to test                                           │
└─────────────────────────────────────────────────────────────┘

                          ↓ REFACTORED ↓

┌─────────────────────────────────────────────────────────────┐
│                     AFTER                                   │
├─────────────────────────────────────────────────────────────┤
│  Services → LLMClient (abstract) → Provider Client          │
│                                         ↓                   │
│                        ┌────────────────┴────────────────┐  │
│                        │                                 │  │
│                  BedrockClient              LiteLLMClient  │
│                        ↓                         ↓         │
│                   AWS Bedrock          Internal API       │
│                                                            │
│  ✅ Provider-agnostic                                     │
│  ✅ Use internal API                                      │
│  ✅ Easy to test                                          │
│  ✅ Future-proof (add OpenAI, etc.)                       │
└────────────────────────────────────────────────────────────┘
```

---

**Summary**: The application now has a clean abstraction layer that allows you to switch between AWS Bedrock and your internal LiteLLM API just by changing configuration - no code changes needed!
