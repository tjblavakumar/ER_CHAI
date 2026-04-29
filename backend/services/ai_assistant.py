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
        region: str = "us-east-1",
        model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
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
            # Detect structural/direct actions that should bypass advisory mode
            msg_lower = message.lower()
            _DIRECT_ACTION_KEYWORDS = [
                "delete", "remove", "hide", "show", "toggle",
                "change to line", "change to bar", "change to area",
                "switch to line", "switch to bar", "switch to area",
                "make it a line", "make it a bar", "make it an area",
                "stacked", "grouped", "undo", "reset",
                "add annotation", "add h-line", "add v-line", "add v-band",
                "add horizontal", "add vertical",
            ]
            is_direct_action = any(kw in msg_lower for kw in _DIRECT_ACTION_KEYWORDS)

            if is_direct_action:
                # Apply directly without suggestions
                delta = await self._handle_chart_modify(session_id, message, chart_context)
                self._sessions[session_id].append({"role": "user", "content": message})
                self._sessions[session_id].append({
                    "role": "assistant",
                    "content": f"Applied: {delta.model_dump_json(exclude_none=True)}",
                })
                return AIResponse(
                    type="chart_modify",
                    message="Done! I've applied the change.",
                    chart_delta=delta,
                )

            # Styling changes — generate suggestions
            suggestions = await self._generate_suggestions(session_id, message, chart_context)
            self._sessions[session_id].append({"role": "user", "content": message})
            suggestion_dicts = [
                {"label": s["label"], "delta": s["delta"].model_dump(exclude_none=True)}
                for s in suggestions
            ]
            labels = ", ".join(s["label"] for s in suggestions)
            self._sessions[session_id].append({
                "role": "assistant",
                "content": f"Suggested options: {labels}",
            })
            return AIResponse(
                type="suggestion",
                message=suggestions[0].get("message", "Here are a few professional options. Pick the one you prefer:"),
                chart_delta=None,
                suggestions=suggestion_dicts,
            )
        elif intent == "summary_update":
            summary_text, replace_flag = await self._handle_summary_update(session_id, message, chart_context)
            self._sessions[session_id].append({"role": "user", "content": message})
            self._sessions[session_id].append({"role": "assistant", "content": summary_text})
            return AIResponse(
                type="summary_update",
                message=summary_text,
                chart_delta=None,
                replace_summary=replace_flag,
            )
        else:
            answer = await self._handle_data_qa(session_id, message, chart_context)
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
    ) -> Literal["chart_modify", "data_qa", "summary_update"]:
        """Use Bedrock to classify *message*."""
        prompt = (
            "You are an intent classifier for a chart editing application.\n"
            "Classify the following user message into exactly one category:\n"
            '- "chart_modify": The user wants to change the chart appearance '
            "(e.g., change chart type, colors, fonts, add annotations, "
            "modify axes, update title, legend, gridlines, etc.)\n"
            '- "data_qa": The user is asking a question about the data '
            "(e.g., trends, peaks, values, comparisons, explanations)\n"
            '- "summary_update": The user wants to update, append to, or modify '
            "the executive summary text (e.g., 'append this to summary', "
            "'update the executive summary', 'add this info to summary')\n\n"
            f"User message: {message}\n\n"
            "Respond with ONLY the category name, nothing else."
        )

        response_text = await self._invoke_bedrock(prompt)
        cleaned = response_text.strip().strip('"').strip("'").lower()

        if "chart_modify" in cleaned:
            return "chart_modify"
        if "summary_update" in cleaned:
            return "summary_update"
        if "data_qa" in cleaned:
            return "data_qa"

        # Default to data_qa if classification is ambiguous
        return "data_qa"

    # -- Suggestion generation -----------------------------------------------

    async def _generate_suggestions(
        self,
        session_id: str,
        message: str,
        chart_context: ChartContext,
    ) -> list[dict]:
        """Generate multiple chart modification suggestions for the user to choose from.

        Returns a list of dicts with 'label', 'delta' (ChartConfigDelta), and 'message'.
        For simple/structural changes, returns a single option (applied directly).
        For styling changes (colors, fonts), returns 2-3 professional options.
        """
        history = self._sessions.get(session_id, [])
        history_text = ""
        if history:
            history_text = "Previous conversation:\n"
            for entry in history[-6:]:
                history_text += f"{entry['role']}: {entry['content']}\n"
            history_text += "\n"

        chart_state_json = chart_context.chart_state.model_dump_json()

        prompt = (
            "You are an AI style advisor for a professional chart editing application.\n"
            "The user wants to modify their chart. You MUST provide multiple options.\n\n"
            f"{history_text}"
            f"Current chart state:\n{chart_state_json}\n\n"
            f"User request: {message}\n\n"
            "CRITICAL RULES:\n"
            "1. You MUST ALWAYS return 2-3 options in the suggestions array.\n"
            "2. For COLOR changes: suggest 3 professional, publication-quality color palettes.\n"
            "3. For FONT SIZE changes: suggest 3 sizes (e.g., 'Compact 10px', 'Standard 14px', 'Presentation 18px').\n"
            "4. For STRUCTURAL changes (add/delete annotation, toggle visibility, change chart type): "
            "still return 2 options (e.g., the requested change + an alternative).\n"
            "5. For THEME changes: suggest 3 complete color schemes.\n"
            "6. NEVER return just 1 suggestion. Always give the user choices.\n\n"
            "Return EXACTLY this JSON format:\n"
            '{"suggestions": [\n'
            '  {"label": "Short Name", "description": "Why this option is good", "delta": {chart delta}},\n'
            '  {"label": "Short Name 2", "description": "Why this is different", "delta": {chart delta}},\n'
            '  {"label": "Short Name 3", "description": "Another approach", "delta": {chart delta}}\n'
            ']}\n\n'
            "Each delta follows the chart modification format. "
            "Valid fields: chart_type, title, axes, series, legend, gridlines, "
            "annotations, data_table, bar_grouping, bar_stacking, display_transforms.\n\n"
            "IMPORTANT: If you include 'series' in a delta, each series MUST have ALL fields: "
            "name, column, chart_type, color, line_width, visible. Copy from current state.\n"
            "If you include 'legend', it MUST have ALL fields: visible, position, entries.\n\n"
            "Return ONLY valid JSON. No markdown fences. No explanation outside JSON."
        )

        response_text = await self._invoke_bedrock(prompt)
        logger.info("AI suggestions raw response: %s", response_text[:500])

        # Parse the suggestions
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Fallback: treat as a single direct modification
            delta = await self._handle_chart_modify(session_id, message, chart_context)
            return [{"label": "Apply Change", "delta": delta, "message": "Applied the change."}]

        suggestions_raw = data.get("suggestions", [])
        if not suggestions_raw or not isinstance(suggestions_raw, list):
            # Fallback
            delta = await self._handle_chart_modify(session_id, message, chart_context)
            return [{"label": "Apply Change", "delta": delta, "message": "Applied the change."}]

        results = []
        for s in suggestions_raw:
            if not isinstance(s, dict) or "delta" not in s:
                continue
            try:
                # Use the same delta parser with merging
                delta_json = json.dumps(s["delta"])
                delta = self._parse_chart_delta(delta_json, chart_context.chart_state)
                label = s.get("label", f"Option {len(results) + 1}")
                desc = s.get("description", "")
                results.append({
                    "label": label,
                    "delta": delta,
                    "message": desc,
                })
            except Exception as exc:
                logger.warning("Failed to parse suggestion delta: %s", exc)
                continue

        if not results:
            # Fallback
            delta = await self._handle_chart_modify(session_id, message, chart_context)
            return [{"label": "Apply Change", "delta": delta, "message": "Applied the change."}]

        # Add a message to the first suggestion
        if results:
            results[0]["message"] = "Here are a few professional options. Pick the one you prefer:"

        return results

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
            "legend, gridlines, annotations, data_table, bar_grouping.\n"
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
            '- "text": text label at a position. Fields: text, font_size, font_color, position.\n'
            '- "vertical_band": shaded vertical band. Fields: band_start, band_end, band_color, '
            "text (optional label), font_size, font_color.\n"
            '- "horizontal_line": reference line across chart at a Y value. '
            "Fields: line_value (Y value), text (label), font_size (label size), "
            "font_color (label color), line_color, line_style (dotted/dashed/solid), line_width.\n"
            '- "vertical_line": vertical line at a date/year. '
            "Fields: line_value (date or year), text (label), font_size (label size), "
            "font_color (label color), line_color, line_style, line_width.\n"
            "All annotation types support font_size and font_color for their label text.\n"
            'Example: {"annotations": [{"type": "horizontal_line", "line_value": 2.0, '
            '"text": "Target 2%", "font_size": 12, "font_color": "#cc0000", '
            '"line_color": "#cc0000", "line_style": "dotted"}]}\n'
            "IMPORTANT: When adding annotations, include ONLY the NEW annotation(s) "
            "in the annotations array. Do NOT include existing annotations — they will "
            "be preserved automatically. Each annotation needs a unique id.\n"
            "To REMOVE an annotation, include it in the annotations array with its id "
            'and add "_delete": true. Example: {"annotations": [{"id": "financial_crisis_line", "_delete": true}]}\n'
            "You can remove multiple annotations at once by including multiple objects with _delete.\n\n"
            "CHART TYPE: When changing chart_type to 'area', set chart_type at the top level. "
            "The system will automatically propagate it to all series.\n\n"
            "BAR GROUPING: For bar charts, the 'bar_grouping' field controls how bars are arranged:\n"
            "- 'by_series' (default): bars grouped by x-axis position, series side by side\n"
            "- 'by_category': bars grouped by category (e.g., all Energy bars together, "
            "all Food bars together). Use this when the user asks to group bars by category, "
            "put similar items together, or cluster bars.\n"
            'Example: {"bar_grouping": "by_category"} groups bars by category\n'
            'Example: {"bar_grouping": "by_series"} returns to default grouping\n\n'
            "BAR STACKING: The 'bar_stacking' field controls whether bars are grouped or stacked:\n"
            "- 'grouped' (default): bars side by side\n"
            "- 'stacked': bars stacked on top of each other (shows composition and total)\n"
            'Example: {"bar_stacking": "stacked"} stacks bars\n\n'
            "DATA TABLE: The 'data_table' field controls the data table shown on the chart.\n"
            "Fields: visible (bool), columns (list of column names to show), "
            "max_rows (number of date columns), font_size (6-24).\n"
            "- To hide: {\"data_table\": {\"visible\": false, ...copy other fields}}\n"
            "- To show: {\"data_table\": {\"visible\": true, ...copy other fields}}\n"
            "- To change columns shown: set 'columns' to the desired list of column names\n"
            "- To change max date columns: set 'max_rows'\n"
            "CUSTOM TABLE: For fully custom tables, use 'custom_headers' and 'custom_rows':\n"
            "- custom_headers: list of column header strings, e.g., [\"Series\", \"in $\", \"in %\"]\n"
            "- custom_rows: list of row objects, e.g., [{\"Series\": \"Energy\", \"in $\": \"4.1\", \"in %\": \"4.1%\"}]\n"
            "When the user asks for a custom table layout, use custom_headers and custom_rows. "
            "Look at the actual data in the current chart state to fill in real values.\n"
            'Example: {"data_table": {"visible": true, "custom_headers": ["Series", "Value", "Change"], '
            '"custom_rows": [{"Series": "GDP", "Value": "21.5T", "Change": "+2.1%"}]}}\n'
            "IMPORTANT: When modifying data_table, include ALL required fields: "
            "visible, position (with x and y), columns, font_size, max_rows. "
            "Copy unchanged fields from the current chart state's data_table.\n"
            "The user may ask to customize what's shown in the data table — "
            "adjust columns, max_rows, font_size, or visibility accordingly.\n\n"
            "IMPORTANT: If you include 'series' in the delta, each series object "
            "MUST include ALL required fields: name, column, chart_type, color, "
            "line_width, visible. Copy unchanged fields from the current chart state.\n\n"
            "DISPLAY TRANSFORMS: The 'display_transforms' field allows non-destructive "
            "value transformations on data columns. Each transform has:\n"
            "- column: the column name to transform\n"
            "- operation: 'multiply', 'divide', 'add', 'subtract', 'normalize'\n"
            "- factor: the numeric factor (for multiply/divide/add/subtract)\n"
            "- base_value: for normalize, the base value to divide by (result * 100)\n"
            "- suffix: display suffix (e.g., 'M' for millions, '%')\n"
            "- label: human-readable description\n"
            "Examples:\n"
            '- Billions to millions: {"display_transforms": [{"column": "value", '
            '"operation": "divide", "factor": 1000, "suffix": "M", '
            '"label": "Billions to Millions"}]}\n'
            '- Show as percentage (multiply by 100): {"display_transforms": [{"column": "value", '
            '"operation": "multiply", "factor": 100, "suffix": "%", '
            '"label": "Convert to percentage"}]}\n'
            '- Clear transforms (show original): {"display_transforms": []}\n'
            "The original data is never modified — transforms are applied on-the-fly.\n"
            "Use this when the user asks to convert units, show as percentage, etc.\n\n"
            "IMPORTANT: If you include 'legend' in the delta, it MUST include ALL "
            "required fields: visible, position (with x and y), entries. "
            "Copy unchanged fields from the current chart state.\n"
            "Each legend entry has: label, color, series_name, font_size, font_color, font_family.\n"
            "When the user asks to change ALL text sizes or ALL font properties, "
            "you MUST also update legend entries' font_size/font_color/font_family "
            "in addition to title, axes tick/label font sizes, and annotation font sizes.\n\n"
            "IMPORTANT: For text/font changes, do NOT include 'series' in the delta — "
            "series controls data rendering, not text display. Only include 'series' "
            "when the user explicitly asks to change series properties (color, chart_type, visibility).\n\n"
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

    # -- Summary update -----------------------------------------------------

    async def _handle_summary_update(
        self,
        session_id: str,
        message: str,
        chart_context: ChartContext,
    ) -> tuple[str, bool]:
        """Generate summary text and determine if it should replace or append.
        
        Returns:
            tuple[str, bool]: (summary_text, replace_flag)
                - summary_text: The generated summary content
                - replace_flag: True to replace entire summary, False to append
        """
        history = self._sessions.get(session_id, [])
        history_text = ""
        if history:
            history_text = "Previous conversation:\n"
            for entry in history[-10:]:
                history_text += f"{entry['role']}: {entry['content']}\n"
            history_text += "\n"

        prompt = (
            "You are an AI assistant for an FRBSF chart editing application.\n"
            "The user wants to update the executive summary.\n\n"
            "First, analyze the user's intent:\n"
            "- REPLACE: User wants to create a NEW summary from scratch "
            "(e.g., 'generate new summary', 'create 100-word summary', 'rewrite the summary')\n"
            "- APPEND: User wants to ADD to existing summary "
            "(e.g., 'add a section about', 'append conclusion', 'include risks section')\n\n"
            f"{history_text}"
            f"User request: {message}\n\n"
            "Respond in JSON format:\n"
            "{\n"
            '  "replace": true or false,\n'
            '  "text": "the summary content here in markdown format"\n'
            "}\n\n"
            "Write in a professional, concise style suitable for an executive audience. "
            "Use markdown formatting (headings, lists, bold) as appropriate."
        )

        response_text = await self._invoke_bedrock(prompt)
        
        # Parse the JSON response
        try:
            # Strip markdown fences if present
            text = response_text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                text = "\n".join(lines)
            
            data = json.loads(text)
            summary_text = data.get("text", response_text)
            replace_flag = data.get("replace", False)
            return summary_text, replace_flag
        except (json.JSONDecodeError, KeyError):
            # Fallback: if parsing fails, treat as append and use raw response
            logger.warning("Failed to parse summary update response as JSON, using raw text")
            return response_text, False

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

        # Merge partial title with current chart state
        if "title" in data and isinstance(data["title"], dict) and current_chart_state:
            existing_title = current_chart_state.title.model_dump()
            merged_title = {**existing_title, **data["title"]}
            # Ensure nested position is merged properly
            if "position" not in data["title"] and "position" in existing_title:
                merged_title["position"] = existing_title["position"]
            data["title"] = merged_title

        # Merge partial data_table with current chart state
        if "data_table" in data and isinstance(data["data_table"], dict) and current_chart_state:
            dt = data["data_table"]

            # Detect if the AI tried to create a custom table layout
            # (computed_columns as plain strings, computed_values as dicts)
            has_custom_layout = False
            if "computed_columns" in dt and isinstance(dt["computed_columns"], list):
                if dt["computed_columns"] and isinstance(dt["computed_columns"][0], str):
                    # AI sent column names as strings — convert to custom table
                    has_custom_layout = True
            if "computed_values" in dt and isinstance(dt["computed_values"], dict):
                first_val = next(iter(dt["computed_values"].values()), None)
                if isinstance(first_val, dict):
                    has_custom_layout = True

            if has_custom_layout:
                # Convert AI's creative output to custom_headers + custom_rows
                headers = dt.get("computed_columns", [])
                if isinstance(headers, list) and headers and isinstance(headers[0], str):
                    dt["custom_headers"] = headers
                else:
                    dt["custom_headers"] = []
                dt["computed_columns"] = []

                rows_data = dt.get("computed_values", {})
                custom_rows = []
                if isinstance(rows_data, dict):
                    for key, val in rows_data.items():
                        if isinstance(val, dict):
                            custom_rows.append({k: str(v) for k, v in val.items()})
                        else:
                            custom_rows.append({"value": str(val)})
                dt["custom_rows"] = custom_rows
                dt["computed_values"] = {}

            existing_dt = (current_chart_state.data_table.model_dump()
                           if current_chart_state.data_table else {
                               "visible": False, "position": {"x": 70, "y": 490},
                               "columns": current_chart_state.dataset_columns,
                               "font_size": 10, "max_rows": 5,
                           })
            data["data_table"] = {**existing_dt, **dt}

        # Merge partial gridlines with current chart state
        if "gridlines" in data and isinstance(data["gridlines"], dict) and current_chart_state:
            existing_gridlines = current_chart_state.gridlines.model_dump()
            data["gridlines"] = {**existing_gridlines, **data["gridlines"]}

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
            _TYPE_MAP = {"line": "horizontal_line", "hline": "horizontal_line", "vband": "vertical_band", "vline": "vertical_line"}
            _SUPPORTED_TYPES = {"text", "vertical_band", "horizontal_line", "vertical_line"}
            fixed_annotations: list[dict] = []
            for idx, ann in enumerate(data["annotations"]):
                if not isinstance(ann, dict):
                    continue

                # Handle deletion markers — pass through with minimal fields
                if ann.get("_delete"):
                    fixed_annotations.append({
                        "id": ann.get("id", f"ann_{idx}"),
                        "type": "text",
                        "position": {"x": 0, "y": 0},
                        "_delete": True,
                    })
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
                # Fill in vertical_line defaults
                if ann["type"] == "vertical_line":
                    if "line_value" not in ann:
                        ann["line_value"] = ann.get("value", ann.get("x_value", ann.get("position", {}).get("x", 0)))
                    ann.setdefault("line_color", "#FF0000")
                    ann.setdefault("line_style", "solid")
                    ann.setdefault("line_width", 1.5)
                fixed_annotations.append(ann)
            data["annotations"] = fixed_annotations

        return ChartConfigDelta.model_validate(data)
