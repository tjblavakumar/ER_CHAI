"""Summary Generator for the FRBSF Chart Builder.

Produces executive summaries of economic datasets using configurable LLM provider (Bedrock or LiteLLM),
including trend analysis, peak/trough identification, predictions,
and economist-perspective interpretation.
"""

from __future__ import annotations

import json
import logging

from backend.services.llm_client import LLMClient
import pandas as pd

from backend.models.schemas import ChartContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Summary Generator
# ---------------------------------------------------------------------------


class SummaryGenerator:
    """Generates executive summaries for economic chart data via LLM."""

    def __init__(self, llm_client: LLMClient) -> None:
        """Initialize the summary generator with an LLM client.
        
        Args:
            llm_client: An LLMClient instance (Bedrock or LiteLLM)
        """
        self._llm_client = llm_client

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
        return await self._llm_client.invoke(prompt)

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


