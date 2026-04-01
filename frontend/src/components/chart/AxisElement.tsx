import React from 'react';
import { Group, Line, Text } from 'react-konva';
import type { AxesConfig } from '../../types';

interface AxisElementProps {
  config: AxesConfig;
  chartArea: { x: number; y: number; width: number; height: number };
  draggable?: boolean;
  xLabels?: string[];
  onDragEnd?: (id: string, x: number, y: number) => void;
  onContextMenu?: (id: string, x: number, y: number) => void;
}

const TICK_COUNT = 5;
const TICK_SIZE = 6;

function formatYTick(val: number, format: string): string {
  switch (format) {
    case 'integer':
      return Math.round(val).toString();
    case 'percent':
      return `${Math.round(val)}%`;
    case 'decimal1':
      return val.toFixed(1);
    case 'decimal2':
      return val.toFixed(2);
    default: {
      if (Math.abs(val) >= 10) return Math.round(val).toString();
      return val.toFixed(1);
    }
  }
}

/** Shorten a date string for x-axis display */
function shortenDate(s: string): string {
  // "2020-01-01" → "2020-01"
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 7);
  return s;
}

const AxisElement: React.FC<AxisElementProps> = ({
  config,
  chartArea,
  draggable = true,
  xLabels,
  onDragEnd,
  onContextMenu,
}) => {
  const { x, y, width, height } = chartArea;
  const axisLineWidth = config.line_width ?? 1;
  const tickFontSize = config.tick_font_size ?? 10;
  const labelFontSize = config.label_font_size ?? 12;
  const yFormat = config.y_format ?? 'auto';

  // Y-axis tick values
  const yMin = config.y_min ?? 0;
  const yMax = config.y_max ?? 100;
  const yTicks: number[] = [];
  for (let i = 0; i <= TICK_COUNT; i++) {
    yTicks.push(yMin + ((yMax - yMin) * i) / TICK_COUNT);
  }

  // X-axis numeric ticks (fallback when no xLabels)
  const xMin = config.x_min ?? 0;
  const xMax = config.x_max ?? 100;
  const xTicks: number[] = [];
  for (let i = 0; i <= TICK_COUNT; i++) {
    xTicks.push(xMin + ((xMax - xMin) * i) / TICK_COUNT);
  }

  const handleCtx = (id: string) => (e: import('konva/lib/Node').KonvaEventObject<MouseEvent>) => {
    e.evt.preventDefault();
    const stage = e.target.getStage();
    if (stage) {
      const pointer = stage.getPointerPosition();
      if (pointer) onContextMenu?.(id, pointer.x, pointer.y);
    }
  };

  // X-axis label spacing
  const xLabelWidth = Math.max(60, width / (TICK_COUNT + 1));

  return (
    <Group>
      {/* Y-axis line */}
      <Line points={[x, y, x, y + height]} stroke="#333" strokeWidth={axisLineWidth} />
      {/* X-axis line */}
      <Line points={[x, y + height, x + width, y + height]} stroke="#333" strokeWidth={axisLineWidth} />

      {/* Y-axis ticks and labels */}
      {yTicks.map((val, i) => {
        const ty = y + height - (i / TICK_COUNT) * height;
        return (
          <Group key={`ytick-${i}`}>
            <Line points={[x - TICK_SIZE, ty, x, ty]} stroke="#333" strokeWidth={axisLineWidth} />
            <Text
              x={x - 60}
              y={ty - tickFontSize / 2}
              text={formatYTick(val, yFormat)}
              fontSize={tickFontSize}
              fontFamily="Arial"
              fill="#333"
              width={54}
              align="right"
            />
          </Group>
        );
      })}

      {/* X-axis ticks and labels */}
      {xLabels && xLabels.length > 0
        ? Array.from({ length: TICK_COUNT + 1 }, (_, i) => {
            const idx = Math.round((i / TICK_COUNT) * (xLabels.length - 1));
            const label = shortenDate(xLabels[idx] ?? '');
            const tx = x + (i / TICK_COUNT) * width;
            return (
              <Group key={`xtick-${i}`}>
                <Line points={[tx, y + height, tx, y + height + TICK_SIZE]} stroke="#333" strokeWidth={axisLineWidth} />
                <Text
                  x={tx - xLabelWidth / 2}
                  y={y + height + TICK_SIZE + 2}
                  text={label}
                  fontSize={tickFontSize}
                  fontFamily="Arial"
                  fill="#333"
                  width={xLabelWidth}
                  align="center"
                />
              </Group>
            );
          })
        : xTicks.map((val, i) => {
            const tx = x + (i / TICK_COUNT) * width;
            return (
              <Group key={`xtick-${i}`}>
                <Line points={[tx, y + height, tx, y + height + TICK_SIZE]} stroke="#333" strokeWidth={axisLineWidth} />
                <Text
                  x={tx - xLabelWidth / 2}
                  y={y + height + TICK_SIZE + 2}
                  text={val.toFixed(1)}
                  fontSize={tickFontSize}
                  fontFamily="Arial"
                  fill="#333"
                  width={xLabelWidth}
                  align="center"
                />
              </Group>
            );
          })}

      {/* Y-axis label */}
      <Group
        draggable={draggable}
        onDragEnd={(e) => onDragEnd?.('y_label', e.target.x(), e.target.y())}
        onContextMenu={handleCtx('y_label')}
      >
        <Text
          x={x - 70}
          y={y + height / 2 + 30}
          text={config.y_label}
          fontSize={labelFontSize}
          fontFamily="Arial"
          fill="#333"
          rotation={-90}
        />
      </Group>

      {/* X-axis label */}
      <Group
        draggable={draggable}
        onDragEnd={(e) => onDragEnd?.('x_label', e.target.x(), e.target.y())}
        onContextMenu={handleCtx('x_label')}
      >
        <Text
          x={x + width / 2 - 30}
          y={y + height + 35}
          text={config.x_label}
          fontSize={labelFontSize}
          fontFamily="Arial"
          fill="#333"
        />
      </Group>
    </Group>
  );
};

export default AxisElement;
