import React from 'react';
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
}

const SERIES_COL_WIDTH = 120;
const DATE_COL_WIDTH = 70;
const ROW_HEIGHT = 22;
const HEADER_HEIGHT = 24;

const formatCellValue = (value: unknown): string => {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') return value.toFixed(2);
  return String(value);
};

const formatDateHeader = (value: unknown): string => {
  if (value === null || value === undefined) return '';
  const s = String(value);
  // Shorten ISO dates like "2020-01-01" to "Jan 20" style
  const d = new Date(s);
  if (!isNaN(d.getTime())) {
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${months[d.getMonth()]} ${String(d.getFullYear()).slice(2)}`;
  }
  return s.length > 8 ? s.slice(0, 8) : s;
};

/**
 * Transposed data table for time series:
 * - Rows = data series (using legend labels)
 * - Columns = evenly sampled dates
 */
const DataTableElement: React.FC<DataTableElementProps> = ({
  config,
  datasetRows,
  seriesLabels,
  seriesColors,
  draggable = true,
  onDragEnd,
  onContextMenu,
}) => {
  if (!config.visible || config.columns.length === 0) return null;

  const maxDateCols = config.max_rows ?? 5;
  const hasData = datasetRows && datasetRows.length > 0;

  // Detect date column (first string/non-numeric column)
  let dateColumn: string | null = null;
  if (hasData) {
    const firstRow = datasetRows[0];
    dateColumn = Object.keys(firstRow).find((key) => {
      const val = firstRow[key];
      return typeof val === 'string' && isNaN(Number(val));
    }) ?? null;
  }

  // Sample evenly spaced date indices
  const totalRows = hasData ? datasetRows.length : 0;
  const sampledIndices: number[] = [];
  if (totalRows > 0 && maxDateCols > 0) {
    const count = Math.min(maxDateCols, totalRows);
    for (let i = 0; i < count; i++) {
      sampledIndices.push(Math.round((i * (totalRows - 1)) / Math.max(count - 1, 1)));
    }
  }

  const dateHeaders = sampledIndices.map((idx) =>
    dateColumn && hasData ? formatDateHeader(datasetRows[idx][dateColumn]) : `Col ${idx}`,
  );

  const seriesCols = config.columns; // numeric series column names
  const computedCols = config.computed_columns ?? [];
  const computedValues = config.computed_values ?? {};
  const numDateCols = dateHeaders.length;
  const numRows = seriesCols.length;

  const tableWidth = SERIES_COL_WIDTH + (numDateCols + computedCols.length) * DATE_COL_WIDTH;
  const tableHeight = HEADER_HEIGHT + numRows * ROW_HEIGHT;

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
        width={SERIES_COL_WIDTH - 8}
        ellipsis
      />

      {/* Date column headers */}
      {dateHeaders.map((header, i) => (
        <Text
          key={`dh-${i}`}
          x={SERIES_COL_WIDTH + i * DATE_COL_WIDTH + 4}
          y={5}
          text={header}
          fontSize={config.font_size}
          fontFamily="Arial"
          fontStyle="bold"
          fill="#333"
          width={DATE_COL_WIDTH - 8}
          ellipsis
        />
      ))}

      {/* Computed column headers */}
      {computedCols.map((cc, i) => (
        <Text
          key={`cch-${i}`}
          x={SERIES_COL_WIDTH + (numDateCols + i) * DATE_COL_WIDTH + 4}
          y={5}
          text={cc.label}
          fontSize={config.font_size}
          fontFamily="Arial"
          fontStyle="bold"
          fill="#333"
          width={DATE_COL_WIDTH - 8}
          ellipsis
        />
      ))}

      {/* Header separator */}
      <Line points={[0, HEADER_HEIGHT, tableWidth, HEADER_HEIGHT]} stroke="#999" strokeWidth={1} />

      {/* Data rows: one per series */}
      {seriesCols.map((col, rowIdx) => {
        const label = seriesLabels?.[col] ?? col;
        return (
          <React.Fragment key={`row-${col}`}>
            {/* Series name cell */}
            <Text
              x={4}
              y={HEADER_HEIGHT + rowIdx * ROW_HEIGHT + 4}
              text={label}
              fontSize={config.font_size}
              fontFamily="Arial"
              fontStyle="bold"
              fill={seriesColors?.[col] ?? "#333"}
              width={SERIES_COL_WIDTH - 8}
              ellipsis
            />
            {/* Value cells at sampled dates */}
            {sampledIndices.map((dataIdx, colIdx) => (
              <Text
                key={`cell-${rowIdx}-${colIdx}`}
                x={SERIES_COL_WIDTH + colIdx * DATE_COL_WIDTH + 4}
                y={HEADER_HEIGHT + rowIdx * ROW_HEIGHT + 4}
                text={hasData ? formatCellValue(datasetRows[dataIdx][col]) : '—'}
                fontSize={config.font_size}
                fontFamily="Arial"
                fill={seriesColors?.[seriesCols[rowIdx]] ?? "#333"}
                width={DATE_COL_WIDTH - 8}
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
                  x={SERIES_COL_WIDTH + (numDateCols + ccIdx) * DATE_COL_WIDTH + 4}
                  y={HEADER_HEIGHT + rowIdx * ROW_HEIGHT + 4}
                  text={val != null ? val.toFixed(2) : '—'}
                  fontSize={config.font_size}
                  fontFamily="Arial"
                  fill={seriesColors?.[col] ?? "#333"}
                  width={DATE_COL_WIDTH - 8}
                  ellipsis
                />
              );
            })}
          </React.Fragment>
        );
      })}

      {/* Row separators */}
      {Array.from({ length: numRows - 1 }, (_, i) => {
        const ry = HEADER_HEIGHT + (i + 1) * ROW_HEIGHT;
        return (
          <Line key={`row-sep-${i}`} points={[0, ry, tableWidth, ry]} stroke="#ddd" strokeWidth={0.5} />
        );
      })}
    </Group>
  );
};

export default DataTableElement;
