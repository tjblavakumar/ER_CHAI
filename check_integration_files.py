"""Simple file-based verification for LLM integration."""

from pathlib import Path

print("="*70)
print("ER_CHAI LLM Integration - File Verification")
print("="*70)
print()

files_to_check = [
    ("backend/services/llm_client.py", "LLM Client abstraction"),
    ("backend/models/schemas.py", "Configuration schemas (modified)"),
    ("backend/services/ai_assistant.py", "AI Assistant (refactored)"),
    ("backend/services/summary_generator.py", "Summary Generator (refactored)"),
    ("backend/main.py", "Main app (modified)"),
    ("config.yaml.example", "Config example (updated)"),
    ("config.yaml.litellm.example", "LiteLLM config example"),
    ("LLM_INTEGRATION_GUIDE.md", "Integration guide"),
    ("LLM_INTEGRATION_SUMMARY.md", "Integration summary"),
]

all_exist = True
for filepath, description in files_to_check:
    exists = Path(filepath).exists()
    status = "[OK]" if exists else "[MISSING]"
    print(f"  {status} {description}")
    print(f"        {filepath}")
    if not exists:
        all_exist = False

print()
print("="*70)
if all_exist:
    print("[SUCCESS] All integration files are present!")
    print()
    print("Configuration Options:")
    print()
    print("  Option 1 - AWS Bedrock:")
    print("    cp config.yaml.example config.yaml")
    print("    # Edit config.yaml - set llm_provider: 'bedrock'")
    print()
    print("  Option 2 - LiteLLM (Internal Federal Reserve API):")
    print("    cp config.yaml.litellm.example config.yaml")
    print("    # Edit config.yaml - add your internal API key")
    print()
    print("Then run:")
    print("  .\\start-servers.ps1")
else:
    print("[ERROR] Some files are missing!")
    print("Please ensure all refactoring scripts completed successfully.")
