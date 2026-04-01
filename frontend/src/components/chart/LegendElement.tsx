import React from 'react';
import { Group, Rect, Text } from 'react-konva';
import type { LegendConfig, Position } from '../../types';

interface LegendElementProps {
  config: LegendConfig;
  elementsPositions?: Record<string, Position>;
  draggable?: boolean;
  onDragEnd?: (id: string, x: number, y: number) => void;
  onContextMenu?: (id: string, x: number, y: number) => void;
}

const SWATCH_SIZE = 12;
const ENTRY_SPACING_Y = 22;

const LegendElement: React.FC<LegendElementProps> = ({
  config,
  elementsPositions,
  draggable = true,
  onDragEnd,
  onContextMenu,
}) => {
  if (!config.visible || config.entries.length === 0) return null;

  return (
    <>
      {config.entries.map((entry, i) => {
        const entryId = `legend_entry_${entry.series_name}`;
        // Resolve position: per-entry override, or stacked from legend position
        const pos = elementsPositions?.[entryId] ?? {
          x: config.position.x,
          y: config.position.y + i * ENTRY_SPACING_Y,
        };

        return (
          <Group
            key={entryId}
            x={pos.x}
            y={pos.y}
            draggable={draggable}
            onDragEnd={(e) => {
              onDragEnd?.(entryId, e.target.x(), e.target.y());
            }}
            onContextMenu={(e) => {
              e.evt.preventDefault();
              const stage = e.target.getStage();
              if (stage) {
                const pointer = stage.getPointerPosition();
                if (pointer) {
                  onContextMenu?.(entryId, pointer.x, pointer.y);
                }
              }
            }}
          >
            <Rect
              width={SWATCH_SIZE}
              height={SWATCH_SIZE}
              fill={entry.color}
              y={1}
            />
            <Text
              x={SWATCH_SIZE + 4}
              text={entry.label}
              fontSize={entry.font_size ?? 11}
              fontFamily={entry.font_family ?? 'Arial'}
              fill={entry.font_color ?? '#333'}
            />
          </Group>
        );
      })}
    </>
  );
};

export default LegendElement;
