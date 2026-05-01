# LLM Provider Integration Guide

## Overview

This guide documents the integration of LiteLLM API support alongside the existing AWS Bedrock provider, allowing the ER_CHAI application to use either provider for all AI functionality.

## Architecture

### 1. **LLM Client Abstraction Layer** (`backend/services/llm_client.py`)

A new abstraction layer has been created with:

- **`LLMClient` (Abstract Base Class)**: Defines the common interface for all LLM providers
- **`BedrockClient`**: Implementation for AWS Bedrock
- **`LiteLLMClient`**: Implementation for LiteLLM API (OpenAI-compatible endpoint)
- **`create_llm_client()`**: Factory function that creates the appropriate client based on configuration

### 2. **Configuration Schema** (`backend/models/schemas.py`)

Updated `AppConfig` to include:

```python
# Provider selection
llm_provider: str = "bedrock"  # or "litellm"

# AWS Bedrock Configuration
aws_region: str | None = None
aws_access_key_id: str | None = None
aws_secret_access_key: str | None = None
aws_session_token: str | None = None
bedrock_model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
bedrock_vision_model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

# LiteLLM Configuration  
litellm_api_base: str | None = None  # e.g., "https://martinai-preview-api.frb.gov"
litellm_api_key: str | None = None
litellm_model_id: str = "claude-3-5-sonnet-20241022"
litellm_vision_model_id: str = "claude-3-5-sonnet-20241022"
```

### 3. **Configuration File** (`config.yaml.example`)

Updated with sections for both providers and clear instructions on which settings are needed for each provider.

## Implementation Status

### ✅ Completed

1. **LLM Client Abstraction** - Fully implemented with:
   - Abstract base class
   - Bedrock client implementation
   - LiteLLM client implementation (OpenAI-compatible API)
   - Factory function for client creation
   - Retry logic and error handling

2. **Configuration Schema** - Updated to support both providers

3. **Configuration Example** - Updated with clear documentation

### 🔄 In Progress / Needs Completion

1. **AI Assistant Handler** (`backend/services/ai_assistant.py`)
   - **Status**: Partially updated (imports updated, but constructor needs refactoring)
   - **TODO**: 
     - Update `__init__` to accept `LLMClient` instead of `bedrock_client`
     - Replace all `await self._invoke_bedrock(prompt)` calls with `await self._llm_client.invoke(prompt)`
     - Remove the old `_invoke_bedrock` method

2. **Summary Generator** (`backend/services/summary_generator.py`)
   - **Status**: Not yet started
   - **TODO**: Same refactoring pattern as AI Assistant

3. **Image Analyzer** (`backend/services/image_analyzer.py`)
   - **Status**: Not yet started
   - **TODO**: Same refactoring pattern

4. **Main Application** (`backend/main.py`)
   - **Status**: Not yet started
   - **TODO**:
     - Replace direct `boto3.client("bedrock-runtime")` creation with `create_llm_client(config)`
     - Update service initializations to pass LLM clients
     - Update Bedrock status endpoint to be provider-agnostic

5. **Tests** (`tests/`)
   - **TODO**: Update all tests to use the new LLM client abstraction

## Usage Instructions

### For AWS Bedrock

```yaml
# config.yaml
fred_api_key: "YOUR_FRED_API_KEY"
llm_provider: "bedrock"
aws_region: "us-east-1"
# AWS credentials (optional if using IAM role)
aws_access_key_id: "AKIA..."
aws_secret_access_key: "secret..."
aws_session_token: "token..."  # for SSO/STS
bedrock_model_id: "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
bedrock_vision_model_id: "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
```

### For LiteLLM (Internal Federal Reserve API)

```yaml
# config.yaml
fred_api_key: "YOUR_FRED_API_KEY"
llm_provider: "litellm"
litellm_api_base: "https://martinai-preview-api.frb.gov"
litellm_api_key: "YOUR_LITELLM_API_KEY"
litellm_model_id: "claude-3-5-sonnet-20241022"
litellm_vision_model_id: "claude-3-5-sonnet-20241022"
```

## Next Steps

To complete the integration:

1. **Refactor AI Assistant**:
   ```python
   # OLD
   class AIAssistantHandler:
       def __init__(self, bedrock_client, *, model_id):
           self._bedrock = bedrock_client
           self._model_id = model_id
       
       async def _invoke_bedrock(self, prompt):
           # Bedrock-specific code
   
   # NEW
   class AIAssistantHandler:
       def __init__(self, llm_client: LLMClient):
           self._llm_client = llm_client
       
       # Use: await self._llm_client.invoke(prompt)
   ```

2. **Update Main Application**:
   ```python
   # OLD
   bedrock_client = boto3.client("bedrock-runtime", **bedrock_kwargs)
   ai_assistant = AIAssistantHandler(
       bedrock_client=bedrock_client,
       model_id=config.bedrock_model_id,
   )
   
   # NEW
   from backend.services.llm_client import create_llm_client
   
   llm_client = create_llm_client(config, use_vision=False)
   ai_assistant = AIAssistantHandler(llm_client=llm_client)
   ```

3. **Apply same pattern to Summary Generator and Image Analyzer**

4. **Update tests** to mock the LLMClient interface

5. **Test both providers** to ensure compatibility

## Benefits

- ✅ **Flexibility**: Easy switching between Bedrock and LiteLLM
- ✅ **Maintainability**: Single abstraction layer for all LLM interactions
- ✅ **Testability**: Easier to mock and test
- ✅ **Future-proof**: Easy to add new providers (e.g., OpenAI, Azure OpenAI)
- ✅ **Internal API Support**: Can use Federal Reserve's internal LiteLLM endpoint

## Dependencies

The LiteLLM client requires the `httpx` library for async HTTP requests:

```bash
pip install httpx
```

Add to `pyproject.toml`:
```toml
dependencies = [
    "httpx>=0.24.0",
    # ... other dependencies
]
```

## API Compatibility

The LiteLLM implementation assumes an OpenAI-compatible API endpoint:

```
POST {litellm_api_base}/v1/chat/completions
Authorization: Bearer {litellm_api_key}

{
  "model": "{model_id}",
  "messages": [{"role": "user", "content": "..."}],
  "max_tokens": 8192
}
```

If your internal API uses a different format, update the `LiteLLMClient.invoke()` method accordingly.
