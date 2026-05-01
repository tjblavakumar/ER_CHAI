# LiteLLM Integration - Quick Reference Card

## 🎯 Goal
Enable ER_CHAI to use the internal Federal Reserve LiteLLM API (`https://martinai-preview-api.frb.gov`) instead of AWS Bedrock.

## ✅ Status: COMPLETE

All files created and refactored. Ready to configure and test!

---

## 📦 What You Need

1. **FRED API Key** - Get from https://fred.stlouisfed.org/docs/api/api_key.html
2. **Internal LiteLLM API Key** - Get from Federal Reserve API portal
3. **Python 3.11+** - Already installed
4. **Dependencies** - Run: `pip install -e ".[dev]"`

---

## 🚀 Quick Start (3 Steps)

### Step 1: Create Config
```bash
cp config.yaml.litellm.example config.yaml
```

### Step 2: Edit Config
```yaml
# config.yaml
fred_api_key: "YOUR_FRED_API_KEY"          # ← Add your key
llm_provider: "litellm"
litellm_api_base: "https://martinai-preview-api.frb.gov"
litellm_api_key: "YOUR_INTERNAL_API_KEY"   # ← Add your key
litellm_model_id: "claude-3-5-sonnet-20241022"
```

### Step 3: Run
```bash
.\start-servers.ps1
```

**Done!** Open http://localhost:5173

---

## 🔄 Switch Between Providers

Just change ONE line in `config.yaml`:

### Use LiteLLM (Internal API)
```yaml
llm_provider: "litellm"
```

### Use AWS Bedrock
```yaml
llm_provider: "bedrock"
```

No code changes needed!

---

## 📋 Verification Checklist

```bash
# Check files
python check_integration_files.py

# Expected output:
# [OK] All integration files are present!
```

---

## 📚 Documentation

| File | What It Contains |
|------|------------------|
| `README_LITELLM_INTEGRATION.md` | **START HERE** - Quick start guide |
| `VISUAL_OVERVIEW.md` | Architecture diagrams |
| `PROJECT_SUMMARY.md` | Executive summary |
| `LLM_INTEGRATION_GUIDE.md` | Technical details |
| `config.yaml.litellm.example` | Example config |

---

## ⚙️ Configuration Templates

### Template 1: LiteLLM Only
```yaml
fred_api_key: "abc123"
llm_provider: "litellm"
litellm_api_base: "https://martinai-preview-api.frb.gov"
litellm_api_key: "xyz789"
litellm_model_id: "claude-3-5-sonnet-20241022"
litellm_vision_model_id: "claude-3-5-sonnet-20241022"
```

### Template 2: Bedrock Only
```yaml
fred_api_key: "abc123"
llm_provider: "bedrock"
aws_region: "us-east-1"
aws_access_key_id: "AKIA..."
aws_secret_access_key: "..."
bedrock_model_id: "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
```

### Template 3: Both (Easy Switching)
```yaml
fred_api_key: "abc123"

# Choose one:
llm_provider: "litellm"  # or "bedrock"

# LiteLLM settings
litellm_api_base: "https://martinai-preview-api.frb.gov"
litellm_api_key: "xyz789"
litellm_model_id: "claude-3-5-sonnet-20241022"

# Bedrock settings
aws_region: "us-east-1"
aws_access_key_id: "AKIA..."
aws_secret_access_key: "..."
bedrock_model_id: "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
```

---

## 🔧 Modified Files

| File | Change |
|------|--------|
| `backend/services/llm_client.py` | **NEW** - Abstraction layer |
| `backend/models/schemas.py` | Added LiteLLM config |
| `backend/services/ai_assistant.py` | Uses LLMClient |
| `backend/services/summary_generator.py` | Uses LLMClient |
| `backend/main.py` | Creates LLM clients |
| `config.yaml.example` | Both providers |

---

## ❗ Common Issues

| Error | Solution |
|-------|----------|
| "litellm_api_base is required" | Add `litellm_api_base` and `litellm_api_key` to config |
| Connection timeout | Check VPN/network, verify API endpoint |
| "Unsupported LLM provider" | Set `llm_provider` to `"bedrock"` or `"litellm"` |
| JSON parsing error | API format may differ - see troubleshooting docs |

---

## 🎨 Architecture (Simple View)

```
┌─────────────────────────────────────┐
│        config.yaml                  │
│  llm_provider: "litellm"           │
└──────────────┬──────────────────────┘
               │
               ↓
┌──────────────────────────────────────┐
│   create_llm_client(config)         │
└──────────────┬───────────────────────┘
               │
    ┌──────────┴──────────┐
    ↓                     ↓
┌─────────────┐    ┌──────────────────┐
│ Bedrock     │    │ LiteLLM          │
│ Client      │    │ Client           │
│ (boto3)     │    │ (httpx)          │
└──────┬──────┘    └────────┬─────────┘
       │                    │
       ↓                    ↓
  AWS Bedrock      Internal API
```

---

## 🧪 Testing Steps

1. **Config Check**: `python check_integration_files.py`
2. **Start App**: `.\start-servers.ps1`
3. **Open Browser**: http://localhost:5173
4. **Test AI**: 
   - Upload data / enter FRED URL
   - Ask AI to modify chart
   - Generate summary
5. **Verify**: Check that responses come from chosen provider

---

## 💡 Key Benefits

✅ Use internal Federal Reserve API  
✅ No code changes to switch providers  
✅ Backward compatible with Bedrock  
✅ Easy to add more providers later  

---

## 📞 Help & Support

- **Setup Issues**: See `README_LITELLM_INTEGRATION.md`
- **Technical Details**: See `LLM_INTEGRATION_GUIDE.md`
- **API Access**: Contact Federal Reserve IT
- **AWS Bedrock**: See AWS documentation

---

## ✨ You're Done!

The integration is complete and ready to use. Just configure your API keys and start the application!

**Files to Read**:
1. `README_LITELLM_INTEGRATION.md` (Quick start)
2. `VISUAL_OVERVIEW.md` (Diagrams)
3. `PROJECT_SUMMARY.md` (Full details)

**Commands to Run**:
```bash
cp config.yaml.litellm.example config.yaml  # Create config
# Edit config.yaml - add your API keys
python check_integration_files.py           # Verify
.\start-servers.ps1                         # Run
```

🎉 **Happy charting with LiteLLM!** 🎉
