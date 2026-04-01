import React from 'react';
import { Group, Line, Text } from 'react-konva';
import type { AxesConfig } from '../../types';

interface AxisElementProps {
  config: AxesConfig;
  chartArea: { x: number; y: number; width: number; height: number };
  draggable?: boolean;
  onDragEnd?: (id: string, x: number, y: number) => void;
  onContextMenu?: (id: string, x: number, y: number) => void;
}

const TICK_COUNT = 5;
const TICK_SIZE = 6;

const AxisElement: React.FC<AxisElementProps> = ({
  config,
  chartArea,
  draggable = true,
  onDragEnd,
  onContextMenu,
}) => {
  const { x, y, width, height } = chartArea;

  // Compute Y-axis tick values
  const yMin = config.y_min ?? 0;
  const yMax = config.y_max ?? 100;
  const yTicks: number[] = [];
  for (let i = 0; i <= TICK_COUNT; i++) {
    yTicks.push(yMin + ((yMax - yMin) * i) / TICK_COUNT);
  }

  // Compute X-axis tick labels
  const xMin = config.x_min ?? 0;
  const xMax = config.x_max ?? 100;
  const xTicks: number[] = [];
  for (let i = 0; i <= TICK_COUNT; i++) {
    xTicks.push(xMin + ((xMax - xMin) * i) / TICK_COUNT);
  }

  const handleContextMenu = (id: string) => (e: import('konva/lib/Node').KonvaEventObject<MouseEvent>) => {
    e.evt.preventDefault();
    const stage = e.target.getStage();
    if (stage) {
      const pointer = stage.getPointerPosition();
      if (pointer) {
        onContextMenu?.(id, pointer.x, pointer.y);
      }
    }
  };

  return (
    <Group>
      {/* Y-axis line */}
      <Line points={[x, y, x, y + height]} stroke="#333" strokeWidth={1} />

      {/* X-axis line */}
      <Line points={[x, y + height, x + width, y + height]} stroke="#333" strokeWidth={1} />

      {/* Y-axis ticks and labels */}
      {yTicks.map((val, i) => {
        const ty = y + height - (i / TICK_COUNT) * height;
        return (
          <Group key={`ytick-${i}`}>
            <Line points={[x - TICK_SIZE, ty, x, ty]} stroke="#333" strokeWidth={1} />
            <Text
              x={x - 45}
              y={ty - 6}
              text={val.toFixed(1)}
              fontSize={10}
              fontFamily="Arial"
              fill="#333"
              width={38}
              align="right"
            />
          </Group>
        );
      })}

      {/* X-axis ticks and labels */}
      {xTicks.map((val, i) => {
        const tx = x + (i / TICK_COUNT) * width;
        return (
          <Group key={`xtick-${i}`}>
            <Line points={[tx, y + height, tx, y + height + TICK_SIZE]} stroke="#333" strokeWidth={1} />
            <Text
              x={tx - 20}
              y={y + height + TICK_SIZE + 2}
              text={val.toFixed(1)}
              fontSize={10}
              fontFamily="Arial"
              fill="#333"
              width={40}
              align="center"
            />
          </Group>
        );
      })}

      {/* Y-axis label */}
      <Group
        draggable={draggable}
        onDragEnd={(e) => onDragEnd?.('y_label', e.target.x(), e.target.y())}
        onContextMenu={handleContextMenu('y_label')}
      >
        <Text
          x={x - 60}
          y={y + height / 2 + 30}
          text={config.y_label}
          fontSize={12}
          fontFamily="Arial"
          fill="#333"
          rotation={-90}
        />
      </Group>

      {/* X-axis label */}
      <Group
        draggable={draggable}
        onDragEnd={(e) => onDragEnd?.('x_label', e.target.x(), e.target.y())}
        onContextMenu={handleContextMenu('x_label')}
      >
        <Text
          x={x + width / 2 - 30}
          y={y + height + 30}
          text={config.x_label}
          fontSize={12}
          fontFamily="Arial"
          fill="#333"
        />
      </Group>
    </Group>
  );
};

export default AxisElement;
