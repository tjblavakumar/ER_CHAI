# LiteLLM Integration - Summary of Changes

## Overview

The ER_CHAI application has been enhanced to support **both AWS Bedrock and LiteLLM** as LLM providers. You can now choose which provider to use through configuration, allowing you to use the internal Federal Reserve LiteLLM API endpoint.

## What Changed?

### 1. New LLM Client Abstraction Layer

**File**: `backend/services/llm_client.py` (**NEW**)

- Created a provider-agnostic abstraction for LLM interactions
- `LLMClient` abstract base class defines the interface
- `BedrockClient` implements AWS Bedrock
- `LiteLLMClient` implements LiteLLM (OpenAI-compatible API)
- `create_llm_client()` factory function creates the appropriate client

### 2. Updated Configuration

**File**: `backend/models/schemas.py` (MODIFIED)

Added to `AppConfig`:
```python
# LLM Provider Selection
llm_provider: str = "bedrock"  # or "litellm"

# LiteLLM Configuration
litellm_api_base: str | None = None
litellm_api_key: str | None = None
litellm_model_id: str = "claude-3-5-sonnet-20241022"
litellm_vision_model_id: str = "claude-3-5-sonnet-20241022"
```

**File**: `config.yaml.example` (MODIFIED)

- Updated with sections for both Bedrock and LiteLLM
- Clear documentation on which settings are needed for each provider

**File**: `config.yaml.litellm.example` (**NEW**)

- Example configuration specifically for LiteLLM usage
- Shows how to configure the internal Federal Reserve API

### 3. Refactored AI Services

**File**: `backend/services/ai_assistant.py` (MODIFIED)

- Now accepts `LLMClient` instead of `bedrock_client`
- Removed bedrock-specific code
- Uses `await self._llm_client.invoke(prompt)` for all LLM calls

**File**: `backend/services/summary_generator.py` (MODIFIED)

- Same refactoring pattern as AI Assistant
- Provider-agnostic implementation

**File**: `backend/main.py` (MODIFIED)

- Uses `create_llm_client()` factory to create LLM clients
- Passes LLM clients to services instead of bedrock clients
- Added `llm_provider` to app state

### 4. Documentation

**File**: `LLM_INTEGRATION_GUIDE.md` (**NEW**)

- Comprehensive guide on the integration architecture
- Usage instructions for both providers
- Implementation details and next steps

## How to Use

### Option 1: AWS Bedrock (Default)

```yaml
# config.yaml
fred_api_key: "YOUR_FRED_API_KEY"
llm_provider: "bedrock"
aws_region: "us-east-1"
aws_access_key_id: "AKIA..."
aws_secret_access_key: "..."
bedrock_model_id: "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
```

### Option 2: LiteLLM (Internal Federal Reserve API)

```yaml
# config.yaml
fred_api_key: "YOUR_FRED_API_KEY"
llm_provider: "litellm"
litellm_api_base: "https://martinai-preview-api.frb.gov"
litellm_api_key: "YOUR_INTERNAL_API_KEY"
litellm_model_id: "claude-3-5-sonnet-20241022"
```

## Installation

No new Python packages are required - `httpx` is already in the dependencies:

```bash
pip install -e ".[dev]"
```

## Running the Application

### With Bedrock

```bash
# 1. Set up config.yaml with Bedrock settings
cp config.yaml.example config.yaml
# Edit config.yaml with your AWS credentials

# 2. Start the application
.\start-servers.ps1
```

### With LiteLLM

```bash
# 1. Set up config.yaml with LiteLLM settings
cp config.yaml.litellm.example config.yaml
# Edit config.yaml with your internal API key

# 2. Start the application
.\start-servers.ps1
```

## Architecture Benefits

✅ **Flexibility**: Easy switching between providers via configuration  
✅ **No Code Changes**: Switch providers without modifying Python code  
✅ **Future-Proof**: Easy to add new providers (OpenAI, Azure OpenAI, etc.)  
✅ **Internal API Support**: Use Federal Reserve's internal LiteLLM endpoint  
✅ **Unified Interface**: All LLM interactions use the same abstraction

## Files Modified

| File | Status | Description |
|------|--------|-------------|
| `backend/models/schemas.py` | Modified | Added LiteLLM config fields |
| `backend/services/llm_client.py` | **NEW** | LLM client abstraction layer |
| `backend/services/ai_assistant.py` | Modified | Uses LLMClient abstraction |
| `backend/services/summary_generator.py` | Modified | Uses LLMClient abstraction |
| `backend/main.py` | Modified | Creates and injects LLM clients |
| `config.yaml.example` | Modified | Added LiteLLM configuration |
| `config.yaml.litellm.example` | **NEW** | LiteLLM-specific example |
| `LLM_INTEGRATION_GUIDE.md` | **NEW** | Comprehensive integration guide |
| `LLM_INTEGRATION_SUMMARY.md` | **NEW** | This file - summary of changes |

## Known Limitations

### ImageAnalyzer Not Yet Refactored

The `ImageAnalyzer` service still uses Bedrock directly for vision analysis. This is because:

1. Vision analysis requires specialized API interactions
2. LiteLLM vision endpoint compatibility needs to be verified
3. The vision workload is separate from main AI assistance

To use LiteLLM, the application will:
- Use LiteLLM for AI Assistant and Summary Generator
- Fall back to Bedrock for image analysis (if configured)

**Future Work**: Refactor `ImageAnalyzer` to support LiteLLM vision models if the internal API supports vision.

## Testing

The existing tests need to be updated to work with the new LLM client abstraction. The tests currently mock Bedrock clients directly.

### Next Steps for Testing

1. Create mock LLM clients for testing
2. Update `tests/unit/test_ai_assistant.py`
3. Update `tests/unit/test_summary.py`

## Troubleshooting

### "litellm_api_base is required for LiteLLM provider"

Make sure you have `litellm_api_base` and `litellm_api_key` set in your `config.yaml` when using `llm_provider: "litellm"`.

### "Unsupported LLM provider"

Check that `llm_provider` is exactly `"bedrock"` or `"litellm"` (lowercase).

### Connection Errors with LiteLLM

Verify:
1. The internal API endpoint URL is correct
2. Your API key is valid
3. You can reach the internal endpoint (not blocked by firewall/VPN)
4. The model ID exists on the endpoint

### API Format Mismatch

If you get JSON parsing errors, the internal LiteLLM endpoint may use a different API format. Update `LiteLLMClient.invoke()` in `backend/services/llm_client.py` to match your endpoint's format.

## Contact

For questions about:
- **AWS Bedrock configuration**: See AWS Bedrock documentation
- **Internal LiteLLM API**: Contact your Federal Reserve IT team or API portal support
- **This integration**: See `LLM_INTEGRATION_GUIDE.md` for technical details

## Version History

- **v3.2.1** (Current): Added LiteLLM support alongside Bedrock
- **v3.2**: Original version with Bedrock only
