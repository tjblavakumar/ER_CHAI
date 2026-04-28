import React, { useState, useCallback } from 'react';
import { useAppStore } from '../store/appStore';
import type { ChartState, AxesConfig, SeriesConfig, GridlineConfig, LegendConfig, AnnotationConfig, DataTableConfig } from '../types';

/* ------------------------------------------------------------------ */
/*  Collapsible section wrapper                                       */
/* ------------------------------------------------------------------ */

const Section: React.FC<{ title: string; defaultOpen?: boolean; children: React.ReactNode }> = ({
  title,
  defaultOpen = false,
  children,
}) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ marginBottom: 12, borderBottom: '1px solid #e0e0e0' }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: '100%',
          textAlign: 'left',
          background: 'none',
          border: 'none',
          padding: '8px 0',
          fontWeight: 600,
          fontSize: 13,
          cursor: 'pointer',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        {title}
        <span style={{ fontSize: 11 }}>{open ? '▲' : '▼'}</span>
      </button>
      {open && <div style={{ paddingBottom: 10 }}>{children}</div>}
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Tiny reusable field row                                           */
/* ------------------------------------------------------------------ */

const Field: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6, fontSize: 12 }}>
    <label style={{ width: 90, flexShrink: 0 }}>{label}</label>
    <div style={{ flex: 1 }}>{children}</div>
  </div>
);

/* ------------------------------------------------------------------ */
/*  Helper: shallow-patch chartState via setChartState                */
/* ------------------------------------------------------------------ */

