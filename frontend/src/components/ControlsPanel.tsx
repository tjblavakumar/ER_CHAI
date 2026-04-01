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
      setChartState({ ...chartState, ...partial });
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
    patch({ series: updated });
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
            <option value="mixed">Mixed</option>
          </select>
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
      <Section title="Title / Fonts">
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
            <div style={{ fontWeight: 600, marginBottom: 4, fontSize: 11 }}>
              {ann.type === 'text' ? `Text: ${ann.text ?? ''}` : `Band: ${ann.id}`}
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
          </>
        )}
      </Section>
    </div>
  );
};

export default ControlsPanel;
