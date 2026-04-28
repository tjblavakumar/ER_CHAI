import React, { useState, useMemo } from 'react';
import { Stage, Layer } from 'react-konva';
import type { ChartState } from '../types';
import DataSeriesElement from './chart/DataSeriesElement';
import AxisElement from './chart/AxisElement';
import GridlineElement from './chart/GridlineElement';
import TitleElement from './chart/TitleElement';

// Mini canvas dimensions (scaled down)
const PREVIEW_WIDTH = 480;
const PREVIEW_HEIGHT = 300;
const MARGIN = { top: 35, right: 20, bottom: 40, left: 50 };
const CHART_AREA = {
  x: MARGIN.left,
  y: MARGIN.top,
  width: PREVIEW_WIDTH - MARGIN.left - MARGIN.right,
  height: PREVIEW_HEIGHT - MARGIN.top - MARGIN.bottom,
};

interface ChartVariant {
  label: string;
  description: string;
  chartState: ChartState;
}

interface ChartPreviewOverlayProps {
  variants: ChartVariant[];
  datasetRows: Record<string, unknown>[] | null;
  onSelect: (chartState: ChartState) => void;
  onCancel: () => void;
}

/**
 * Mini chart preview rendered in a small Konva stage.
 */
const MiniChart: React.FC<{
  chartState: ChartState;
  datasetRows: Record<string, unknown>[] | null;
}> = ({ chartState, datasetRows }) => {
  const yMin = chartState.axes.y_min ?? 0;
  const yMax = chartState.axes.y_max ?? 100;

  // Extract xLabels for the mini chart
  const xLabels = useMemo(() => {
    if (!datasetRows || datasetRows.length === 0) return undefined;
    const firstRow = datasetRows[0];
    const dateCol = Object.keys(firstRow).find((key) => {
      const val = firstRow[key];
      return typeof val === 'string' && isNaN(Number(val));
    });
    if (!dateCol) return undefined;
    return datasetRows.map((row) => String(row[dateCol] ?? ''));
  }, [datasetRows]);

  return (
    <Stage
      width={PREVIEW_WIDTH}
      height={PREVIEW_HEIGHT}
      style={{ background: '#fff', borderRadius: 6 }}
    >
      <Layer>
        <GridlineElement
          config={chartState.gridlines}
          chartArea={CHART_AREA}
        />
        <DataSeriesElement
          series={chartState.series}
          chartArea={CHART_AREA}
          yMin={yMin}
          yMax={yMax}
          datasetRows={datasetRows}
          barGrouping={chartState.bar_grouping}
          categoryColumn={chartState.category_column}
          groupColumn={chartState.group_column}
          barLabelFontSize={8}
        />
        <AxisElement
          config={{ ...chartState.axes, tick_font_size: 8, label_font_size: 9 }}
          chartArea={CHART_AREA}
          xLabels={chartState.bar_grouping === 'by_category' ? undefined : xLabels}
          hideXLabels={chartState.bar_grouping === 'by_category'}
          draggable={false}
        />
        <TitleElement
          config={{
            ...chartState.title,
            font_size: 12,
            position: { x: PREVIEW_WIDTH / 2 - 60, y: 6 },
          }}
          elementId="preview_title"
          draggable={false}
        />
      </Layer>
    </Stage>
  );
};

/**
 * Overlay modal showing multiple chart variants for the user to choose from.
 * Displays a carousel with < > navigation and a select button per variant.
 */
const ChartPreviewOverlay: React.FC<ChartPreviewOverlayProps> = ({
  variants,
  datasetRows,
  onSelect,
  onCancel,
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);

  if (variants.length === 0) return null;

  const current = variants[currentIndex];

  const goLeft = () => setCurrentIndex((i) => (i - 1 + variants.length) % variants.length);
  const goRight = () => setCurrentIndex((i) => (i + 1) % variants.length);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.55)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 3000,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div
        style={{
          background: '#fff',
          borderRadius: 12,
          padding: '24px 32px',
          boxShadow: '0 12px 48px rgba(0,0,0,0.3)',
          maxWidth: 600,
          width: '90%',
          textAlign: 'center',
        }}
      >
        {/* Header */}
        <h2 style={{ margin: '0 0 4px', fontSize: 18, color: '#333' }}>
          Choose a Chart Style
        </h2>
        <p style={{ margin: '0 0 16px', fontSize: 13, color: '#888' }}>
          AI analyzed your data and generated {variants.length} options. Pick one to start customizing.
        </p>

        {/* Carousel */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, justifyContent: 'center' }}>
          {/* Left arrow */}
          <button
            onClick={goLeft}
            style={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              border: '1px solid #ddd',
              background: '#f5f5f5',
              fontSize: 18,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            ‹
          </button>

          {/* Preview card */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div
              style={{
                border: '2px solid #1a73e8',
                borderRadius: 8,
                overflow: 'hidden',
                background: '#fafafa',
              }}
            >
              <MiniChart chartState={current.chartState} datasetRows={datasetRows} />
            </div>
            <div style={{ marginTop: 10 }}>
              <div style={{ fontWeight: 700, fontSize: 15, color: '#1a73e8' }}>
                {current.label}
              </div>
              <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>
                {current.description}
              </div>
            </div>
          </div>

          {/* Right arrow */}
          <button
            onClick={goRight}
            style={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              border: '1px solid #ddd',
              background: '#f5f5f5',
              fontSize: 18,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            ›
          </button>
        </div>

        {/* Dots indicator */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 6, marginTop: 12 }}>
          {variants.map((_, i) => (
            <div
              key={i}
              onClick={() => setCurrentIndex(i)}
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: i === currentIndex ? '#1a73e8' : '#ddd',
                cursor: 'pointer',
              }}
            />
          ))}
        </div>

        {/* Action buttons */}
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 18 }}>
          <button
            onClick={onCancel}
            style={{
              padding: '8px 24px',
              fontSize: 13,
              border: '1px solid #ccc',
              borderRadius: 6,
              background: '#fff',
              cursor: 'pointer',
              color: '#666',
            }}
          >
            Cancel
          </button>
          <button
            onClick={() => onSelect(current.chartState)}
            style={{
              padding: '8px 24px',
              fontSize: 13,
              border: 'none',
              borderRadius: 6,
              background: '#1a73e8',
              color: '#fff',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            Use This Style
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChartPreviewOverlay;
export type { ChartVariant };