function usePatchChart() {
  const chartState = useAppStore((s) => s.chartState);
  const setChartState = useAppStore((s) => s.setChartState);

  return useCallback(
    (partial: Partial<ChartState>) => {
      if (!chartState) return;
      const merged = { ...chartState, ...partial };

      // When global chart_type changes, propagate to all series
      if (partial.chart_type && partial.chart_type !== chartState.chart_type && !partial.series) {
        merged.series = chartState.series.map((s) => ({
          ...s,
          chart_type: partial.chart_type!,
        }));
      }

      setChartState(merged);
    },
    [chartState, setChartState],
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                    */
/* ------------------------------------------------------------------ */

const ControlsPanel: React.FC = () => {
  const chartState = useAppStore((s) => s.chartState);
  const patch = usePatchChart();

  if (!chartState) {
    return (
      <div style={{ padding: 16, color: '#888', fontSize: 13 }}>
        No chart loaded. Ingest data to begin.
      </div>
    );
  }

  const { axes, series, legend, gridlines, annotations, data_table, title } = chartState;

  /* ---- helpers for nested updates ---- */
  const patchAxes = (p: Partial<AxesConfig>) => patch({ axes: { ...axes, ...p } });

  const patchSeries = (idx: number, p: Partial<SeriesConfig>) => {
    const updated = series.map((s, i) => (i === idx ? { ...s, ...p } : s));
    // If color changed, also update the corresponding legend entry
    let updatedLegend = legend;
    if (p.color) {
      const seriesName = series[idx].name;
      const updatedEntries = legend.entries.map((entry) =>
        entry.series_name === seriesName ? { ...entry, color: p.color! } : entry,
      );
      updatedLegend = { ...legend, entries: updatedEntries };
    }
    patch({ series: updated, legend: updatedLegend });
  };

  const patchLegend = (p: Partial<LegendConfig>) => patch({ legend: { ...legend, ...p } });

  const patchGridlines = (p: Partial<GridlineConfig>) =>
    patch({ gridlines: { ...gridlines, ...p } });

  const patchAnnotation = (idx: number, p: Partial<AnnotationConfig>) => {
    const updated = annotations.map((a, i) => (i === idx ? { ...a, ...p } : a));
    patch({ annotations: updated });
  };

  const patchDataTable = (p: Partial<DataTableConfig>) => {
    const current: DataTableConfig = data_table ?? {
      visible: false,
      position: { x: 0, y: 0 },
      columns: [],
      font_size: 10,
      max_rows: 5,
    };
    patch({ data_table: { ...current, ...p } });
  };

  return (
    <div style={{ fontSize: 12 }}>
      {/* ---- Chart Type ---- */}
      <Section title="Chart Type" defaultOpen>
        <Field label="Type">
          <select
            value={chartState.chart_type}
            onChange={(e) => patch({ chart_type: e.target.value })}
            style={{ width: '100%' }}
          >
            <option value="line">Line</option>
            <option value="bar">Bar</option>
            <option value="area">Area</option>
            <option value="mixed">Mixed</option>
          </select>
        </Field>
        {chartState.chart_type === 'bar' && (
          <Field label="Bar Grouping">
            <select
              value={chartState.bar_grouping ?? 'by_series'}
              onChange={(e) => patch({ bar_grouping: e.target.value })}
              style={{ width: '100%' }}
            >
              <option value="by_series">By Series (default)</option>
              <option value="by_category">By Category</option>
            </select>
          </Field>
        )}
      </Section>

      {/* ---- Canvas Size ---- */}
      <Section title="Canvas Size">
        <Field label="Width">
          <input
            type="number"
            min={800}
            max={2400}
            step={50}
            value={useAppStore.getState().canvasWidth}
            onChange={(e) => useAppStore.getState().setCanvasSize(Number(e.target.value), useAppStore.getState().canvasHeight)}
            style={{ width: '100%' }}
          />
        </Field>
        <Field label="Height">
          <input
            type="number"
            min={400}
            max={1600}
            step={50}
            value={useAppStore.getState().canvasHeight}
            onChange={(e) => useAppStore.getState().setCanvasSize(useAppStore.getState().canvasWidth, Number(e.target.value))}
            style={{ width: '100%' }}
          />
        </Field>
      </Section>

      {/* ---- Axes ---- */}
      <Section title="Axes" defaultOpen>
        <Field label="X Label">
          <input
            type="text"
            value={axes.x_label}
            onChange={(e) => patchAxes({ x_label: e.target.value })}
            style={{ width: '100%' }}
          />
        </Field>
        <Field label="Y Label">
          <input
            type="text"
            value={axes.y_label}
            onChange={(e) => patchAxes({ y_label: e.target.value })}
            style={{ width: '100%' }}
          />
        </Field>
        <Field label="X Min">
          <input
            type="number"
            value={axes.x_min ?? ''}
            onChange={(e) => patchAxes({ x_min: e.target.value === '' ? null : Number(e.target.value) })}
            style={{ width: '100%' }}
          />
        </Field>
        <Field label="X Max">
          <input
            type="number"
            value={axes.x_max ?? ''}
            onChange={(e) => patchAxes({ x_max: e.target.value === '' ? null : Number(e.target.value) })}
            style={{ width: '100%' }}
          />
        </Field>
        <Field label="Y Min">
          <input
            type="number"
            value={axes.y_min ?? ''}
            onChange={(e) => patchAxes({ y_min: e.target.value === '' ? null : Number(e.target.value) })}
            style={{ width: '100%' }}
          />
        </Field>
        <Field label="Y Max">
          <input
            type="number"
            value={axes.y_max ?? ''}
            onChange={(e) => patchAxes({ y_max: e.target.value === '' ? null : Number(e.target.value) })}
            style={{ width: '100%' }}
          />
        </Field>
        <Field label="X Scale">
          <select
            value={axes.x_scale}
            onChange={(e) => patchAxes({ x_scale: e.target.value })}
            style={{ width: '100%' }}
          >
            <option value="linear">Linear</option>
            <option value="logarithmic">Logarithmic</option>
          </select>
        </Field>
        <Field label="Y Scale">
          <select
            value={axes.y_scale}
            onChange={(e) => patchAxes({ y_scale: e.target.value })}
            style={{ width: '100%' }}
          >
            <option value="linear">Linear</option>
            <option value="logarithmic">Logarithmic</option>
          </select>
        </Field>
        <Field label="Y Format">
          <select
            value={axes.y_format ?? 'auto'}
            onChange={(e) => patchAxes({ y_format: e.target.value })}
            style={{ width: '100%' }}
          >
            <option value="auto">Auto</option>
            <option value="integer">Whole Number</option>
            <option value="percent">Percent (%)</option>
            <option value="decimal1">1 Decimal</option>
            <option value="decimal2">2 Decimals</option>
          </select>
        </Field>
        <Field label="Line Width">
          <input
            type="number"
            min={0.5}
            max={10}
            step={0.5}
            value={axes.line_width ?? 1}
            onChange={(e) => patchAxes({ line_width: Number(e.target.value) })}
            style={{ width: '100%' }}
          />
        </Field>
        <Field label="Tick Font">
          <input
            type="number"
            min={6}
            max={24}
            value={axes.tick_font_size ?? 10}
            onChange={(e) => patchAxes({ tick_font_size: Number(e.target.value) })}
            style={{ width: '100%' }}
          />
        </Field>
        <Field label="Label Font">
          <input
            type="number"
            min={8}
            max={32}
            value={axes.label_font_size ?? 12}
            onChange={(e) => patchAxes({ label_font_size: Number(e.target.value) })}
            style={{ width: '100%' }}
          />
        </Field>
      </Section>

      {/* ---- Series ---- */}
      <Section title="Data Series">
        {series.map((s, idx) => (
          <div key={s.name} style={{ marginBottom: 8, padding: 6, background: '#f5f5f5', borderRadius: 4 }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>{s.name}</div>
            <Field label="Color">
              <input
                type="color"
                value={s.color}
                onChange={(e) => patchSeries(idx, { color: e.target.value })}
              />
            </Field>
            <Field label="Chart Type">
              <select
                value={s.chart_type}
                onChange={(e) => patchSeries(idx, { chart_type: e.target.value })}
                style={{ width: '100%' }}
              >
                <option value="line">Line</option>
                <option value="bar">Bar</option>
                <option value="area">Area</option>
              </select>
            </Field>
            <Field label="Line Width">
              <input
                type="number"
                min={0.5}
                max={10}
                step={0.5}
                value={s.line_width}
                onChange={(e) => patchSeries(idx, { line_width: Number(e.target.value) })}
                style={{ width: '100%' }}
              />
            </Field>
            <Field label="Visible">
              <input
                type="checkbox"
                checked={s.visible}
                onChange={(e) => patchSeries(idx, { visible: e.target.checked })}
              />
            </Field>
          </div>
        ))}
        {series.length === 0 && <p style={{ color: '#999' }}>No series configured.</p>}
      </Section>

      {/* ---- Title Font ---- */}
      <Section title="Title / Fonts" defaultOpen>
        <Field label="Title Text">
          <input
            type="text"
            value={title.text}
            onChange={(e) => patch({ title: { ...title, text: e.target.value } })}
            style={{ width: '100%' }}
          />
        </Field>
        <Field label="Font Family">
          <select
            value={title.font_family}
            onChange={(e) => patch({ title: { ...title, font_family: e.target.value } })}
            style={{ width: '100%' }}
          >
            <option value="Arial">Arial</option>
            <option value="Helvetica">Helvetica</option>
            <option value="Times New Roman">Times New Roman</option>
            <option value="Georgia">Georgia</option>
            <option value="Courier New">Courier New</option>
            <option value="Greycliff CF">Greycliff CF</option>
          </select>
        </Field>
        <Field label="Font Size">
          <input
            type="number"
            min={8}
            max={48}
            value={title.font_size}
            onChange={(e) => patch({ title: { ...title, font_size: Number(e.target.value) } })}
            style={{ width: '100%' }}
          />
        </Field>
        <Field label="Font Color">
          <input
            type="color"
            value={title.font_color}
            onChange={(e) => patch({ title: { ...title, font_color: e.target.value } })}
          />
        </Field>
      </Section>

      {/* ---- Legend ---- */}
      <Section title="Legend">
        <Field label="Visible">
          <input
            type="checkbox"
            checked={legend.visible}
            onChange={(e) => patchLegend({ visible: e.target.checked })}
          />
        </Field>
        <Field label="X Position">
          <input
            type="number"
            value={legend.position.x}
            onChange={(e) =>
              patchLegend({ position: { ...legend.position, x: Number(e.target.value) } })
            }
            style={{ width: '100%' }}
          />
        </Field>
        <Field label="Y Position">
          <input
            type="number"
            value={legend.position.y}
            onChange={(e) =>
              patchLegend({ position: { ...legend.position, y: Number(e.target.value) } })
            }
            style={{ width: '100%' }}
          />
        </Field>
        {legend.entries.map((entry, idx) => (
          <div key={entry.series_name} style={{ marginBottom: 8, padding: 6, background: '#f5f5f5', borderRadius: 4 }}>
            <div style={{ fontWeight: 600, marginBottom: 4, fontSize: 11, color: entry.color }}>{entry.label}</div>
            <Field label="Label">
              <input
                type="text"
                value={entry.label}
                onChange={(e) => {
                  const updated = legend.entries.map((en, i) => i === idx ? { ...en, label: e.target.value } : en);
                  patchLegend({ entries: updated });
                }}
                style={{ width: '100%' }}
              />
            </Field>
            <Field label="Font Size">
              <input
                type="number"
                min={6}
                max={36}
                value={entry.font_size ?? 11}
                onChange={(e) => {
                  const updated = legend.entries.map((en, i) => i === idx ? { ...en, font_size: Number(e.target.value) } : en);
                  patchLegend({ entries: updated });
                }}
                style={{ width: '100%' }}
              />
            </Field>
            <Field label="Font Color">
              <input
                type="color"
                value={entry.font_color ?? '#333333'}
                onChange={(e) => {
                  const updated = legend.entries.map((en, i) => i === idx ? { ...en, font_color: e.target.value } : en);
                  patchLegend({ entries: updated });
                }}
              />
            </Field>
            <Field label="Font Family">
              <select
                value={entry.font_family ?? 'Arial'}
                onChange={(e) => {
                  const updated = legend.entries.map((en, i) => i === idx ? { ...en, font_family: e.target.value } : en);
                  patchLegend({ entries: updated });
                }}
                style={{ width: '100%' }}
              >
                <option value="Arial">Arial</option>
                <option value="Helvetica">Helvetica</option>
                <option value="Times New Roman">Times New Roman</option>
                <option value="Georgia">Georgia</option>
                <option value="Courier New">Courier New</option>
              </select>
            </Field>
          </div>
        ))}
      </Section>

      {/* ---- Gridlines ---- */}
      <Section title="Gridlines">
        <Field label="Horizontal">
          <input
            type="checkbox"
            checked={gridlines.horizontal_visible}
            onChange={(e) => patchGridlines({ horizontal_visible: e.target.checked })}
          />
        </Field>
        <Field label="Vertical">
          <input
            type="checkbox"
            checked={gridlines.vertical_visible}
            onChange={(e) => patchGridlines({ vertical_visible: e.target.checked })}
          />
        </Field>
        <Field label="Style">
          <select
            value={gridlines.style}
            onChange={(e) => patchGridlines({ style: e.target.value })}
            style={{ width: '100%' }}
          >
            <option value="solid">Solid</option>
            <option value="dashed">Dashed</option>
            <option value="dotted">Dotted</option>
          </select>
        </Field>
        <Field label="Color">
          <input
            type="color"
            value={gridlines.color}
            onChange={(e) => patchGridlines({ color: e.target.value })}
          />
        </Field>
      </Section>

      {/* ---- Annotations ---- */}
      <Section title="Annotations">
        {annotations.map((ann, idx) => (
          <div key={ann.id} style={{ marginBottom: 8, padding: 6, background: '#f5f5f5', borderRadius: 4 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <span style={{ fontWeight: 600, fontSize: 11 }}>
                {ann.type === 'text' ? `Text: ${ann.text ?? ''}` :
                 ann.type === 'horizontal_line' ? `H-Line: ${ann.line_value ?? ''}` :
                 ann.type === 'vertical_line' ? `V-Line: ${ann.text ?? ann.line_value ?? ''}` :
                 `V-Band: ${ann.band_start ?? ''} - ${ann.band_end ?? ''}`}
              </span>
              <button
                onClick={() => {
                  const updated = annotations.filter((_, i) => i !== idx);
                  patch({ annotations: updated });
                }}
                style={{ background: 'none', border: 'none', color: '#c00', cursor: 'pointer', fontSize: 13, padding: '0 2px' }}
                title="Delete annotation"
              >
                ✕
              </button>
            </div>
            {ann.type === 'text' && (
              <>
                <Field label="Text">
                  <input
                    type="text"
                    value={ann.text ?? ''}
                    onChange={(e) => patchAnnotation(idx, { text: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </Field>
                <Field label="Font Size">
                  <input
                    type="number"
                    min={6}
                    max={36}
                    value={ann.font_size}
                    onChange={(e) => patchAnnotation(idx, { font_size: Number(e.target.value) })}
                    style={{ width: '100%' }}
                  />
                </Field>
                <Field label="Font Color">
                  <input
                    type="color"
                    value={ann.font_color}
                    onChange={(e) => patchAnnotation(idx, { font_color: e.target.value })}
                  />
                </Field>
              </>
            )}
            {ann.type === 'vertical_band' && (
              <>
                <Field label="Band Start">
                  <input
                    type="text"
                    value={ann.band_start ?? ''}
                    onChange={(e) => patchAnnotation(idx, { band_start: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </Field>
                <Field label="Band End">
                  <input
                    type="text"
                    value={ann.band_end ?? ''}
                    onChange={(e) => patchAnnotation(idx, { band_end: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </Field>
                <Field label="Band Color">
                  <input
                    type="color"
                    value={ann.band_color ?? '#cccccc'}
                    onChange={(e) => patchAnnotation(idx, { band_color: e.target.value })}
                  />
                </Field>
                <Field label="Label">
                  <input
                    type="text"
                    value={ann.text ?? ''}
                    onChange={(e) => patchAnnotation(idx, { text: e.target.value })}
                    placeholder="Optional label"
                    style={{ width: '100%' }}
                  />
                </Field>
                <Field label="Label Font Size">
                  <input
                    type="number"
                    min={6}
                    max={36}
                    value={ann.font_size}
                    onChange={(e) => patchAnnotation(idx, { font_size: Number(e.target.value) })}
                    style={{ width: '100%' }}
                  />
                </Field>
                <Field label="Label Color">
                  <input
                    type="color"
                    value={ann.font_color}
                    onChange={(e) => patchAnnotation(idx, { font_color: e.target.value })}
                  />
                </Field>
              </>
            )}
            {ann.type === 'horizontal_line' && (
              <>
                <Field label="Y Value">
                  <input
                    type="number"
                    step={0.1}
                    value={ann.line_value ?? 0}
                    onChange={(e) => patchAnnotation(idx, { line_value: Number(e.target.value) })}
                    style={{ width: '100%' }}
                  />
                </Field>
                <Field label="Label">
                  <input
                    type="text"
                    value={ann.text ?? ''}
                    onChange={(e) => patchAnnotation(idx, { text: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </Field>
                <Field label="Label Font Size">
                  <input
                    type="number"
                    min={6}
                    max={36}
                    value={ann.font_size}
                    onChange={(e) => patchAnnotation(idx, { font_size: Number(e.target.value) })}
                    style={{ width: '100%' }}
                  />
                </Field>
                <Field label="Label Color">
                  <input
                    type="color"
                    value={ann.font_color}
                    onChange={(e) => patchAnnotation(idx, { font_color: e.target.value })}
                  />
                </Field>
                <Field label="Line Color">
                  <input
                    type="color"
                    value={ann.line_color ?? '#cc0000'}
                    onChange={(e) => patchAnnotation(idx, { line_color: e.target.value })}
                  />
                </Field>
                <Field label="Line Style">
                  <select
                    value={ann.line_style ?? 'dotted'}
                    onChange={(e) => patchAnnotation(idx, { line_style: e.target.value })}
                    style={{ width: '100%' }}
                  >
                    <option value="dotted">Dotted</option>
                    <option value="dashed">Dashed</option>
                    <option value="solid">Solid</option>
                  </select>
                </Field>
                <Field label="Line Width">
                  <input
                    type="number"
                    min={0.5}
                    max={5}
                    step={0.5}
                    value={ann.line_width ?? 1.5}
                    onChange={(e) => patchAnnotation(idx, { line_width: Number(e.target.value) })}
                    style={{ width: '100%' }}
                  />
                </Field>
              </>
            )}
            {ann.type === 'vertical_line' && (
              <>
                <Field label="Date/Year">
                  <input
                    type="text"
                    value={ann.line_value ?? ''}
                    onChange={(e) => patchAnnotation(idx, { line_value: isNaN(Number(e.target.value)) ? e.target.value : Number(e.target.value) as unknown as number })}
                    placeholder="2008 or 2008-03"
                    style={{ width: '100%' }}
                  />
                </Field>
                <Field label="Label">
                  <input
                    type="text"
                    value={ann.text ?? ''}
                    onChange={(e) => patchAnnotation(idx, { text: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </Field>
                <Field label="Label Font Size">
                  <input
                    type="number"
                    min={6}
                    max={36}
                    value={ann.font_size}
                    onChange={(e) => patchAnnotation(idx, { font_size: Number(e.target.value) })}
                    style={{ width: '100%' }}
                  />
                </Field>
                <Field label="Label Color">
                  <input
                    type="color"
                    value={ann.font_color}
                    onChange={(e) => patchAnnotation(idx, { font_color: e.target.value })}
                  />
                </Field>
                <Field label="Line Color">
                  <input
                    type="color"
                    value={ann.line_color ?? '#FF0000'}
                    onChange={(e) => patchAnnotation(idx, { line_color: e.target.value })}
                  />
                </Field>
                <Field label="Line Style">
                  <select
                    value={ann.line_style ?? 'solid'}
                    onChange={(e) => patchAnnotation(idx, { line_style: e.target.value })}
                    style={{ width: '100%' }}
                  >
                    <option value="solid">Solid</option>
                    <option value="dashed">Dashed</option>
                    <option value="dotted">Dotted</option>
                  </select>
                </Field>
              </>
            )}
            <Field label="X">
              <input
                type="number"
                value={ann.position.x}
                onChange={(e) =>
                  patchAnnotation(idx, { position: { ...ann.position, x: Number(e.target.value) } })
                }
                style={{ width: '100%' }}
              />
            </Field>
            <Field label="Y">
              <input
                type="number"
                value={ann.position.y}
                onChange={(e) =>
                  patchAnnotation(idx, { position: { ...ann.position, y: Number(e.target.value) } })
                }
                style={{ width: '100%' }}
              />
            </Field>
          </div>
        ))}
        {annotations.length === 0 && <p style={{ color: '#999' }}>No annotations.</p>}
        {annotations.length > 0 && (
          <button
            onClick={() => patch({ annotations: [] })}
            style={{
              width: '100%',
              fontSize: 11,
              padding: '4px 0',
              marginBottom: 6,
              color: '#c00',
              background: '#fff0f0',
              border: '1px solid #fcc',
              borderRadius: 3,
              cursor: 'pointer',
            }}
          >
            🗑 Delete All Annotations
          </button>
        )}
        <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
          <button
            style={{ flex: 1, fontSize: 11, padding: '3px 0' }}
            onClick={() => {
              const newAnn = {
                id: `ann_${Date.now()}`,
                type: 'horizontal_line' as const,
                text: '',
                position: { x: 0, y: 0 },
                font_size: 10,
                font_color: '#cc0000',
                band_start: null,
                band_end: null,
                band_color: null,
                line_value: 2.0,
                line_color: '#cc0000',
                line_style: 'dotted',
                line_width: 1.5,
              };
              patch({ annotations: [...annotations, newAnn] });
            }}
          >
            + H-Line
          </button>
          <button
            style={{ flex: 1, fontSize: 11, padding: '3px 0' }}
            onClick={() => {
              const newAnn = {
                id: `ann_${Date.now()}`,
                type: 'text' as const,
                text: 'Note',
                position: { x: 200, y: 200 },
                font_size: 10,
                font_color: '#333333',
                band_start: null,
                band_end: null,
                band_color: null,
                line_value: null,
                line_color: '#cc0000',
                line_style: 'dotted',
                line_width: 1.5,
              };
              patch({ annotations: [...annotations, newAnn] });
            }}
          >
            + Text
          </button>
          <button
            style={{ flex: 1, fontSize: 11, padding: '3px 0' }}
            onClick={() => {
              const newAnn = {
                id: `ann_${Date.now()}`,
                type: 'vertical_band' as const,
                text: null,
                position: { x: 200, y: 0 },
                font_size: 10,
                font_color: '#333333',
                band_start: null,
                band_end: null,
                band_color: '#cccccc',
                line_value: null,
                line_color: '#cc0000',
                line_style: 'dotted',
                line_width: 1.5,
              };
              patch({ annotations: [...annotations, newAnn] });
            }}
          >
            + V-Band
          </button>
          <button
            style={{ flex: 1, fontSize: 11, padding: '3px 0' }}
            onClick={() => {
              const newAnn = {
                id: `ann_${Date.now()}`,
                type: 'vertical_line' as const,
                text: 'Event',
                position: { x: 200, y: 0 },
                font_size: 10,
                font_color: '#FF0000',
                band_start: null,
                band_end: null,
                band_color: null,
                line_value: 2020,
                line_color: '#FF0000',
                line_style: 'solid',
                line_width: 1.5,
              };
              patch({ annotations: [...annotations, newAnn] });
            }}
          >
            + V-Line
          </button>
        </div>
      </Section>

      {/* ---- Data Table ---- */}
      <Section title="Data Table">
        <Field label="Visible">
          <input
            type="checkbox"
            checked={data_table?.visible ?? false}
            onChange={(e) => patchDataTable({ visible: e.target.checked })}
          />
        </Field>
        {(data_table?.visible ?? false) && (
          <>
            <Field label="Max Rows">
              <input
                type="number"
                min={1}
                max={100}
                value={data_table?.max_rows ?? 5}
                onChange={(e) => patchDataTable({ max_rows: Number(e.target.value) })}
                style={{ width: '100%' }}
              />
            </Field>
            <Field label="Font Size">
              <input
                type="number"
                min={6}
                max={24}
                value={data_table?.font_size ?? 10}
                onChange={(e) => patchDataTable({ font_size: Number(e.target.value) })}
                style={{ width: '100%' }}
              />
            </Field>
            <div style={{ marginBottom: 6, fontSize: 12 }}>
              <label style={{ fontWeight: 600 }}>Columns</label>
              <div style={{ marginTop: 4 }}>
                {(chartState.dataset_columns ?? []).map((col) => {
                  const isChecked = (data_table?.columns ?? []).includes(col);
                  return (
                    <label key={col} style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={(e) => {
                          const current = data_table?.columns ?? [];
                          const updated = e.target.checked
                            ? [...current, col]
                            : current.filter((c) => c !== col);
                          patchDataTable({ columns: updated });
                        }}
                      />
                      {col}
                    </label>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </Section>
    </div>
  );
};

export default ControlsPanel;
