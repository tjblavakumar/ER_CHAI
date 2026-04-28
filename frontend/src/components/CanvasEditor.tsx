import React, { useCallback, useState, useRef } from 'react';
import { Stage, Layer } from 'react-konva';
import { useAppStore } from '../store/appStore';
import TitleElement from './chart/TitleElement';
import AxisElement from './chart/AxisElement';
import DataSeriesElement from './chart/DataSeriesElement';
import LegendElement from './chart/LegendElement';
import GridlineElement from './chart/GridlineElement';
import AnnotationElement from './chart/AnnotationElement';
import DataTableElement from './chart/DataTableElement';
import ContextMenu from './ContextMenu';
import type { ChartState, Position } from '../types';

// Canvas dimensions
const STAGE_WIDTH = 1200;
const STAGE_HEIGHT = 700;

// Chart area with margins
const MARGIN = { top: 50, right: 30, bottom: 60, left: 70 };
const CHART_AREA = {
  x: MARGIN.left,
  y: MARGIN.top,
  width: STAGE_WIDTH - MARGIN.left - MARGIN.right,
  height: STAGE_HEIGHT - MARGIN.top - MARGIN.bottom - 80, // leave room for data table
};

const ZOOM_MIN = 0.3;
const ZOOM_MAX = 3.0;
const ZOOM_STEP = 0.15;

/**
 * Apply display transforms to dataset rows (non-destructive).
 * Returns a new array of rows with transformed values.
 */
function applyDisplayTransforms(
  rows: Record<string, unknown>[],
  transforms: import('../types').DisplayTransform[],
): Record<string, unknown>[] {
  if (!transforms || transforms.length === 0) return rows;
  return rows.map((row) => {
    const newRow = { ...row };
    for (const t of transforms) {
      const val = Number(newRow[t.column]);
      if (isNaN(val)) continue;
      let result = val;
      switch (t.operation) {
        case 'multiply':
          result = val * (t.factor ?? 1);
          break;
        case 'divide':
          result = (t.factor ?? 1) !== 0 ? val / (t.factor ?? 1) : val;
          break;
        case 'add':
          result = val + (t.factor ?? 0);
          break;
        case 'subtract':
          result = val - (t.factor ?? 0);
          break;
        case 'normalize':
          result = (t.base_value ?? 1) !== 0 ? (val / (t.base_value ?? 1)) * 100 : val;
          break;
        default:
          break;
      }
      newRow[t.column] = result;
    }
    return newRow;
  });
}

