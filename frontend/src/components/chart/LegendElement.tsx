import React from 'react';
import { Group, Rect, Text } from 'react-konva';
import type { LegendConfig } from '../../types';

interface LegendElementProps {
  config: LegendConfig;
  draggable?: boolean;
  onDragEnd?: (id: string, x: number, y: number) => void;
  onContextMenu?: (id: string, x: number, y: number) => void;
}

const SWATCH_SIZE = 12;
const ENTRY_GAP = 18;
const PADDING = 8;

const LegendElement: React.FC<LegendElementProps> = ({
  config,
  draggable = true,
  onDragEnd,
  onContextMenu,
}) => {
  if (!config.visible || config.entries.length === 0) return null;

  const entryWidth = 100;
  const totalWidth = config.entries.length * entryWidth + PADDING * 2;
  const totalHeight = ENTRY_GAP + PADDING * 2;

  return (
    <Group
      x={config.position.x}
      y={config.position.y}
      draggable={draggable}
      onDragEnd={(e) => {
        onDragEnd?.('legend', e.target.x(), e.target.y());
      }}
      onContextMenu={(e) => {
        e.evt.preventDefault();
        const stage = e.target.getStage();
        if (stage) {
          const pointer = stage.getPointerPosition();
          if (pointer) {
            onContextMenu?.('legend', pointer.x, pointer.y);
          }
        }
      }}
    >
      {/* Background */}
      <Rect
        width={totalWidth}
        height={totalHeight}
        fill="#ffffff"
        stroke="#ccc"
        strokeWidth={1}
        cornerRadius={3}
      />

      {/* Entries */}
      {config.entries.map((entry, i) => (
        <Group key={entry.series_name} x={PADDING + i * entryWidth} y={PADDING}>
          <Rect
            width={SWATCH_SIZE}
            height={SWATCH_SIZE}
            fill={entry.color}
            y={2}
          />
          <Text
            x={SWATCH_SIZE + 4}
            text={entry.label}
            fontSize={11}
            fontFamily="Arial"
            fill="#333"
          />
        </Group>
      ))}
    </Group>
  );
};

export default LegendElement;
