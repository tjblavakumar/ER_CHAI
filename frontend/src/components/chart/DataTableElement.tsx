import React, { useRef, useState } from 'react';
import { Group, Rect, Text, Line } from 'react-konva';
import type { DataTableConfig } from '../../types';

interface DataTableElementProps {
  config: DataTableConfig;
  datasetRows?: Record<string, unknown>[] | null;
  seriesLabels?: Record<string, string>;
  seriesColors?: Record<string, string>;
  draggable?: boolean;
  onDragEnd?: (id: string, x: number, y: number) => void;
  onContextMenu?: (id: string, x: number, y: number) => void;
  onResize?: (colWidth: number, rowHeight: number, seriesColWidth: number) => void;
}

const DEFAULT_SERIES_COL_WIDTH = 120;
const DEFAULT_COL_WIDTH = 70;
const DEFAULT_ROW_HEIGHT = 22;
const HEADER_HEIGHT = 24;
const HANDLE_SIZE = 8;

const formatCellValue = (value: unknown): string => {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') return value.toFixed(2);
  return String(value);
};

/** Clean up column/row labels — remove \r\n, special chars, truncate */
const cleanHeaderLabel = (s: string): string => {
  return s.replace(/[\r\n]+/g, ' ').replace(/\s+/g, ' ').trim();
};

