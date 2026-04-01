import React from 'react';
import { Group, Rect, Text, Line } from 'react-konva';
import type { AnnotationConfig } from '../../types';

interface AnnotationElementProps {
  config: AnnotationConfig;
  chartArea: { x: number; y: number; width: number; height: number };
  yMin?: number;
  yMax?: number;
  draggable?: boolean;
  onDragEnd?: (id: string, x: number, y: number) => void;
  onContextMenu?: (id: string, x: number, y: number) => void;
}

function dashForStyle(style: string): number[] | undefined {
  switch (style) {
    case 'dashed': return [8, 4];
    case 'dotted': return [3, 3];
    default: return undefined;
  }
}

const AnnotationElement: React.FC<AnnotationElementProps> = ({
  config,
  chartArea,
  yMin = 0,
  yMax = 100,
  draggable = true,
  onDragEnd,
  onContextMenu,
}) => {
  const elementId = `annotation_${config.id}`;

  const handleContextMenu = (e: import('konva/lib/Node').KonvaEventObject<MouseEvent>) => {
    e.evt.preventDefault();
    const stage = e.target.getStage();
    if (stage) {
      const pointer = stage.getPointerPosition();
      if (pointer) onContextMenu?.(elementId, pointer.x, pointer.y);
    }
  };

  // Horizontal line at a specific Y value
  if (config.type === 'horizontal_line') {
    const lineVal = config.line_value ?? 0;
    const yRange = yMax - yMin || 1;
    const py = chartArea.y + chartArea.height - ((lineVal - yMin) / yRange) * chartArea.height;
    const dash = dashForStyle(config.line_style ?? 'dotted');
    const label = config.text ?? `${lineVal}`;

    return (
      <Group
        draggable={draggable}
        onDragEnd={(e) => {
          onDragEnd?.(elementId, e.target.x(), e.target.y());
        }}
      >
        <Line
          points={[chartArea.x, py, chartArea.x + chartArea.width, py]}
          stroke={config.line_color ?? '#cc0000'}
          strokeWidth={config.line_width ?? 1.5}
          dash={dash}
        />
        {label && (
          <Text
            x={chartArea.x + chartArea.width + 4}
            y={py - 6}
            text={label}
            fontSize={config.font_size}
            fontFamily="Arial"
            fill={config.line_color ?? '#cc0000'}
          />
        )}
      </Group>
    );
  }

  // Vertical band
  if (config.type === 'vertical_band') {
    const bandWidth = chartArea.width * 0.15;
    return (
      <Group
        x={config.position.x}
        y={chartArea.y}
        draggable={draggable}
        onDragEnd={(e) => {
          onDragEnd?.(elementId, e.target.x(), e.target.y());
        }}
      >
        <Rect
          width={bandWidth}
          height={chartArea.height}
          fill={config.band_color ?? '#cccccc'}
          opacity={0.3}
        />
      </Group>
    );
  }

  // Text annotation
  return (
    <Group
      x={config.position.x}
      y={config.position.y}
      draggable={draggable}
      onDragEnd={(e) => {
        onDragEnd?.(elementId, e.target.x(), e.target.y());
      }}
      onContextMenu={handleContextMenu}
    >
      <Text
        text={config.text ?? ''}
        fontSize={config.font_size}
        fontFamily="Arial"
        fill={config.font_color}
      />
    </Group>
  );
};

export default AnnotationElement;
