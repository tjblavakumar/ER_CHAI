"""AI Assistant Handler for the FRBSF Chart Builder.

Provides conversational chart modification and data Q&A capabilities
using AWS Bedrock. Maintains per-session conversation history in memory.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Literal

import boto3

from backend.models.schemas import (
    AIResponse,
    AnnotationConfig,
    ChartConfigDelta,
    ChartContext,
    ChartState,
    Position,
    SeriesConfig,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_RETRIES = 2
_RETRY_DELAY_SECONDS = 2.0


# ---------------------------------------------------------------------------
# AI Assistant Handler
# ---------------------------------------------------------------------------


class AIAssistantHandler:
    """Orchestrates AI-driven chart modification and data Q&A via Bedrock."""

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
        self._sessions: dict[str, list[dict]] = {}

    # -- Public API ---------------------------------------------------------

    async def handle_message(
        self,
        session_id: str,
        message: str,
        chart_context: ChartContext,
    ) -> AIResponse:
        """Classify intent and route to the appropriate handler.

        Returns an ``AIResponse`` with either a chart delta (for
        modifications) or a text answer (for data Q&A).
        """
        # Ensure session exists
        if session_id not in self._sessions:
            self._sessions[session_id] = []

        intent = await self._classify_intent(message)

        if intent == "chart_modify":
            delta = await self._handle_chart_modify(session_id, message, chart_context)
            # Store the exchange in session history
            self._sessions[session_id].append({"role": "user", "content": message})
            self._sessions[session_id].append({
                "role": "assistant",
                "content": f"Applied chart modifications: {delta.model_dump_json(exclude_none=True)}",
            })
            return AIResponse(
                type="chart_modify",
                message="I've applied the requested chart modifications.",
                chart_delta=delta,
            )
        else:
            answer = await self._handle_data_qa(session_id, message, chart_context)
            # Store the exchange in session history
            self._sessions[session_id].append({"role": "user", "content": message})
            self._sessions[session_id].append({"role": "assistant", "content": answer})
            return AIResponse(
                type="data_qa",
                message=answer,
                chart_delta=None,
            )

    def reset_session(self, session_id: str) -> None:
        """Clear conversation history for *session_id*."""
        self._sessions.pop(session_id, None)

    # -- Intent classification ----------------------------------------------

    async def _classify_intent(
        self, message: str
    ) -> Literal["chart_modify", "data_qa"]:
        """Use Bedrock to classify *message* as chart modification or data Q&A."""
        prompt = (
            "You are an intent classifier for a chart editing application.\n"
            "Classify the following user message into exactly one category:\n"
            '- "chart_modify": The user wants to change the chart appearance '
            "(e.g., change chart type, colors, fonts, add annotations, "
            "modify axes, update title, legend, gridlines, etc.)\n"
            '- "data_qa": The user is asking a question about the data '
            "(e.g., trends, peaks, values, comparisons, explanations)\n\n"
            f"User message: {message}\n\n"
            "Respond with ONLY the category name, nothing else. "
            'Either "chart_modify" or "data_qa".'
        )

        response_text = await self._invoke_bedrock(prompt)
        cleaned = response_text.strip().strip('"').strip("'").lower()

        if "chart_modify" in cleaned:
            return "chart_modify"
        if "data_qa" in cleaned:
            return "data_qa"

        # Default to data_qa if classification is ambiguous
        return "data_qa"

    # -- Chart modification -------------------------------------------------

    async def _handle_chart_modify(
        self,
        session_id: str,
        message: str,
        chart_context: ChartContext,
    ) -> ChartConfigDelta:
        """Generate a ``ChartConfigDelta`` from a natural language command."""
        history = self._sessions.get(session_id, [])
        history_text = ""
        if history:
            history_text = "Previous conversation:\n"
            for entry in history[-6:]:  # last 3 exchanges
                history_text += f"{entry['role']}: {entry['content']}\n"
            history_text += "\n"

        chart_state_json = chart_context.chart_state.model_dump_json()

        prompt = (
            "You are an AI assistant for an FRBSF chart editing application.\n"
            "The user wants to modify their chart. Generate a JSON object "
            "representing ONLY the fields that need to change.\n\n"
            f"{history_text}"
            f"Current chart state:\n{chart_state_json}\n\n"
            f"Dataset summary: {chart_context.dataset_summary}\n\n"
            f"User request: {message}\n\n"
            "Return a JSON object with only the fields that should change. "
            "Valid top-level fields are: chart_type, title, axes, series, "
            "legend, gridlines, annotations, data_table.\n"
            "Omit any field that should not change.\n\n"
            "AXES FORMAT: The axes object supports these styling fields:\n"
            "- 'y_format': controls Y-axis tick display. Values: "
            '"auto", "integer" (whole numbers), "percent" (adds % symbol), '
            '"decimal1", "decimal2"\n'
            "- 'line_width': axis line thickness (default 1, range 0.5-10)\n"
            "- 'tick_font_size': font size for tick labels (default 10)\n"
            "- 'label_font_size': font size for axis labels (default 12)\n"
            'Example: {"axes": {"y_format": "percent"}} adds % to y-axis values\n'
            'Example: {"axes": {"y_format": "integer"}} shows whole numbers\n'
            'Example: {"axes": {"line_width": 5}} makes axis lines thicker\n'
            'Example: {"axes": {"tick_font_size": 14}} makes tick labels bigger\n\n'
            "CHART TYPES: Valid chart_type values are: line, bar, area, mixed.\n"
            "For area charts, set chart_type to 'area' (fills under the line).\n\n"
            "ANNOTATIONS: Supported annotation types:\n"
            '- "text": text label at a position\n'
            '- "vertical_band": shaded vertical band (needs band_start, band_end, band_color)\n'
            '- "horizontal_line": dotted line across chart at a Y value. '
            "Use line_value for the Y value, line_color, line_style (dotted/dashed/solid), line_width.\n"
            'Example: {"annotations": [{"type": "horizontal_line", "line_value": 2.0, '
            '"text": "Target 2%", "line_color": "#cc0000", "line_style": "dotted"}]}\n\n'
            "IMPORTANT: If you include 'series' in the delta, each series object "
            "MUST include ALL required fields: name, column, chart_type, color, "
            "line_width, visible. Copy unchanged fields from the current chart state.\n\n"
            "IMPORTANT: If you include 'legend' in the delta, it MUST include ALL "
            "required fields: visible, position (with x and y), entries. "
            "Copy unchanged fields from the current chart state.\n\n"
            "Return ONLY valid JSON, no markdown fences or explanation."
        )

        response_text = await self._invoke_bedrock(prompt)
        logger.info("AI chart modify raw response: %s", response_text[:500])
        return self._parse_chart_delta(response_text, chart_context.chart_state)

    # -- Data Q&A -----------------------------------------------------------

    async def _handle_data_qa(
        self,
        session_id: str,
        message: str,
        chart_context: ChartContext,
    ) -> str:
        """Answer a data question using the dataset context."""
        history = self._sessions.get(session_id, [])
        history_text = ""
        if history:
            history_text = "Previous conversation:\n"
            for entry in history[-6:]:
                history_text += f"{entry['role']}: {entry['content']}\n"
            history_text += "\n"

        sample_text = json.dumps(chart_context.dataset_sample[:5], default=str)

        prompt = (
            "You are an AI assistant for an FRBSF chart editing application.\n"
            "The user is asking a question about their economic dataset.\n\n"
            f"{history_text}"
            f"Dataset summary: {chart_context.dataset_summary}\n\n"
            f"Sample data (first rows):\n{sample_text}\n\n"
            f"User question: {message}\n\n"
            "Provide a clear, concise answer based on the dataset information. "
            "Use only the provided data and your knowledge. "
            "Do not perform web searches."
        )

        return await self._invoke_bedrock(prompt)

    # -- Bedrock invocation with retry --------------------------------------

    async def _invoke_bedrock(self, prompt: str) -> str:
        """Call Bedrock with retry logic (up to 2 retries, 2s delay).

        Returns the text content from the model response.
        Raises ``RuntimeError`` if all attempts fail.
        """
        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 8192,
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

    # -- Helpers ------------------------------------------------------------

    @staticmethod
    def _parse_chart_delta(
        response_text: str,
        current_chart_state: ChartState | None = None,
    ) -> ChartConfigDelta:
        """Parse a JSON string into a ``ChartConfigDelta``.

        Strips markdown fences if present and handles parse errors gracefully.

        When *current_chart_state* is provided and the delta contains a
        ``series`` array, each partial series object is merged with the
        corresponding existing series so that missing required fields
        (name, column, chart_type, color, line_width, visible) are filled
        in from the current state.
        """
        text = response_text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last fence lines
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Failed to parse chart modification response as JSON: {exc}"
            ) from exc

        # Merge partial axes with current chart state
        if "axes" in data and isinstance(data["axes"], dict) and current_chart_state:
            existing_axes = current_chart_state.axes.model_dump()
            data["axes"] = {**existing_axes, **data["axes"]}

        # Merge partial legend with current chart state
        if "legend" in data and isinstance(data["legend"], dict) and current_chart_state:
            existing_legend = current_chart_state.legend.model_dump()
            merged_legend = {**existing_legend, **data["legend"]}
            # Ensure nested position is merged properly
            if "position" not in data["legend"] and "position" in existing_legend:
                merged_legend["position"] = existing_legend["position"]
            if "entries" not in data["legend"] and "entries" in existing_legend:
                merged_legend["entries"] = existing_legend["entries"]
            if "visible" not in data["legend"] and "visible" in existing_legend:
                merged_legend["visible"] = existing_legend["visible"]
            data["legend"] = merged_legend

        # Merge partial series with current chart state
        if "series" in data and isinstance(data["series"], list) and current_chart_state:
            existing_series = current_chart_state.series
            merged_series: list[dict] = []
            for i, partial in enumerate(data["series"]):
                if not isinstance(partial, dict):
                    continue
                # Find the base series to merge with (by index)
                if i < len(existing_series):
                    base = existing_series[i].model_dump()
                else:
                    # No corresponding existing series; use last existing or empty defaults
                    base = existing_series[-1].model_dump() if existing_series else {
                        "name": f"series_{i}",
                        "column": "",
                        "chart_type": "line",
                        "color": "#003B5C",
                        "line_width": 2.0,
                        "visible": True,
                    }
                # Override base with any fields the LLM provided
                base.update(partial)
                merged_series.append(base)
            data["series"] = merged_series

        # Merge / fix annotations from LLM output
        if "annotations" in data and isinstance(data["annotations"], list):
            _TYPE_MAP = {"line": "horizontal_line", "hline": "horizontal_line", "vband": "vertical_band"}
            _SUPPORTED_TYPES = {"text", "vertical_band", "horizontal_line"}
            fixed_annotations: list[dict] = []
            for idx, ann in enumerate(data["annotations"]):
                if not isinstance(ann, dict):
                    continue
                # Generate id if missing
                if "id" not in ann:
                    ann["id"] = f"ann_{idx}"
                # Map unsupported types
                ann_type = ann.get("type", "text")
                ann["type"] = _TYPE_MAP.get(ann_type, ann_type)
                if ann["type"] not in _SUPPORTED_TYPES:
                    ann["type"] = "text"
                # Construct position if missing or incomplete
                if "position" not in ann:
                    px = ann.pop("x1", None) or ann.pop("x", 0)
                    py = ann.pop("y1", None) or ann.pop("y", 0)
                    ann["position"] = {"x": float(px), "y": float(py)}
                elif isinstance(ann["position"], dict):
                    # Ensure both x and y exist in position
                    pos = ann["position"]
                    if "x" not in pos:
                        pos["x"] = float(ann.pop("x1", None) or ann.pop("x", 0))
                    if "y" not in pos:
                        pos["y"] = float(ann.pop("y1", None) or ann.pop("y", 0))
                # Fill in default font properties
                ann.setdefault("font_size", 10)
                ann.setdefault("font_color", "#333333")
                # Fill in horizontal_line defaults
                if ann["type"] == "horizontal_line":
                    if "line_value" not in ann:
                        ann["line_value"] = ann.get("value", ann.get("y_value", ann.get("y", 0)))
                    ann.setdefault("line_color", "#cc0000")
                    ann.setdefault("line_style", "dotted")
                    ann.setdefault("line_width", 1.5)
                fixed_annotations.append(ann)
            data["annotations"] = fixed_annotations

        return ChartConfigDelta.model_validate(data)
