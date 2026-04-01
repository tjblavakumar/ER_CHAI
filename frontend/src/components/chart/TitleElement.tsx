import React from 'react';
import { Group, Text } from 'react-konva';
import type { ChartElementState } from '../../types';

interface TitleElementProps {
  config: ChartElementState;
  elementId: string;
  draggable?: boolean;
  onDragEnd?: (id: string, x: number, y: number) => void;
  onContextMenu?: (id: string, x: number, y: number) => void;
}

const TitleElement: React.FC<TitleElementProps> = ({
  config,
  elementId,
  draggable = true,
  onDragEnd,
  onContextMenu,
}) => {
  return (
    <Group
      x={config.position.x}
      y={config.position.y}
      draggable={draggable}
      onDragEnd={(e) => {
        const node = e.target;
        onDragEnd?.(elementId, node.x(), node.y());
      }}
      onContextMenu={(e) => {
        e.evt.preventDefault();
        const stage = e.target.getStage();
        if (stage) {
          const pointer = stage.getPointerPosition();
          if (pointer) {
            onContextMenu?.(elementId, pointer.x, pointer.y);
          }
        }
      }}
    >
      <Text
        text={config.text}
        fontSize={config.font_size}
        fontFamily={config.font_family}
        fill={config.font_color}
        fontStyle="bold"
      />
    </Group>
  );
};

export default TitleElement;
