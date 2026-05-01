"""Verification script to check LLM integration setup."""

import sys
from pathlib import Path

def check_file_exists(filepath: str) -> bool:
    """Check if a file exists."""
    return Path(filepath).exists()

def check_import(module_path: str) -> bool:
    """Check if a Python module can be imported."""
    try:
        __import__(module_path)
        return True
    except ImportError as e:
        print(f"  [FAIL] Import error: {e}")
        return False

def main():
    print("="*70)
    print("ER_CHAI LLM Integration Verification")
    print("="*70)
    print()
    
    all_checks_passed = True
    
    # Check key files exist
    print("[FILES] Checking key files...")
    files_to_check = [
        ("backend/services/llm_client.py", "LLM Client abstraction"),
        ("backend/models/schemas.py", "Configuration schemas"),
        ("config.yaml.example", "Config example"),
        ("config.yaml.litellm.example", "LiteLLM config example"),
        ("LLM_INTEGRATION_GUIDE.md", "Integration guide"),
        ("LLM_INTEGRATION_SUMMARY.md", "Integration summary"),
    ]
    
    for filepath, description in files_to_check:
        exists = check_file_exists(filepath)
        status = "[PASS]" if exists else "[FAIL]"
        print(f"  {status} {description}: {filepath}")
        if not exists:
            all_checks_passed = False
    print()
    
    # Check Python imports
    print("[IMPORTS] Checking Python imports...")
    modules_to_check = [
        ("backend.services.llm_client", "LLM Client module"),
        ("backend.services.ai_assistant", "AI Assistant module"),
        ("backend.services.summary_generator", "Summary Generator module"),
        ("backend.models.schemas", "Schemas module"),
        ("httpx", "httpx library (required for LiteLLM)"),
    ]
    
    for module_path, description in modules_to_check:
        can_import = check_import(module_path)
        status = "[PASS]" if can_import else "[FAIL]"
        print(f"  {status} {description}: {module_path}")
        if not can_import:
            all_checks_passed = False
    print()
    
    # Check config structure
    print("[CONFIG]  Checking configuration...")
    try:
        from backend.models.schemas import AppConfig
        
        # Check if AppConfig has new fields
        config_fields = AppConfig.model_fields.keys()
        required_fields = [
            'llm_provider',
            'litellm_api_base',
            'litellm_api_key',
            'litellm_model_id',
            'litellm_vision_model_id',
        ]
        
        for field in required_fields:
            has_field = field in config_fields
            status = "[PASS]" if has_field else "[FAIL]"
            print(f"  {status} AppConfig.{field}")
            if not has_field:
                all_checks_passed = False
    except Exception as e:
        print(f"  [FAIL] Error checking AppConfig: {e}")
        all_checks_passed = False
    print()
    
    # Check LLM client implementation
    print("[LLM] Checking LLM client implementation...")
    try:
        from backend.services.llm_client import (
            LLMClient,
            BedrockClient,
            LiteLLMClient,
            create_llm_client,
        )
        
        checks = [
            (LLMClient, "LLMClient base class"),
            (BedrockClient, "BedrockClient implementation"),
            (LiteLLMClient, "LiteLLMClient implementation"),
            (create_llm_client, "create_llm_client factory"),
        ]
        
        for obj, description in checks:
            exists = obj is not None
            status = "[PASS]" if exists else "[FAIL]"
            print(f"  {status} {description}")
            if not exists:
                all_checks_passed = False
    except Exception as e:
        print(f"  [FAIL] Error checking LLM client: {e}")
        all_checks_passed = False
    print()
    
    # Check service refactoring
    print("[SERVICES] Checking service refactoring...")
    try:
        from backend.services.ai_assistant import AIAssistantHandler
        from backend.services.summary_generator import SummaryGenerator
        from backend.services.llm_client import LLMClient
        import inspect
        
        # Check AI Assistant __init__ signature
        ai_sig = inspect.signature(AIAssistantHandler.__init__)
        ai_params = list(ai_sig.parameters.keys())
        ai_refactored = 'llm_client' in ai_params and 'bedrock_client' not in ai_params
        status = "[PASS]" if ai_refactored else "[FAIL]"
        print(f"  {status} AIAssistantHandler refactored (accepts llm_client)")
        if not ai_refactored:
            print(f"      Current params: {ai_params}")
            all_checks_passed = False
        
        # Check Summary Generator __init__ signature
        sg_sig = inspect.signature(SummaryGenerator.__init__)
        sg_params = list(sg_sig.parameters.keys())
        sg_refactored = 'llm_client' in sg_params and 'bedrock_client' not in sg_params
        status = "[PASS]" if sg_refactored else "[FAIL]"
        print(f"  {status} SummaryGenerator refactored (accepts llm_client)")
        if not sg_refactored:
            print(f"      Current params: {sg_params}")
            all_checks_passed = False
            
    except Exception as e:
        print(f"  [FAIL] Error checking services: {e}")
        all_checks_passed = False
    print()
    
    # Summary
    print("="*70)
    if all_checks_passed:
        print("[PASS] All checks passed! LLM integration is properly set up.")
        print()
        print("Next steps:")
        print("  1. Copy config.yaml.example or config.yaml.litellm.example to config.yaml")
        print("  2. Fill in your API keys")
        print("  3. Set llm_provider to 'bedrock' or 'litellm'")
        print("  4. Run: .\\start-servers.ps1")
        return 0
    else:
        print("[FAIL] Some checks failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
