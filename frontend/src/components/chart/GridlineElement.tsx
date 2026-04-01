import React from 'react';
import { Group, Line } from 'react-konva';
import type { GridlineConfig } from '../../types';

interface GridlineElementProps {
  config: GridlineConfig;
  chartArea: { x: number; y: number; width: number; height: number };
  draggable?: boolean;
  onDragEnd?: (id: string, x: number, y: number) => void;
}

const GRID_COUNT = 5;

function dashForStyle(style: string): number[] | undefined {
  switch (style) {
    case 'dashed':
      return [6, 4];
    case 'dotted':
      return [2, 3];
    default:
      return undefined;
  }
}

const GridlineElement: React.FC<GridlineElementProps> = ({
  config,
  chartArea,
  draggable = true,
  onDragEnd,
}) => {
  const { x, y, width, height } = chartArea;
  const dash = dashForStyle(config.style);

  return (
    <Group
      draggable={draggable}
      onDragEnd={(e) => {
        onDragEnd?.('gridlines', e.target.x(), e.target.y());
      }}
    >
      {/* Horizontal gridlines */}
      {config.horizontal_visible &&
        Array.from({ length: GRID_COUNT - 1 }, (_, i) => {
          const gy = y + ((i + 1) / GRID_COUNT) * height;
          return (
            <Line
              key={`h-${i}`}
              points={[x, gy, x + width, gy]}
              stroke={config.color}
              strokeWidth={0.5}
              dash={dash}
            />
          );
        })}

      {/* Vertical gridlines */}
      {config.vertical_visible &&
        Array.from({ length: GRID_COUNT - 1 }, (_, i) => {
          const gx = x + ((i + 1) / GRID_COUNT) * width;
          return (
            <Line
              key={`v-${i}`}
              points={[gx, y, gx, y + height]}
              stroke={config.color}
              strokeWidth={0.5}
              dash={dash}
            />
          );
        })}
    </Group>
  );
};

export default GridlineElement;
