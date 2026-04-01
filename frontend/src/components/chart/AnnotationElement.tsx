import React from 'react';
import { Group, Rect, Text } from 'react-konva';
import type { AnnotationConfig } from '../../types';

interface AnnotationElementProps {
  config: AnnotationConfig;
  chartArea: { x: number; y: number; width: number; height: number };
  draggable?: boolean;
  onDragEnd?: (id: string, x: number, y: number) => void;
  onContextMenu?: (id: string, x: number, y: number) => void;
}

const AnnotationElement: React.FC<AnnotationElementProps> = ({
  config,
  chartArea,
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
      if (pointer) {
        onContextMenu?.(elementId, pointer.x, pointer.y);
      }
    }
  };

  if (config.type === 'vertical_band') {
    // Render a vertical band across the chart area
    const bandWidth = chartArea.width * 0.15; // placeholder width
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
