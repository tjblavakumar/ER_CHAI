"""Unit tests for the AI Assistant Handler service.

Covers:
- Session management (create, reset, history tracking)
- Intent classification routing
- Chart modification with mocked Bedrock responses
- Data Q&A with mocked Bedrock responses
- Retry logic on Bedrock failures
- Response structure validity
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.models.schemas import (
    AIResponse,
    AnnotationConfig,
    AxesConfig,
    ChartConfigDelta,
    ChartContext,
    ChartElementState,
    ChartState,
    DataTableConfig,
    GridlineConfig,
    LegendConfig,
    LegendEntry,
    Position,
    SeriesConfig,
)
from backend.services.ai_assistant import AIAssistantHandler


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
            text="Test Chart", position=Position(x=100, y=10)
        ),
        axes=AxesConfig(x_label="Date", y_label="Value"),
        series=[
            SeriesConfig(name="GDP", column="gdp", chart_type="line", color="#003B5C"),
        ],
        legend=LegendConfig(
            visible=True,
            position=Position(x=400, y=50),
            entries=[LegendEntry(label="GDP", color="#003B5C", series_name="gdp")],
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
        dataset_summary="Columns: date, gdp. 100 rows. Date range: 2020-01 to 2024-01.",
        dataset_sample=[
            {"date": "2020-01-01", "gdp": 21000},
            {"date": "2020-04-01", "gdp": 19500},
        ],
    )


# ---------------------------------------------------------------------------
# Tests: Session management
# ---------------------------------------------------------------------------


class TestSessionManagement:
    """Tests for session creation, tracking, and reset."""

    def test_new_session_created_on_first_message(self) -> None:
        handler = AIAssistantHandler(bedrock_client=MagicMock())
        assert "session-1" not in handler._sessions
        # Initialise session manually (handle_message does this)
        handler._sessions["session-1"] = []
        assert handler._sessions["session-1"] == []

    def test_reset_session_clears_history(self) -> None:
        handler = AIAssistantHandler(bedrock_client=MagicMock())
        handler._sessions["session-1"] = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        handler.reset_session("session-1")
        assert "session-1" not in handler._sessions

    def test_reset_nonexistent_session_is_noop(self) -> None:
        handler = AIAssistantHandler(bedrock_client=MagicMock())
        handler.reset_session("does-not-exist")  # should not raise

    @pytest.mark.asyncio
    async def test_session_history_grows_with_messages(self) -> None:
        mock_client = _make_mock_bedrock("data_qa")
        handler = AIAssistantHandler(bedrock_client=mock_client)
        ctx = _make_chart_context()

        # First call classifies as data_qa, second call answers
        call_count = 0
        original_invoke = mock_client.invoke_model

        def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            body = json.loads(kwargs.get("body", "{}"))
            msg = body.get("messages", [{}])[0].get("content", "")
            if "classifier" in msg.lower() or "classify" in msg.lower():
                mock_body = MagicMock()
                mock_body.read.return_value = json.dumps({
                    "content": [{"type": "text", "text": "data_qa"}],
                }).encode()
                return {"body": mock_body}
            mock_body = MagicMock()
            mock_body.read.return_value = json.dumps({
                "content": [{"type": "text", "text": "The trend is upward."}],
            }).encode()
            return {"body": mock_body}

        mock_client.invoke_model.side_effect = side_effect

        await handler.handle_message("s1", "what is the trend?", ctx)
        assert len(handler._sessions["s1"]) == 2  # user + assistant

        await handler.handle_message("s1", "when was the peak?", ctx)
        assert len(handler._sessions["s1"]) == 4  # 2 more entries


# ---------------------------------------------------------------------------
# Tests: Intent classification
# ---------------------------------------------------------------------------


class TestIntentClassification:
    """Tests for intent routing based on Bedrock classification."""

    @pytest.mark.asyncio
    async def test_classify_chart_modify(self) -> None:
        mock_client = _make_mock_bedrock("chart_modify")
        handler = AIAssistantHandler(bedrock_client=mock_client)
        result = await handler._classify_intent("change to bar chart")
        assert result == "chart_modify"

    @pytest.mark.asyncio
    async def test_classify_data_qa(self) -> None:
        mock_client = _make_mock_bedrock("data_qa")
        handler = AIAssistantHandler(bedrock_client=mock_client)
        result = await handler._classify_intent("what is the trend?")
        assert result == "data_qa"

    @pytest.mark.asyncio
    async def test_classify_with_quotes(self) -> None:
        mock_client = _make_mock_bedrock('"chart_modify"')
        handler = AIAssistantHandler(bedrock_client=mock_client)
        result = await handler._classify_intent("make the title bigger")
        assert result == "chart_modify"

    @pytest.mark.asyncio
    async def test_classify_ambiguous_defaults_to_data_qa(self) -> None:
        mock_client = _make_mock_bedrock("something unexpected")
        handler = AIAssistantHandler(bedrock_client=mock_client)
        result = await handler._classify_intent("hello")
        assert result == "data_qa"


# ---------------------------------------------------------------------------
# Tests: Chart modification
# ---------------------------------------------------------------------------


class TestChartModify:
    """Tests for chart modification via handle_message."""

    @pytest.mark.asyncio
    async def test_chart_modify_returns_delta(self) -> None:
        delta_json = json.dumps({"chart_type": "bar"})
        call_count = [0]

        def side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # Intent classification
                text = "chart_modify"
            else:
                # Chart modification
                text = delta_json
            mock_body = MagicMock()
            mock_body.read.return_value = json.dumps({
                "content": [{"type": "text", "text": text}],
            }).encode()
            return {"body": mock_body}

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = side_effect

        handler = AIAssistantHandler(bedrock_client=mock_client)
        ctx = _make_chart_context()

        response = await handler.handle_message("s1", "change to bar chart", ctx)

        assert response.type == "chart_modify"
        assert response.chart_delta is not None
        assert response.chart_delta.chart_type == "bar"

    @pytest.mark.asyncio
    async def test_chart_modify_with_title_change(self) -> None:
        delta_json = json.dumps({
            "title": {
                "text": "New Title",
                "font_family": "Arial",
                "font_size": 18,
                "font_color": "#000000",
                "position": {"x": 100, "y": 10},
            }
        })
        call_count = [0]

        def side_effect(**kwargs):
            call_count[0] += 1
            text = "chart_modify" if call_count[0] == 1 else delta_json
            mock_body = MagicMock()
            mock_body.read.return_value = json.dumps({
                "content": [{"type": "text", "text": text}],
            }).encode()
            return {"body": mock_body}

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = side_effect

        handler = AIAssistantHandler(bedrock_client=mock_client)
        ctx = _make_chart_context()

        response = await handler.handle_message("s1", "change title to New Title", ctx)

        assert response.type == "chart_modify"
        assert response.chart_delta.title is not None
        assert response.chart_delta.title.text == "New Title"


# ---------------------------------------------------------------------------
# Tests: Data Q&A
# ---------------------------------------------------------------------------


class TestDataQA:
    """Tests for data Q&A via handle_message."""

    @pytest.mark.asyncio
    async def test_data_qa_returns_text_answer(self) -> None:
        call_count = [0]

        def side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                text = "data_qa"
            else:
                text = "GDP peaked in Q3 2023 at $25 trillion."
            mock_body = MagicMock()
            mock_body.read.return_value = json.dumps({
                "content": [{"type": "text", "text": text}],
            }).encode()
            return {"body": mock_body}

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = side_effect

        handler = AIAssistantHandler(bedrock_client=mock_client)
        ctx = _make_chart_context()

        response = await handler.handle_message("s1", "when was the peak?", ctx)

        assert response.type == "data_qa"
        assert response.chart_delta is None
        assert "peaked" in response.message.lower() or "25" in response.message

    @pytest.mark.asyncio
    async def test_data_qa_message_is_non_empty(self) -> None:
        call_count = [0]

        def side_effect(**kwargs):
            call_count[0] += 1
            text = "data_qa" if call_count[0] == 1 else "The trend is upward."
            mock_body = MagicMock()
            mock_body.read.return_value = json.dumps({
                "content": [{"type": "text", "text": text}],
            }).encode()
            return {"body": mock_body}

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = side_effect

        handler = AIAssistantHandler(bedrock_client=mock_client)
        ctx = _make_chart_context()

        response = await handler.handle_message("s1", "explain the data", ctx)

        assert response.type == "data_qa"
        assert len(response.message) > 0


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
                "content": [{"type": "text", "text": "data_qa"}],
            }).encode()
            return {"body": mock_body}

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = side_effect

        handler = AIAssistantHandler(bedrock_client=mock_client)

        with patch("backend.services.ai_assistant.asyncio.sleep", new_callable=AsyncMock):
            result = await handler._classify_intent("test")

        assert result == "data_qa"
        assert call_count[0] == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_raises_after_all_retries_exhausted(self) -> None:
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = RuntimeError("Persistent failure")

        handler = AIAssistantHandler(bedrock_client=mock_client)

        with patch("backend.services.ai_assistant.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="failed after 3 attempts"):
                await handler._invoke_bedrock("test prompt")

        assert mock_client.invoke_model.call_count == 3


# ---------------------------------------------------------------------------
# Tests: Parse chart delta
# ---------------------------------------------------------------------------


class TestParseChartDelta:
    """Tests for JSON parsing of chart modification responses."""

    def test_parse_valid_delta(self) -> None:
        text = '{"chart_type": "bar"}'
        delta = AIAssistantHandler._parse_chart_delta(text)
        assert delta.chart_type == "bar"
        assert delta.title is None  # unchanged fields are None

    def test_parse_delta_with_markdown_fences(self) -> None:
        text = '```json\n{"chart_type": "mixed"}\n```'
        delta = AIAssistantHandler._parse_chart_delta(text)
        assert delta.chart_type == "mixed"

    def test_parse_empty_delta(self) -> None:
        text = "{}"
        delta = AIAssistantHandler._parse_chart_delta(text)
        assert delta.chart_type is None
        assert delta.title is None

    def test_parse_invalid_json_raises(self) -> None:
        with pytest.raises(ValueError, match="Failed to parse"):
            AIAssistantHandler._parse_chart_delta("not json at all")
