"""Summary Generator for the FRBSF Chart Builder.

Produces executive summaries of economic datasets using AWS Bedrock,
including trend analysis, peak/trough identification, predictions,
and economist-perspective interpretation.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import boto3
import pandas as pd

from backend.models.schemas import ChartContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_RETRIES = 2
_RETRY_DELAY_SECONDS = 2.0


# ---------------------------------------------------------------------------
# Summary Generator
# ---------------------------------------------------------------------------


class SummaryGenerator:
    """Generates executive summaries for economic chart data via Bedrock."""

    def __init__(
        self,
        bedrock_client: Any | None = None,
        *,
        region: str = "us-west-2",
        model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
    ) -> None:
        self._bedrock = bedrock_client or boto3.client(
            "bedrock-runtime", region_name=region,
        )
        self._model_id = model_id

    # -- Public API ---------------------------------------------------------

    async def generate(
        self,
        dataset: pd.DataFrame,
        chart_context: ChartContext,
    ) -> str:
        """Generate an executive summary with trend analysis, peaks/troughs,
        predictions, and economist-perspective interpretation.

        Uses only the provided dataset and Bedrock model knowledge.
        No web searches are performed.
        """
        prompt = self._build_prompt(dataset, chart_context)
        return await self._invoke_bedrock(prompt)

    # -- Prompt construction ------------------------------------------------

    @staticmethod
    def _build_prompt(
        dataset: pd.DataFrame,
        chart_context: ChartContext,
    ) -> str:
        """Construct the Bedrock prompt from dataset and chart context."""
        # Summarise the dataset for the prompt
        stats_text = ""
        numeric_cols = dataset.select_dtypes(include="number").columns.tolist()
        if numeric_cols:
            desc = dataset[numeric_cols].describe().to_string()
            stats_text = f"Descriptive statistics:\n{desc}\n\n"

        sample_rows = dataset.head(10).to_string(index=False)

        return (
            "You are an economist at the Federal Reserve Bank of San Francisco.\n"
            "Produce a well-structured executive summary for the following "
            "economic dataset and chart.\n\n"
            f"Dataset summary: {chart_context.dataset_summary}\n\n"
            f"{stats_text}"
            f"Sample data (first rows):\n{sample_rows}\n\n"
            "Your summary MUST include the following sections:\n"
            "1. **Trend Analysis** — Describe the overall direction and "
            "notable movements in the data.\n"
            "2. **Key Peaks and Troughs** — Identify the highest and lowest "
            "points, with approximate dates and values.\n"
            "3. **Predictions / Outlook** — Provide a forward-looking "
            "perspective based on the observed trends.\n"
            "4. **Economist Perspective** — Offer an interpretation of what "
            "the data means in a broader economic context.\n\n"
            "Use only the provided data and your economic knowledge. "
            "Do NOT perform web searches or reference external real-time data. "
            "Write in a professional, concise style suitable for an executive "
            "audience."
        )

    # -- Bedrock invocation with retry --------------------------------------

    async def _invoke_bedrock(self, prompt: str) -> str:
        """Call Bedrock with retry logic (up to 2 retries, 2 s delay).

        Returns the text content from the model response.
        Raises ``RuntimeError`` if all attempts fail.
        """
        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096,
                    "messages": [
                        {"role": "user", "content": prompt},
                    ],
                })

                response = self._bedrock.invoke_model(
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
