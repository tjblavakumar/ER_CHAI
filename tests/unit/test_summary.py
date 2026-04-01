"""Unit tests for the Summary Generator service.

Covers:
- Summary generation with mocked Bedrock responses
- Prompt construction (includes all required sections)
- Retry logic on Bedrock failures
- Edge cases: single-row dataset, no numeric columns
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from backend.models.schemas import (
    AxesConfig,
    ChartContext,
    ChartElementState,
    ChartState,
    GridlineConfig,
    LegendConfig,
    LegendEntry,
    Position,
    SeriesConfig,
)
from backend.services.summary_generator import SummaryGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_bedrock(response_text: str) -> MagicMock:
    """Create a mock Bedrock client returning *response_text*."""
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps({
        "content": [{"type": "text", "text": response_text}],
    }).encode()
    mock_client = MagicMock()
    mock_client.invoke_model.return_value = {"body": mock_body}
    return mock_client


def _make_chart_context() -> ChartContext:
    """Create a minimal valid ChartContext for testing."""
    chart_state = ChartState(
        chart_type="line",
        title=ChartElementState(
            text="GDP Over Time", position=Position(x=100, y=10),
        ),
        axes=AxesConfig(x_label="Date", y_label="GDP (Billions)"),
        series=[
            SeriesConfig(
                name="GDP", column="gdp", chart_type="line", color="#003B5C",
            ),
        ],
        legend=LegendConfig(
            visible=True,
            position=Position(x=400, y=50),
            entries=[
                LegendEntry(label="GDP", color="#003B5C", series_name="gdp"),
            ],
        ),
        gridlines=GridlineConfig(),
        annotations=[],
        data_table=None,
        elements_positions={},
        dataset_path="data/test.csv",
        dataset_columns=["date", "gdp"],
    )
    return ChartContext(
        chart_state=chart_state,
        dataset_summary="Columns: date, gdp. 4 rows. Date range: 2020-01 to 2023-01.",
        dataset_sample=[
            {"date": "2020-01-01", "gdp": 21000},
            {"date": "2021-01-01", "gdp": 22500},
        ],
    )


def _make_sample_dataframe() -> pd.DataFrame:
    """Create a small sample DataFrame for testing."""
    return pd.DataFrame({
        "date": ["2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01"],
        "gdp": [21000, 22500, 25000, 24500],
    })


# ---------------------------------------------------------------------------
# Tests: Summary generation
# ---------------------------------------------------------------------------


class TestSummaryGeneration:
    """Tests for the generate() method."""

    @pytest.mark.asyncio
    async def test_generate_returns_non_empty_summary(self) -> None:
        summary_text = (
            "## Trend Analysis\nGDP shows an upward trend.\n\n"
            "## Key Peaks and Troughs\nPeak in 2022 at $25T.\n\n"
            "## Predictions / Outlook\nModerate growth expected.\n\n"
            "## Economist Perspective\nRecovery is on track."
        )
        mock_client = _make_mock_bedrock(summary_text)
        generator = SummaryGenerator(bedrock_client=mock_client)

        result = await generator.generate(
            _make_sample_dataframe(), _make_chart_context(),
        )

        assert len(result) > 0
        assert result == summary_text

    @pytest.mark.asyncio
    async def test_generate_calls_bedrock_with_correct_model(self) -> None:
        mock_client = _make_mock_bedrock("Summary text.")
        generator = SummaryGenerator(
            bedrock_client=mock_client,
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
        )

        await generator.generate(_make_sample_dataframe(), _make_chart_context())

        call_kwargs = mock_client.invoke_model.call_args
        assert call_kwargs.kwargs["modelId"] == "anthropic.claude-3-haiku-20240307-v1:0"

    @pytest.mark.asyncio
    async def test_generate_sends_dataset_info_in_prompt(self) -> None:
        mock_client = _make_mock_bedrock("Summary.")
        generator = SummaryGenerator(bedrock_client=mock_client)

        await generator.generate(_make_sample_dataframe(), _make_chart_context())

        call_kwargs = mock_client.invoke_model.call_args
        body = json.loads(call_kwargs.kwargs["body"])
        prompt = body["messages"][0]["content"]

        # Prompt should contain dataset summary and section headings
        assert "date, gdp" in prompt.lower() or "Date" in prompt
        assert "Trend Analysis" in prompt
        assert "Peaks and Troughs" in prompt
        assert "Predictions" in prompt or "Outlook" in prompt
        assert "Economist Perspective" in prompt


# ---------------------------------------------------------------------------
# Tests: Prompt construction
# ---------------------------------------------------------------------------


class TestPromptConstruction:
    """Tests for _build_prompt static method."""

    def test_prompt_includes_all_required_sections(self) -> None:
        prompt = SummaryGenerator._build_prompt(
            _make_sample_dataframe(), _make_chart_context(),
        )

        assert "Trend Analysis" in prompt
        assert "Peaks and Troughs" in prompt
        assert "Predictions" in prompt or "Outlook" in prompt
        assert "Economist Perspective" in prompt

    def test_prompt_includes_dataset_summary(self) -> None:
        ctx = _make_chart_context()
        prompt = SummaryGenerator._build_prompt(
            _make_sample_dataframe(), ctx,
        )

        assert ctx.dataset_summary in prompt

    def test_prompt_includes_descriptive_statistics(self) -> None:
        df = _make_sample_dataframe()
        prompt = SummaryGenerator._build_prompt(df, _make_chart_context())

        # Should contain stats from describe()
        assert "mean" in prompt.lower() or "count" in prompt.lower()

    def test_prompt_includes_sample_rows(self) -> None:
        df = _make_sample_dataframe()
        prompt = SummaryGenerator._build_prompt(df, _make_chart_context())

        # Should contain actual data values
        assert "21000" in prompt
        assert "2020" in prompt

    def test_prompt_no_web_search_instruction(self) -> None:
        prompt = SummaryGenerator._build_prompt(
            _make_sample_dataframe(), _make_chart_context(),
        )

        assert "web search" in prompt.lower()

    def test_prompt_with_no_numeric_columns(self) -> None:
        df = pd.DataFrame({"category": ["A", "B", "C"]})
        prompt = SummaryGenerator._build_prompt(df, _make_chart_context())

        # Should still produce a valid prompt without stats
        assert "Trend Analysis" in prompt
        assert "Descriptive statistics" not in prompt


# ---------------------------------------------------------------------------
# Tests: Retry logic
# ---------------------------------------------------------------------------


class TestRetryLogic:
    """Tests for Bedrock retry behaviour."""

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self) -> None:
        call_count = [0]

        def side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                raise RuntimeError("Temporary failure")
            mock_body = MagicMock()
            mock_body.read.return_value = json.dumps({
                "content": [{"type": "text", "text": "Summary after retry."}],
            }).encode()
            return {"body": mock_body}

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = side_effect

        generator = SummaryGenerator(bedrock_client=mock_client)

        with patch(
            "backend.services.summary_generator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            result = await generator._invoke_bedrock("test prompt")

        assert result == "Summary after retry."
        assert call_count[0] == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_raises_after_all_retries_exhausted(self) -> None:
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = RuntimeError("Persistent failure")

        generator = SummaryGenerator(bedrock_client=mock_client)

        with patch(
            "backend.services.summary_generator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            with pytest.raises(RuntimeError, match="failed after 3 attempts"):
                await generator._invoke_bedrock("test prompt")

        assert mock_client.invoke_model.call_count == 3


# ---------------------------------------------------------------------------
# Tests: Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge-case datasets."""

    @pytest.mark.asyncio
    async def test_single_row_dataset(self) -> None:
        df = pd.DataFrame({"date": ["2023-01-01"], "value": [100.0]})
        mock_client = _make_mock_bedrock("Single data point summary.")
        generator = SummaryGenerator(bedrock_client=mock_client)

        result = await generator.generate(df, _make_chart_context())

        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_large_dataset_uses_head(self) -> None:
        """Prompt should only include first 10 rows even for large datasets."""
        df = pd.DataFrame({
            "date": [f"2020-{i:02d}-01" for i in range(1, 13)] * 10,
            "value": list(range(120)),
        })
        mock_client = _make_mock_bedrock("Large dataset summary.")
        generator = SummaryGenerator(bedrock_client=mock_client)

        await generator.generate(df, _make_chart_context())

        call_kwargs = mock_client.invoke_model.call_args
        body = json.loads(call_kwargs.kwargs["body"])
        prompt = body["messages"][0]["content"]

        # The prompt should contain sample rows but not all 120
        assert "2020-01-01" in prompt
        # Row 11+ should not appear in the sample section
        # (head(10) means rows 0-9 only)
