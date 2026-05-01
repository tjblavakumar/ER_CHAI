"""Diagnostic script to test LiteLLM API and see the actual error response."""

import asyncio
import httpx
import json

async def test_litellm_api():
    """Test the LiteLLM API with detailed error reporting."""
    
    # Load config
    print("Loading configuration...")
    from backend.services.config import load_config
    config = load_config()
    
    print(f"API Base: {config.litellm_api_base}")
    print(f"Model ID: {config.litellm_model_id}")
    print(f"API Key: {config.litellm_api_key[:20]}..." if config.litellm_api_key else "None")
    print()
    
    # Test 1: Basic connectivity
    print("=" * 70)
    print("TEST 1: Testing API connectivity...")
    print("=" * 70)
    
    url = f"{config.litellm_api_base}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.litellm_api_key}",
        "Content-Type": "application/json",
    }
    
    # Standard OpenAI format payload
    payload = {
        "model": config.litellm_model_id,
        "messages": [
            {"role": "user", "content": "Say 'Hello' in one word."}
        ],
        "max_tokens": 100,
    }
    
    print(f"URL: {url}")
    print(f"Headers: {json.dumps({k: v[:50] + '...' if len(v) > 50 else v for k, v in headers.items()}, indent=2)}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print()
            
            if response.status_code == 200:
                print("✅ SUCCESS!")
                result = response.json()
                print(f"Response: {json.dumps(result, indent=2)}")
            else:
                print("❌ FAILED!")
                print(f"Response Body: {response.text}")
                
                # Try to parse as JSON
                try:
                    error_json = response.json()
                    print(f"Error Details: {json.dumps(error_json, indent=2)}")
                except:
                    pass
                    
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    print()
    print("=" * 70)
    print("TEST 2: Trying alternative payload formats...")
    print("=" * 70)
    
    # Test different payload variations
    test_payloads = [
        {
            "name": "Without max_tokens",
            "payload": {
                "model": config.litellm_model_id,
                "messages": [{"role": "user", "content": "Hello"}],
            }
        },
        {
            "name": "With temperature",
            "payload": {
                "model": config.litellm_model_id,
                "messages": [{"role": "user", "content": "Hello"}],
                "temperature": 0.7,
            }
        },
        {
            "name": "Anthropic-style",
            "payload": {
                "model": config.litellm_model_id,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 100,
                "anthropic_version": "bedrock-2023-05-31",
            }
        },
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for test in test_payloads:
            print(f"\nTrying: {test['name']}")
            print(f"Payload: {json.dumps(test['payload'], indent=2)}")
            
            try:
                response = await client.post(url, headers=headers, json=test['payload'])
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    print("✅ This format works!")
                    result = response.json()
                    print(f"Response: {json.dumps(result, indent=2)[:200]}...")
                    break
                else:
                    print(f"❌ Failed: {response.text[:200]}")
            except Exception as e:
                print(f"❌ Exception: {e}")
    
    print()
    print("=" * 70)
    print("TEST 3: Check if /v1/models endpoint exists...")
    print("=" * 70)
    
    models_url = f"{config.litellm_api_base}/v1/models"
    print(f"URL: {models_url}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(models_url, headers={"Authorization": f"Bearer {config.litellm_api_key}"})
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Models endpoint accessible!")
                print(f"Response: {response.text[:500]}")
            else:
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_litellm_api())
