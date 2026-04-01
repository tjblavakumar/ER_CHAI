import React from 'react';
import { Group, Rect, Text, Line } from 'react-konva';
import type { DataTableConfig } from '../../types';

interface DataTableElementProps {
  config: DataTableConfig;
  draggable?: boolean;
  onDragEnd?: (id: string, x: number, y: number) => void;
  onContextMenu?: (id: string, x: number, y: number) => void;
}

const COL_WIDTH = 90;
const ROW_HEIGHT = 22;
const HEADER_HEIGHT = 24;
const PLACEHOLDER_ROWS = 3;

const DataTableElement: React.FC<DataTableElementProps> = ({
  config,
  draggable = true,
  onDragEnd,
  onContextMenu,
}) => {
  if (!config.visible || config.columns.length === 0) return null;

  const tableWidth = config.columns.length * COL_WIDTH;
  const tableHeight = HEADER_HEIGHT + PLACEHOLDER_ROWS * ROW_HEIGHT;

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
      <Rect
        width={tableWidth}
        height={tableHeight}
        fill="#fff"
        stroke="#999"
        strokeWidth={1}
      />

      {/* Header row background */}
      <Rect
        width={tableWidth}
        height={HEADER_HEIGHT}
        fill="#e8e8e8"
      />

      {/* Column headers */}
      {config.columns.map((col, i) => (
        <Text
          key={`header-${col}`}
          x={i * COL_WIDTH + 4}
          y={5}
          text={col}
          fontSize={config.font_size}
          fontFamily="Arial"
          fontStyle="bold"
          fill="#333"
          width={COL_WIDTH - 8}
          ellipsis
        />
      ))}

      {/* Header separator */}
      <Line
        points={[0, HEADER_HEIGHT, tableWidth, HEADER_HEIGHT]}
        stroke="#999"
        strokeWidth={1}
      />

      {/* Placeholder data rows */}
      {Array.from({ length: PLACEHOLDER_ROWS }, (_, row) =>
        config.columns.map((col, colIdx) => (
          <Text
            key={`cell-${row}-${col}`}
            x={colIdx * COL_WIDTH + 4}
            y={HEADER_HEIGHT + row * ROW_HEIGHT + 4}
            text="—"
            fontSize={config.font_size}
            fontFamily="Arial"
            fill="#888"
            width={COL_WIDTH - 8}
          />
        )),
      )}

      {/* Row separators */}
      {Array.from({ length: PLACEHOLDER_ROWS - 1 }, (_, i) => {
        const ry = HEADER_HEIGHT + (i + 1) * ROW_HEIGHT;
        return (
          <Line
            key={`row-sep-${i}`}
            points={[0, ry, tableWidth, ry]}
            stroke="#ddd"
            strokeWidth={0.5}
          />
        );
      })}
    </Group>
  );
};

export default DataTableElement;