const formatDateHeader = (value: unknown): string => {
  if (value === null || value === undefined) return '';
  const s = String(value);
  const d = new Date(s);
  if (!isNaN(d.getTime())) {
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${months[d.getMonth()]} ${String(d.getFullYear()).slice(2)}`;
  }
  return s.length > 8 ? s.slice(0, 8) : s;
};

/**
 * Transposed data table for time series with drag-to-resize handles:
 * - Right edge: resize column widths proportionally
 * - Bottom edge: resize row heights
 * - Bottom-right corner: resize both
 */
const DataTableElement: React.FC<DataTableElementProps> = ({
  config,
  datasetRows,
  seriesLabels,
  seriesColors,
  draggable = true,
  onDragEnd,
  onContextMenu,
  onResize,
}) => {
  if (!config.visible) return null;

  // Check for custom table mode
  const customHeaders = config.custom_headers ?? [];
  const customRows = config.custom_rows ?? [];
  const isCustomTable = customHeaders.length > 0 && customRows.length > 0;

  // If not custom and no columns, nothing to render
  if (!isCustomTable && config.columns.length === 0) return null;

  const [hovered, setHovered] = useState(false);

  const seriesColWidth = config.series_col_width ?? DEFAULT_SERIES_COL_WIDTH;
  const colWidth = config.col_width ?? DEFAULT_COL_WIDTH;
  const rowHeight = config.row_height ?? DEFAULT_ROW_HEIGHT;

  // Refs for resize tracking
  const resizeStart = useRef<{ x: number; y: number; colW: number; rowH: number; seriesW: number } | null>(null);

  const handleResizeRight = (e: any) => {
    e.cancelBubble = true;
    const stage = e.target.getStage();
    if (!stage) return;
    const startPointer = stage.getPointerPosition();
    if (!startPointer) return;
    resizeStart.current = { x: startPointer.x, y: startPointer.y, colW: colWidth, rowH: rowHeight, seriesW: seriesColWidth };
    const onMove = () => {
      if (!resizeStart.current) return;
      const pointer = stage.getPointerPosition();
      if (!pointer) return;
      const dx = pointer.x - resizeStart.current.x;
      const perColDelta = dx / Math.max((customHeaders.length || 3), 1);
      const newColW = Math.max(40, resizeStart.current.colW + perColDelta);
      const newSeriesW = Math.max(60, resizeStart.current.seriesW + perColDelta);
      onResize?.(newColW, resizeStart.current.rowH, newSeriesW);
    };
    const onUp = () => { resizeStart.current = null; stage.off('mousemove touchmove', onMove); stage.off('mouseup touchend', onUp); stage.container().style.cursor = 'default'; };
    stage.on('mousemove touchmove', onMove); stage.on('mouseup touchend', onUp); stage.container().style.cursor = 'col-resize';
  };

  const handleResizeBottom = (e: any) => {
    e.cancelBubble = true;
    const stage = e.target.getStage();
    if (!stage) return;
    const startPointer = stage.getPointerPosition();
    if (!startPointer) return;
    resizeStart.current = { x: startPointer.x, y: startPointer.y, colW: colWidth, rowH: rowHeight, seriesW: seriesColWidth };
    const rowCount = isCustomTable ? customRows.length : (config.columns.length || 1);
    const onMove = () => {
      if (!resizeStart.current) return;
      const pointer = stage.getPointerPosition();
      if (!pointer) return;
      const dy = pointer.y - resizeStart.current.y;
      const newRowH = Math.max(14, resizeStart.current.rowH + dy / Math.max(rowCount, 1));
      onResize?.(resizeStart.current.colW, newRowH, resizeStart.current.seriesW);
    };
    const onUp = () => { resizeStart.current = null; stage.off('mousemove touchmove', onMove); stage.off('mouseup touchend', onUp); stage.container().style.cursor = 'default'; };
    stage.on('mousemove touchmove', onMove); stage.on('mouseup touchend', onUp); stage.container().style.cursor = 'row-resize';
  };

  const handleResizeCorner = (e: any) => {
    e.cancelBubble = true;
    const stage = e.target.getStage();
    if (!stage) return;
    const startPointer = stage.getPointerPosition();
    if (!startPointer) return;
    resizeStart.current = { x: startPointer.x, y: startPointer.y, colW: colWidth, rowH: rowHeight, seriesW: seriesColWidth };
    const rowCount = isCustomTable ? customRows.length : (config.columns.length || 1);
    const onMove = () => {
      if (!resizeStart.current) return;
      const pointer = stage.getPointerPosition();
      if (!pointer) return;
      const dx = pointer.x - resizeStart.current.x;
      const dy = pointer.y - resizeStart.current.y;
      const perColDelta = dx / Math.max((customHeaders.length || 3), 1);
      const newColW = Math.max(40, resizeStart.current.colW + perColDelta);
      const newSeriesW = Math.max(60, resizeStart.current.seriesW + perColDelta);
      const newRowH = Math.max(14, resizeStart.current.rowH + dy / Math.max(rowCount, 1));
      onResize?.(newColW, newRowH, newSeriesW);
    };
    const onUp = () => { resizeStart.current = null; stage.off('mousemove touchmove', onMove); stage.off('mouseup touchend', onUp); stage.container().style.cursor = 'default'; };
    stage.on('mousemove touchmove', onMove); stage.on('mouseup touchend', onUp); stage.container().style.cursor = 'nwse-resize';
  };

  const maxDateCols = config.max_rows ?? 5;
  const hasData = datasetRows && datasetRows.length > 0;

  // Detect date column
  let dateColumn: string | null = null;
  if (hasData) {
    const firstRow = datasetRows[0];
    dateColumn = Object.keys(firstRow).find((key) => {
      const val = firstRow[key];
      return typeof val === 'string' && isNaN(Number(val));
    }) ?? null;
  }

  // Sample the last N date indices
  const totalRows = hasData ? datasetRows.length : 0;
  const sampledIndices: number[] = [];
  if (totalRows > 0 && maxDateCols > 0) {
    const count = Math.min(maxDateCols, totalRows);
    const startIdx = totalRows - count;
    for (let i = 0; i < count; i++) {
      sampledIndices.push(startIdx + i);
    }
  }

  const dateHeaders = sampledIndices.map((idx) =>
    dateColumn && hasData ? formatDateHeader(datasetRows[idx][dateColumn]) : `Col ${idx}`,
  ).map(cleanHeaderLabel);

  const seriesCols = config.columns;
  const computedCols = config.computed_columns ?? [];
  const computedValues = config.computed_values ?? {};
  const numDateCols = dateHeaders.length;
  const numRows = seriesCols.length;

  // --- Custom table rendering ---
  if (isCustomTable) {
    const cColWidth = config.col_width ?? 100;
    const cRowHeight = config.row_height ?? DEFAULT_ROW_HEIGHT;
    const cTableWidth = customHeaders.length * cColWidth;
    const cTableHeight = HEADER_HEIGHT + customRows.length * cRowHeight;

    return (
      <Group
        x={config.position.x}
        y={config.position.y}
        draggable={draggable}
        onDragEnd={(e) => onDragEnd?.('data_table', e.target.x(), e.target.y())}
        onContextMenu={(e) => {
          e.evt.preventDefault();
          const stage = e.target.getStage();
          if (stage) {
            const pointer = stage.getPointerPosition();
            if (pointer) onContextMenu?.('data_table', pointer.x, pointer.y);
          }
        }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        <Rect width={cTableWidth} height={cTableHeight} fill="#fff" stroke="#999" strokeWidth={1} />
        <Rect width={cTableWidth} height={HEADER_HEIGHT} fill="#e8e8e8" />
        {/* Headers */}
        {customHeaders.map((h, i) => (
          <Text
            key={`ch-${i}`}
            x={i * cColWidth + 4}
            y={5}
            text={cleanHeaderLabel(h)}
            fontSize={config.font_size}
            fontFamily="Arial"
            fontStyle="bold"
            fill="#333"
            width={cColWidth - 8}
            ellipsis
          />
        ))}
        <Line points={[0, HEADER_HEIGHT, cTableWidth, HEADER_HEIGHT]} stroke="#999" strokeWidth={1} />
        {/* Rows */}
        {customRows.map((row, rowIdx) => (
          <React.Fragment key={`cr-${rowIdx}`}>
            {customHeaders.map((h, colIdx) => (
              <Text
                key={`cc-${rowIdx}-${colIdx}`}
                x={colIdx * cColWidth + 4}
                y={HEADER_HEIGHT + rowIdx * cRowHeight + 4}
                text={cleanHeaderLabel(row[h] ?? '—')}
                fontSize={config.font_size}
                fontFamily="Arial"
                fill={colIdx === 0 ? (seriesColors?.[row[h]] ?? '#333') : '#333'}
                width={cColWidth - 8}
                ellipsis
              />
            ))}
            {rowIdx < customRows.length - 1 && (
              <Line
                points={[0, HEADER_HEIGHT + (rowIdx + 1) * cRowHeight, cTableWidth, HEADER_HEIGHT + (rowIdx + 1) * cRowHeight]}
                stroke="#ddd"
                strokeWidth={0.5}
              />
            )}
          </React.Fragment>
        ))}
        {/* Resize handles on hover */}
        {hovered && (
          <>
            <Rect
              x={cTableWidth - HANDLE_SIZE / 2}
              y={cTableHeight / 2 - 16}
              width={HANDLE_SIZE}
              height={32}
              fill="#1a73e8"
              opacity={0.5}
              cornerRadius={2}
              onMouseEnter={(e) => { e.target.opacity(0.9); e.target.getStage()!.container().style.cursor = 'col-resize'; e.target.getLayer()?.batchDraw(); }}
              onMouseLeave={(e) => { e.target.opacity(0.5); e.target.getStage()!.container().style.cursor = 'default'; e.target.getLayer()?.batchDraw(); }}
              onMouseDown={handleResizeRight}
            />
            <Rect
              x={cTableWidth / 2 - 16}
              y={cTableHeight - HANDLE_SIZE / 2}
              width={32}
              height={HANDLE_SIZE}
              fill="#1a73e8"
              opacity={0.5}
              cornerRadius={2}
              onMouseEnter={(e) => { e.target.opacity(0.9); e.target.getStage()!.container().style.cursor = 'row-resize'; e.target.getLayer()?.batchDraw(); }}
              onMouseLeave={(e) => { e.target.opacity(0.5); e.target.getStage()!.container().style.cursor = 'default'; e.target.getLayer()?.batchDraw(); }}
              onMouseDown={handleResizeBottom}
            />
            <Rect
              x={cTableWidth - HANDLE_SIZE}
              y={cTableHeight - HANDLE_SIZE}
              width={HANDLE_SIZE + 2}
              height={HANDLE_SIZE + 2}
              fill="#1a73e8"
              opacity={0.7}
              cornerRadius={2}
              onMouseEnter={(e) => { e.target.opacity(1); e.target.getStage()!.container().style.cursor = 'nwse-resize'; e.target.getLayer()?.batchDraw(); }}
              onMouseLeave={(e) => { e.target.opacity(0.7); e.target.getStage()!.container().style.cursor = 'default'; e.target.getLayer()?.batchDraw(); }}
              onMouseDown={handleResizeCorner}
            />
          </>
        )}
      </Group>
    );
  }

  // --- Standard time-series table rendering ---
  const tableWidth = seriesColWidth + (numDateCols + computedCols.length) * colWidth;
  const tableHeight = HEADER_HEIGHT + numRows * rowHeight;

  return (
    <Group
      x={config.position.x}
      y={config.position.y}
      draggable={draggable}
      onDragEnd={(e) => {
        onDragEnd?.('data_table', e.target.x(), e.target.y());
      }}
      onContextMenu={(e) => {
        e.evt.preventDefault();
        const stage = e.target.getStage();
        if (stage) {
          const pointer = stage.getPointerPosition();
          if (pointer) {
            onContextMenu?.('data_table', pointer.x, pointer.y);
          }
        }
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Background */}
      <Rect width={tableWidth} height={tableHeight} fill="#fff" stroke="#999" strokeWidth={1} />

      {/* Header row background */}
      <Rect width={tableWidth} height={HEADER_HEIGHT} fill="#e8e8e8" />

      {/* First header cell: "Series" */}
      <Text
        x={4}
        y={5}
        text="Series"
        fontSize={config.font_size}
        fontFamily="Arial"
        fontStyle="bold"
        fill="#333"
        width={seriesColWidth - 8}
        ellipsis
      />

      {/* Date column headers */}
      {dateHeaders.map((header, i) => (
        <Text
          key={`dh-${i}`}
          x={seriesColWidth + i * colWidth + 4}
          y={5}
          text={header}
          fontSize={config.font_size}
          fontFamily="Arial"
          fontStyle="bold"
          fill="#333"
          width={colWidth - 8}
          ellipsis
        />
      ))}

      {/* Computed column headers */}
      {computedCols.map((cc, i) => (
        <Text
          key={`cch-${i}`}
          x={seriesColWidth + (numDateCols + i) * colWidth + 4}
          y={5}
          text={cc.label}
          fontSize={config.font_size}
          fontFamily="Arial"
          fontStyle="bold"
          fill="#333"
          width={colWidth - 8}
          ellipsis
        />
      ))}

      {/* Header separator */}
      <Line points={[0, HEADER_HEIGHT, tableWidth, HEADER_HEIGHT]} stroke="#999" strokeWidth={1} />

      {/* Data rows: one per series */}
      {seriesCols.map((col, rowIdx) => {
        const label = cleanHeaderLabel(seriesLabels?.[col] ?? col);
        return (
          <React.Fragment key={`row-${col}`}>
            {/* Series name cell */}
            <Text
              x={4}
              y={HEADER_HEIGHT + rowIdx * rowHeight + 4}
              text={label}
              fontSize={config.font_size}
              fontFamily="Arial"
              fontStyle="bold"
              fill={seriesColors?.[col] ?? "#333"}
              width={seriesColWidth - 8}
              ellipsis
            />
            {/* Value cells at sampled dates */}
            {sampledIndices.map((dataIdx, colIdx) => (
              <Text
                key={`cell-${rowIdx}-${colIdx}`}
                x={seriesColWidth + colIdx * colWidth + 4}
                y={HEADER_HEIGHT + rowIdx * rowHeight + 4}
                text={hasData ? formatCellValue(datasetRows[dataIdx][col]) : '—'}
                fontSize={config.font_size}
                fontFamily="Arial"
                fill={seriesColors?.[seriesCols[rowIdx]] ?? "#333"}
                width={colWidth - 8}
                ellipsis
              />
            ))}
            {/* Computed column cells */}
            {computedCols.map((cc, ccIdx) => {
              const key = `${col}:${cc.label}`;
              const val = computedValues[key];
              return (
                <Text
                  key={`cc-${rowIdx}-${ccIdx}`}
                  x={seriesColWidth + (numDateCols + ccIdx) * colWidth + 4}
                  y={HEADER_HEIGHT + rowIdx * rowHeight + 4}
                  text={val != null ? val.toFixed(2) : '—'}
                  fontSize={config.font_size}
                  fontFamily="Arial"
                  fill={seriesColors?.[col] ?? "#333"}
                  width={colWidth - 8}
                  ellipsis
                />
              );
            })}
          </React.Fragment>
        );
      })}

      {/* Row separators */}
      {Array.from({ length: numRows - 1 }, (_, i) => {
        const ry = HEADER_HEIGHT + (i + 1) * rowHeight;
        return (
          <Line key={`row-sep-${i}`} points={[0, ry, tableWidth, ry]} stroke="#ddd" strokeWidth={0.5} />
        );
      })}

      {/* --- Resize handles (visible on hover only) --- */}
      {hovered && (
        <>
          {/* Right edge handle */}
          <Rect
            x={tableWidth - HANDLE_SIZE / 2}
            y={tableHeight / 2 - 16}
            width={HANDLE_SIZE}
            height={32}
            fill="#1a73e8"
            opacity={0.5}
            cornerRadius={2}
            onMouseEnter={(e) => {
              e.target.opacity(0.9);
              e.target.getStage()!.container().style.cursor = 'col-resize';
              e.target.getLayer()?.batchDraw();
            }}
            onMouseLeave={(e) => {
              e.target.opacity(0.5);
              e.target.getStage()!.container().style.cursor = 'default';
              e.target.getLayer()?.batchDraw();
            }}
            onMouseDown={handleResizeRight}
            onTouchStart={handleResizeRight}
          />

          {/* Bottom edge handle */}
          <Rect
            x={tableWidth / 2 - 16}
            y={tableHeight - HANDLE_SIZE / 2}
            width={32}
            height={HANDLE_SIZE}
            fill="#1a73e8"
            opacity={0.5}
            cornerRadius={2}
            onMouseEnter={(e) => {
              e.target.opacity(0.9);
              e.target.getStage()!.container().style.cursor = 'row-resize';
              e.target.getLayer()?.batchDraw();
            }}
            onMouseLeave={(e) => {
              e.target.opacity(0.5);
              e.target.getStage()!.container().style.cursor = 'default';
              e.target.getLayer()?.batchDraw();
            }}
            onMouseDown={handleResizeBottom}
            onTouchStart={handleResizeBottom}
          />

          {/* Bottom-right corner handle */}
          <Rect
            x={tableWidth - HANDLE_SIZE}
            y={tableHeight - HANDLE_SIZE}
            width={HANDLE_SIZE + 2}
            height={HANDLE_SIZE + 2}
            fill="#1a73e8"
            opacity={0.7}
            cornerRadius={2}
            onMouseEnter={(e) => {
              e.target.opacity(1);
              e.target.getStage()!.container().style.cursor = 'nwse-resize';
              e.target.getLayer()?.batchDraw();
            }}
            onMouseLeave={(e) => {
              e.target.opacity(0.7);
              e.target.getStage()!.container().style.cursor = 'default';
              e.target.getLayer()?.batchDraw();
            }}
            onMouseDown={handleResizeCorner}
            onTouchStart={handleResizeCorner}
          />
        </>
      )}
    </Group>
  );
};

export default DataTableElement;