const CanvasEditor: React.FC = () => {
  const chartState = useAppStore((s) => s.chartState);
  const datasetRows = useAppStore((s) => s.datasetRows);
  const setChartState = useAppStore((s) => s.setChartState);
  const setContextMenuTarget = useAppStore((s) => s.setContextMenuTarget);

  const [zoom, setZoom] = useState(1);
  const stageRef = useRef<any>(null);

  const handleZoomIn = useCallback(() => {
    setZoom((z) => Math.min(ZOOM_MAX, z + ZOOM_STEP));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom((z) => Math.max(ZOOM_MIN, z - ZOOM_STEP));
  }, []);

  const handleZoomFit = useCallback(() => {
    setZoom(1);
  }, []);

  const handleWheel = useCallback((e: any) => {
    e.evt.preventDefault();
    const delta = e.evt.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
    setZoom((z) => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, z + delta)));
  }, []);

  /**
   * Persist new position to chart state on drag end (Req 7.3).
   */
  const handleDragEnd = useCallback(
    (elementId: string, x: number, y: number) => {
      if (!chartState) return;
      const updated: ChartState = {
        ...chartState,
        elements_positions: {
          ...chartState.elements_positions,
          [elementId]: { x, y },
        },
      };

      // Also update the canonical position on known elements
      if (elementId === 'title') {
        updated.title = { ...chartState.title, position: { x, y } };
      } else if (elementId === 'legend') {
        updated.legend = { ...chartState.legend, position: { x, y } };
      } else if (elementId.startsWith('legend_entry_')) {
        // Individual legend entry dragged — only update elements_positions (already done above)
      } else if (elementId === 'data_table' && chartState.data_table) {
        updated.data_table = { ...chartState.data_table, position: { x, y } };
      } else if (elementId.startsWith('annotation_')) {
        const annId = elementId.replace('annotation_', '');
        updated.annotations = chartState.annotations.map((a) =>
          a.id === annId ? { ...a, position: { x, y } } : a,
        );
      }

      setChartState(updated);
    },
    [chartState, setChartState],
  );

  /**
   * Show context menu on right-click over text elements (Req 8.1).
   */
  const handleContextMenu = useCallback(
    (elementId: string, x: number, y: number) => {
      setContextMenuTarget({ elementId, x, y });
    },
    [setContextMenuTarget],
  );

  /**
   * Apply font property changes from context menu (Req 8.2).
   */
  const handleApplyChange = useCallback(
    (elementId: string, property: string, value: string | number) => {
      if (!chartState) return;
      const updated = { ...chartState };

      if (elementId === 'title') {
        updated.title = { ...chartState.title, [property]: value };
      } else if (elementId === 'x_label' || elementId === 'y_label') {
        // Axis label font changes — map to axes config
        if (property === 'font_size') {
          updated.axes = { ...chartState.axes, label_font_size: value as number };
        }
      } else if (elementId.startsWith('legend_entry_')) {
        const seriesName = elementId.replace('legend_entry_', '');
        updated.legend = {
          ...chartState.legend,
          entries: chartState.legend.entries.map((entry) =>
            entry.series_name === seriesName
              ? { ...entry, [property]: value }
              : entry,
          ),
        };
      } else if (elementId.startsWith('annotation_')) {
        const annId = elementId.replace('annotation_', '');
        if (property === '_delete') {
          // Remove the annotation
          updated.annotations = chartState.annotations.filter((a) => a.id !== annId);
        } else {
          updated.annotations = chartState.annotations.map((a) =>
            a.id === annId ? { ...a, [property]: value } : a,
          );
        }
      } else if (elementId === 'data_table' && chartState.data_table) {
        if (property === '_hide') {
          updated.data_table = { ...chartState.data_table, visible: false };
        } else if (property === '_delete') {
          updated.data_table = null;
        } else if (property === 'font_size') {
          updated.data_table = { ...chartState.data_table, font_size: value as number };
        }
      }

      setChartState(updated);
      // Don't close context menu for label edits (text input needs to stay open)
      if (property !== 'label') {
        setContextMenuTarget(null);
      }
    },
    [chartState, setChartState, setContextMenuTarget],
  );

  /**
   * Handle data table resize from drag handles.
   */
  const handleDataTableResize = useCallback(
    (colWidth: number, rowHeight: number, seriesColWidth: number) => {
      if (!chartState || !chartState.data_table) return;
      const updated: ChartState = {
        ...chartState,
        data_table: {
          ...chartState.data_table,
          col_width: Math.round(colWidth * 10) / 10,
          row_height: Math.round(rowHeight * 10) / 10,
          series_col_width: Math.round(seriesColWidth * 10) / 10,
        },
      };
      setChartState(updated);
    },
    [chartState, setChartState],
  );

  // Extract date labels from datasetRows (first non-numeric column)
  // Must be before any early return to satisfy Rules of Hooks
  const xLabels = React.useMemo(() => {
    if (!datasetRows || datasetRows.length === 0) return undefined;
    const firstRow = datasetRows[0];
    const dateCol = Object.keys(firstRow).find((key) => {
      const val = firstRow[key];
      return typeof val === 'string' && isNaN(Number(val));
    });
    if (!dateCol) return undefined;
    return datasetRows.map((row) => String(row[dateCol] ?? ''));
  }, [datasetRows]);

  // Build series labels map from legend entries (series_name -> display label)
  const seriesLabels = React.useMemo(() => {
    if (!chartState) return {};
    const map: Record<string, string> = {};
    for (const entry of chartState.legend.entries) {
      map[entry.series_name] = entry.label;
    }
    return map;
  }, [chartState]);

  // Build series colors map from series config (column -> color)
  const seriesColors = React.useMemo(() => {
    if (!chartState) return {};
    const map: Record<string, string> = {};
    for (const s of chartState.series) {
      map[s.column] = s.color;
    }
    return map;
  }, [chartState]);

  // Filter datasetRows by x-axis date range (x_min/x_max) when they are date strings
  const filteredRows = React.useMemo(() => {
    if (!datasetRows || datasetRows.length === 0 || !chartState) return datasetRows;
    const xMin = chartState.axes.x_min;
    const xMax = chartState.axes.x_max;
    if (xMin == null && xMax == null) return datasetRows;
    // Only filter if x_min/x_max are strings (dates)
    if (typeof xMin !== 'string' && typeof xMax !== 'string') return datasetRows;

    // Find the date column
    const firstRow = datasetRows[0];
    const dateCol = Object.keys(firstRow).find((key) => {
      const val = firstRow[key];
      return typeof val === 'string' && isNaN(Number(val));
    });
    if (!dateCol) return datasetRows;

    return datasetRows.filter((row) => {
      const dateVal = String(row[dateCol] ?? '');
      if (xMin != null && dateVal < String(xMin)) return false;
      if (xMax != null && dateVal > String(xMax) + '-99') return false;
      return true;
    });
  }, [datasetRows, chartState]);

  // Apply display transforms to filtered rows (non-destructive)
  const transformedRows = React.useMemo(() => {
    if (!filteredRows || !chartState?.display_transforms?.length) return filteredRows;
    return applyDisplayTransforms(filteredRows, chartState.display_transforms);
  }, [filteredRows, chartState?.display_transforms]);

  // Recompute xLabels from filtered rows
  const filteredXLabels = React.useMemo(() => {
    if (!filteredRows || filteredRows.length === 0) return xLabels;
    const firstRow = filteredRows[0];
    const dateCol = Object.keys(firstRow).find((key) => {
      const val = firstRow[key];
      return typeof val === 'string' && isNaN(Number(val));
    });
    if (!dateCol) return xLabels;
    return filteredRows.map((row) => String(row[dateCol] ?? ''));
  }, [filteredRows, xLabels]);

  if (!chartState) {
    return (
      <div
        style={{
          width: STAGE_WIDTH,
          height: STAGE_HEIGHT,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#f5f5f5',
          border: '1px dashed #ccc',
          borderRadius: 4,
          color: '#999',
          fontSize: 14,
        }}
      >
        Load or create a chart to get started
      </div>
    );
  }

  const yMin = chartState.axes.y_min ?? 0;
  const yMax = chartState.axes.y_max ?? 100;

  // Resolve positions from elements_positions or use defaults
  const resolvePos = (id: string, fallback: Position): Position =>
    chartState.elements_positions[id] ?? fallback;

  const titlePos = resolvePos('title', chartState.title.position);
  const legendPos = resolvePos('legend', chartState.legend.position);
  const dataTablePos = chartState.data_table
    ? resolvePos('data_table', chartState.data_table.position)
    : { x: MARGIN.left, y: STAGE_HEIGHT - 70 };

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      {/* Zoom controls */}
      <div
        style={{
          position: 'absolute',
          top: 8,
          right: 8,
          zIndex: 100,
          display: 'flex',
          gap: 4,
          background: 'rgba(255,255,255,0.9)',
          borderRadius: 6,
          padding: '4px 6px',
          boxShadow: '0 1px 4px rgba(0,0,0,0.15)',
          fontSize: 12,
        }}
      >
        <button
          onClick={handleZoomOut}
          style={{ width: 28, height: 28, cursor: 'pointer', border: '1px solid #ccc', borderRadius: 4, background: '#fff', fontSize: 16, lineHeight: '26px' }}
          title="Zoom out"
        >
          −
        </button>
        <span
          style={{ minWidth: 44, textAlign: 'center', lineHeight: '28px', fontWeight: 600, color: '#555' }}
        >
          {Math.round(zoom * 100)}%
        </span>
        <button
          onClick={handleZoomIn}
          style={{ width: 28, height: 28, cursor: 'pointer', border: '1px solid #ccc', borderRadius: 4, background: '#fff', fontSize: 16, lineHeight: '26px' }}
          title="Zoom in"
        >
          +
        </button>
        <button
          onClick={handleZoomFit}
          style={{ height: 28, cursor: 'pointer', border: '1px solid #ccc', borderRadius: 4, background: '#fff', fontSize: 11, padding: '0 8px' }}
          title="Reset zoom"
        >
          Fit
        </button>
      </div>
      <Stage
        ref={stageRef}
        width={STAGE_WIDTH * zoom}
        height={STAGE_HEIGHT * zoom}
        scaleX={zoom}
        scaleY={zoom}
        style={{ background: '#ffffff', border: '1px solid #ddd' }}
        onWheel={handleWheel}
      >
        <Layer>
          {/* Gridlines (behind data) */}
          <GridlineElement
            config={chartState.gridlines}
            chartArea={CHART_AREA}
            onDragEnd={handleDragEnd}
          />

          {/* Data series */}
          <DataSeriesElement
            series={chartState.series}
            chartArea={CHART_AREA}
            yMin={yMin}
            yMax={yMax}
            datasetRows={transformedRows}
            barGrouping={chartState.bar_grouping}
            categoryColumn={chartState.category_column}
            groupColumn={chartState.group_column}
            barLabelFontSize={chartState.axes.tick_font_size ?? 10}
          />

          {/* Axes */}
          <AxisElement
            config={chartState.axes}
            chartArea={CHART_AREA}
            xLabels={filteredXLabels}
            hideXLabels={chartState.bar_grouping === 'by_category'}
            onDragEnd={handleDragEnd}
            onContextMenu={handleContextMenu}
          />

          {/* Title */}
          <TitleElement
            config={{ ...chartState.title, position: titlePos }}
            elementId="title"
            onDragEnd={handleDragEnd}
            onContextMenu={handleContextMenu}
          />

          {/* Legend */}
          <LegendElement
            config={{ ...chartState.legend, position: legendPos }}
            elementsPositions={chartState.elements_positions}
            onDragEnd={handleDragEnd}
            onContextMenu={handleContextMenu}
          />

          {/* Annotations */}
          {chartState.annotations.map((ann) => {
            const annPos = resolvePos(`annotation_${ann.id}`, ann.position);
            return (
              <AnnotationElement
                key={ann.id}
                config={{ ...ann, position: annPos }}
                chartArea={CHART_AREA}
                yMin={yMin}
                yMax={yMax}
                xLabels={filteredXLabels}
                onDragEnd={handleDragEnd}
                onContextMenu={handleContextMenu}
              />
            );
          })}

          {/* Data Table */}
          {chartState.data_table && (
            <DataTableElement
              config={{ ...chartState.data_table, position: dataTablePos }}
              datasetRows={transformedRows}
              seriesLabels={seriesLabels}
              seriesColors={seriesColors}
              onDragEnd={handleDragEnd}
              onContextMenu={handleContextMenu}
              onResize={handleDataTableResize}
            />
          )}
        </Layer>
      </Stage>

      {/* Context Menu (HTML overlay) */}
      <ContextMenu onApplyChange={handleApplyChange} />
    </div>
  );
};

export default CanvasEditor;
