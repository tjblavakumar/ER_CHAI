// TypeScript types mirroring backend Pydantic models (backend/models/schemas.py)

// --- Chart Configuration ---

export interface Position {
  x: number;
  y: number;
}

export interface ChartElementState {
  text: string;
  font_family: string;
  font_size: number;
  font_color: string;
  position: Position;
}

export interface AxesConfig {
  x_label: string;
  y_label: string;
  x_min: number | string | null;
  x_max: number | string | null;
  y_min: number | null;
  y_max: number | null;
  x_scale: string;
  y_scale: string;
  y_format: string;
  line_width: number;
  tick_font_size: number;
  label_font_size: number;
}

export interface SeriesConfig {
  name: string;
  column: string;
  chart_type: string; // "line" | "bar" | "area"
  color: string;
  line_width: number;
  visible: boolean;
}

export interface LegendEntry {
  label: string;
  color: string;
  series_name: string;
  font_size: number;
  font_color: string;
  font_family: string;
}

export interface LegendConfig {
  visible: boolean;
  position: Position;
  entries: LegendEntry[];
}

export interface GridlineConfig {
  horizontal_visible: boolean;
  vertical_visible: boolean;
  style: string; // "solid" | "dashed" | "dotted"
  color: string;
}

export interface AnnotationConfig {
  id: string;
  type: string; // "text" | "vertical_band" | "horizontal_line" | "vertical_line"
  text: string | null;
  position: Position;
  font_size: number;
  font_color: string;
  band_start: string | null;
  band_end: string | null;
  band_color: string | null;
  line_value: number | string | null;  // y-value for horizontal_line, date string for vertical_line
  line_color: string;         // color for horizontal_line
  line_style: string;         // "solid" | "dashed" | "dotted"
  line_width: number;
}

export interface ComputedColumnDefinition {
  label: string;
  formula: string;
  operands: number[];
}

export interface DataTableConfig {
  visible: boolean;
  position: Position;
  columns: string[];
  font_size: number;
  max_rows: number;
  col_width?: number;
  row_height?: number;
  series_col_width?: number;
  computed_columns?: ComputedColumnDefinition[];
  computed_values?: Record<string, number | null>;
  // Custom table mode
  custom_headers?: string[];
  custom_rows?: Record<string, string>[];
}

export interface DisplayTransform {
  column: string;
  operation: string; // "multiply" | "divide" | "add" | "subtract" | "percent_change" | "normalize"
  factor?: number;
  base_value?: number | null;
  suffix?: string;
  label?: string;
}

export interface ChartState {
  chart_type: string; // "line" | "bar" | "area" | "mixed"
  title: ChartElementState;
  axes: AxesConfig;
  series: SeriesConfig[];
  legend: LegendConfig;
  gridlines: GridlineConfig;
  annotations: AnnotationConfig[];
  data_table: DataTableConfig | null;
  elements_positions: Record<string, Position>;
  dataset_path: string;
  dataset_columns: string[];
  // Categorical bar chart support
  bar_grouping?: string;       // "by_series" | "by_category"
  category_column?: string | null;
  group_column?: string | null;
  bar_stacking?: string;       // "grouped" | "stacked"
  // Display transforms
  display_transforms?: DisplayTransform[];
}

// --- AI ---

export interface ChartConfigDelta {
  chart_type?: string | null;
  title?: ChartElementState | null;
  axes?: AxesConfig | null;
  series?: SeriesConfig[] | null;
  legend?: LegendConfig | null;
  gridlines?: GridlineConfig | null;
  annotations?: AnnotationConfig[] | null;
  data_table?: DataTableConfig | null;
  bar_grouping?: string | null;
  bar_stacking?: string | null;
  display_transforms?: DisplayTransform[] | null;
}

export interface ChartContext {
  chart_state: ChartState;
  dataset_summary: string;
  dataset_sample: Record<string, unknown>[];
}

export interface AIResponse {
  type: string; // "chart_modify" | "data_qa" | "summary_update" | "suggestion"
  message: string;
  chart_delta: ChartConfigDelta | null;
  replace_summary?: boolean;
  suggestions?: { label: string; delta: ChartConfigDelta }[] | null;
}

// --- Project ---

export interface Project {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  chart_state: ChartState;
  dataset_path: string;
  summary_text: string;
}

export interface ProjectCreate {
  name: string;
  chart_state: ChartState;
  dataset_path: string;
  summary_text?: string;
}

export interface ProjectUpdate {
  name?: string | null;
  chart_state?: ChartState | null;
  summary_text?: string | null;
}

export interface ProjectSummary {
  id: string;
  name: string;
  updated_at: string;
}

// --- Ingestion ---

export interface DatasetInfo {
  columns: string[];
  row_count: number;
  date_range: string | null;
  source: string; // "fred" | "upload"
}

export interface IngestionResult {
  dataset_path: string;
  chart_state: ChartState;
  dataset_info: DatasetInfo;
  dataset_rows: Record<string, unknown>[] | null;
}

// --- Error ---

export interface ErrorResponse {
  error: string;
  message: string;
  details?: Record<string, unknown> | null;
}

// --- Frontend-only: Chat UI ---

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  chartDelta?: ChartConfigDelta;
  suggestions?: { label: string; delta: ChartConfigDelta }[];
  timestamp: string;
}
