"""LLM Client abstraction layer for Bedrock and LiteLLM providers.

Provides a unified interface for interacting with LLM services,
supporting both AWS Bedrock and LiteLLM API endpoints.
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import boto3
import httpx

from backend.models.schemas import AppConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_RETRIES = 2
_RETRY_DELAY_SECONDS = 2.0
_REQUEST_TIMEOUT = 120.0  # seconds


# ---------------------------------------------------------------------------
# Abstract Base Class
# ---------------------------------------------------------------------------


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def invoke(self, prompt: str, max_tokens: int = 8192) -> str:
        """Invoke the LLM with a prompt and return the response text.

        Args:
            prompt: The user prompt to send to the LLM
            max_tokens: Maximum number of tokens in the response

        Returns:
            The text response from the LLM

        Raises:
            RuntimeError: If the API call fails after all retries
        """
        pass


# ---------------------------------------------------------------------------
# AWS Bedrock Client
# ---------------------------------------------------------------------------


class BedrockClient(LLMClient):
    """LLM client for AWS Bedrock service."""

    def __init__(
        self,
        region: str,
        model_id: str,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
    ) -> None:
        """Initialize the Bedrock client.

        Args:
            region: AWS region (e.g., "us-east-1")
            model_id: Bedrock model ID (e.g., "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
            aws_access_key_id: AWS access key (optional, uses IAM role if not provided)
            aws_secret_access_key: AWS secret key (optional)
            aws_session_token: AWS session token (required for STS/SSO credentials)
        """
        self._model_id = model_id
        
        # Build boto3 client with explicit credentials if provided
        client_kwargs: dict[str, Any] = {"region_name": region}
        if aws_access_key_id and aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = aws_access_key_id
            client_kwargs["aws_secret_access_key"] = aws_secret_access_key
            if aws_session_token:
                client_kwargs["aws_session_token"] = aws_session_token

        self._bedrock = boto3.client("bedrock-runtime", **client_kwargs)
        logger.info("Initialized Bedrock client with model: %s", model_id)

    async def invoke(self, prompt: str, max_tokens: int = 8192) -> str:
        """Invoke Bedrock with retry logic."""
        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "user", "content": prompt},
                    ],
                })

                response = await asyncio.to_thread(
                    self._bedrock.invoke_model,
                    modelId=self._model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=body,
                )

                response_body = json.loads(response["body"].read())
                return response_body["content"][0]["text"]

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Bedrock call failed (attempt %d/%d): %s",
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    exc,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(_RETRY_DELAY_SECONDS)

        raise RuntimeError(
            f"Bedrock API call failed after {_MAX_RETRIES + 1} attempts: {last_error}"
        )


# ---------------------------------------------------------------------------
# LiteLLM Client
# ---------------------------------------------------------------------------


class LiteLLMClient(LLMClient):
    """LLM client for LiteLLM API service."""

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model_id: str,
    ) -> None:
        """Initialize the LiteLLM client.

        Args:
            api_base: Base URL for the LiteLLM API (e.g., "https://martinai-preview-api.frb.gov")
            api_key: API key for authentication
            model_id: Model ID to use (e.g., "claude-3-5-sonnet-20241022")
        """
        self._api_base = api_base.rstrip("/")
        self._api_key = api_key
        self._model_id = model_id
        self._client = httpx.AsyncClient(timeout=_REQUEST_TIMEOUT)
        logger.info("Initialized LiteLLM client with model: %s", model_id)

    async def invoke(self, prompt: str, max_tokens: int = 8192) -> str:
        """Invoke LiteLLM API with retry logic."""
        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                # LiteLLM typically uses OpenAI-compatible API format
                url = f"{self._api_base}/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": self._model_id,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_tokens,
                }

                response = await self._client.post(url, headers=headers, json=payload)
                response.raise_for_status()

                result = response.json()
                # Extract message content from OpenAI-compatible format
                return result["choices"][0]["message"]["content"]

            except httpx.HTTPStatusError as exc:
                last_error = exc
                # Log the full response body for debugging
                response_text = exc.response.text if hasattr(exc, 'response') else 'No response body'
                logger.warning(
                    "LiteLLM call failed (attempt %d/%d): %s\nResponse: %s",
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    exc,
                    response_text[:500],  # First 500 chars
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(_RETRY_DELAY_SECONDS)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "LiteLLM call failed (attempt %d/%d): %s",
                    attempt + 1,
                    _MAX_RETRIES + 1,
                    exc,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(_RETRY_DELAY_SECONDS)

        raise RuntimeError(
            f"LiteLLM API call failed after {_MAX_RETRIES + 1} attempts: {last_error}"
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def create_llm_client(config: AppConfig, use_vision: bool = False) -> LLMClient:
    """Factory function to create the appropriate LLM client based on config.

    Args:
        config: Application configuration
        use_vision: If True, use vision model IDs; otherwise use regular model IDs

    Returns:
        LLMClient instance (either BedrockClient or LiteLLMClient)

    Raises:
        ValueError: If the provider is unsupported or required config is missing
    """
    provider = config.llm_provider.lower()

    if provider == "bedrock":
        if not config.aws_region:
            raise ValueError("aws_region is required for Bedrock provider")
        
        model_id = (config.bedrock_vision_model_id if use_vision 
                    else config.bedrock_model_id)
        
        return BedrockClient(
            region=config.aws_region,
            model_id=model_id,
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
            aws_session_token=config.aws_session_token,
        )

    elif provider == "litellm":
        if not config.litellm_api_base:
            raise ValueError("litellm_api_base is required for LiteLLM provider")
        if not config.litellm_api_key:
            raise ValueError("litellm_api_key is required for LiteLLM provider")
        
        model_id = (config.litellm_vision_model_id if use_vision 
                    else config.litellm_model_id)
        
        return LiteLLMClient(
            api_base=config.litellm_api_base,
            api_key=config.litellm_api_key,
            model_id=model_id,
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            "Must be 'bedrock' or 'litellm'"
        )
