# Troubleshooting: Application Startup Issues

## Error: "You must specify a region" (NoRegionError)

### Problem
```
botocore.exceptions.NoRegionError: You must specify a region.
```

This error occurs when using LiteLLM but the application still tries to create a Bedrock client without AWS credentials.

### Solution
This has been **FIXED** in the latest version of `backend/main.py`.

The fix makes Bedrock client creation conditional:
- Only creates Bedrock client when `llm_provider == "bedrock"` OR AWS credentials are present
- Gracefully handles missing Bedrock client (disables ImageAnalyzer)
- LiteLLM-only mode now works without AWS credentials

### To Verify the Fix

1. **Check your config.yaml**:
```yaml
llm_provider: "litellm"  # Must be "litellm"
litellm_api_base: "https://martinai-preview-api.frb.gov"
litellm_api_key: "YOUR_API_KEY"
```

2. **Ensure you DON'T have AWS credentials** (or comment them out):
```yaml
# aws_region: "us-east-1"     # ← Should be commented out
# aws_access_key_id: "..."    # ← Should be commented out
```

3. **Restart the server**:
```bash
.\start-servers.ps1
```

### Expected Behavior

When using LiteLLM without AWS credentials:
- ✅ Application starts successfully
- ✅ AI Assistant works (using LiteLLM)
- ✅ Summary Generator works (using LiteLLM)
- ⚠️ Warning: "ImageAnalyzer disabled - Bedrock client not available"
- ⚠️ Reference image analysis won't work (requires Bedrock)

---

## Error: "No module named 'uvicorn'" or Missing Dependencies

### Problem
```
python.exe: No module named uvicorn
```
or
```
ModuleNotFoundError: No module named 'httpx'
```

### Solution

Install dependencies:

```bash
# Make sure you're in the ER_CHAI directory
cd ER_CHAI

# Install all dependencies
pip install -e ".[dev]"
```

Or if you prefer pip directly:
```bash
pip install fastapi uvicorn httpx boto3 pydantic pandas openpyxl opencv-python-headless reportlab pyyaml python-multipart aiosqlite matplotlib
```

---

## Error: "litellm_api_base is required"

### Problem
```
ValueError: litellm_api_base is required for LiteLLM provider
```

### Solution

Your `config.yaml` is missing required LiteLLM fields:

```yaml
llm_provider: "litellm"
litellm_api_base: "https://martinai-preview-api.frb.gov"  # ← Add this
litellm_api_key: "YOUR_API_KEY"                            # ← Add this
```

---

## Error: Connection Timeout to LiteLLM API

### Problem
```
httpx.ConnectTimeout: Connection timed out
```
or
```
Connection refused
```

### Possible Causes

1. **VPN/Network**: You're not connected to the Federal Reserve network
2. **Firewall**: The endpoint is blocked
3. **Wrong URL**: API endpoint URL is incorrect
4. **API Down**: The internal API is temporarily unavailable

### Solutions

1. **Check VPN**: Ensure you're connected to Federal Reserve VPN
2. **Test connectivity**:
```bash
curl https://martinai-preview-api.frb.gov/v1/models
```
3. **Verify URL** with your IT team
4. **Check API status** with Federal Reserve API portal

---

## Warning: "ImageAnalyzer disabled"

### Message
```
WARNING: ImageAnalyzer disabled - Bedrock client not available
```

### Explanation

This is **expected** when using LiteLLM without AWS credentials.

**Impact**:
- ✅ All AI functionality works (chat, summaries, Q&A)
- ❌ Reference image analysis is disabled
- You cannot upload a reference chart image to extract styling

**To enable ImageAnalyzer**:

Add AWS Bedrock credentials to your `config.yaml`:
```yaml
llm_provider: "litellm"      # LiteLLM for AI features
aws_region: "us-east-1"      # Bedrock for image analysis
aws_access_key_id: "AKIA..."
aws_secret_access_key: "..."
```

This allows:
- LiteLLM for AI Assistant and Summaries
- Bedrock for image/vision analysis only

---

## Testing Your Setup

### Quick Test Script

Save as `test_startup.py`:

```python
"""Test if the application can start."""

import sys

try:
    print("[1/5] Loading configuration...")
    from backend.services.config import load_config
    config = load_config()
    print(f"  ✓ Config loaded. Provider: {config.llm_provider}")
    
    print("\n[2/5] Creating LLM client...")
    from backend.services.llm_client import create_llm_client
    llm_client = create_llm_client(config, use_vision=False)
    print(f"  ✓ LLM client created: {type(llm_client).__name__}")
    
    print("\n[3/5] Testing LLM invoke...")
    import asyncio
    async def test():
        response = await llm_client.invoke("Say 'Hello' in one word.")
        return response
    
    result = asyncio.run(test())
    print(f"  ✓ LLM responded: {result[:50]}...")
    
    print("\n[4/5] Checking services...")
    from backend.services.ai_assistant import AIAssistantHandler
    from backend.services.summary_generator import SummaryGenerator
    ai_assistant = AIAssistantHandler(llm_client=llm_client)
    summary_generator = SummaryGenerator(llm_client=llm_client)
    print("  ✓ Services initialized")
    
    print("\n[5/5] Application ready!")
    print("\n✅ All checks passed! You can start the server.")
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

Run it:
```bash
python test_startup.py
```

---

## Full Startup Checklist

1. **Dependencies installed?**
```bash
pip install -e ".[dev]"
```

2. **Config file exists?**
```bash
# Check if file exists
ls config.yaml

# Should show: config.yaml
```

3. **Config file correct?**
```bash
# For LiteLLM:
fred_api_key: "YOUR_KEY"
llm_provider: "litellm"
litellm_api_base: "https://martinai-preview-api.frb.gov"
litellm_api_key: "YOUR_KEY"
```

4. **File verification**:
```bash
python check_integration_files.py
# Should show: [OK] for all files
```

5. **Start server**:
```bash
.\start-servers.ps1
```

6. **Check logs**:
Look for:
- ✅ "FRBSF Chart Builder started successfully"
- ✅ "Application startup complete"
- ⚠️ "ImageAnalyzer disabled" (expected if no AWS creds)

7. **Test endpoint**:
```bash
curl http://localhost:8080/docs
# Should return HTML
```

---

## Still Having Issues?

### Check these files were updated:

```bash
# Verify main.py was updated
python -c "with open('backend/main.py') as f: content = f.read(); print('✓ Updated' if 'create_llm_client' in content else '✗ Old version')"

# Verify llm_client.py exists
python -c "from pathlib import Path; print('✓ Exists' if Path('backend/services/llm_client.py').exists() else '✗ Missing')"
```

### Get help:

1. Check `LLM_INTEGRATION_SUMMARY.md` - Troubleshooting section
2. Check `VISUAL_OVERVIEW.md` - Architecture diagrams
3. Check `INDEX.md` - Documentation guide

### Common Solutions

| Issue | Solution |
|-------|----------|
| NoRegionError | Use latest `backend/main.py` (creates Bedrock client conditionally) |
| Missing dependencies | Run `pip install -e ".[dev]"` |
| API connection error | Check VPN, verify API URL |
| ImageAnalyzer disabled | Expected without AWS creds - add if needed |
| Config error | Verify `llm_provider` is "litellm" or "bedrock" |

---

## Success Indicators

When everything is working:

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

And in browser (http://localhost:5173):
- ✅ Application loads
- ✅ Can upload data / enter FRED URL  
- ✅ AI chat responds
- ✅ Can generate summaries
