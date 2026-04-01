import React from 'react';
import { Group, Line, Rect } from 'react-konva';
import type { SeriesConfig } from '../../types';

interface DataSeriesElementProps {
  series: SeriesConfig[];
  chartArea: { x: number; y: number; width: number; height: number };
  yMin: number;
  yMax: number;
}

/**
 * Generates placeholder data points for a series.
 * Uses a deterministic seed based on series name so each series looks different.
 */
function generatePlaceholderData(seriesName: string, count: number): number[] {
  let seed = 0;
  for (let i = 0; i < seriesName.length; i++) {
    seed += seriesName.charCodeAt(i);
  }
  const data: number[] = [];
  let val = 30 + (seed % 40);
  for (let i = 0; i < count; i++) {
    // Simple pseudo-random walk
    val += Math.sin(seed + i * 0.7) * 8 + Math.cos(seed * 0.3 + i) * 5;
    val = Math.max(5, Math.min(95, val));
    data.push(val);
  }
  return data;
}

const DATA_POINT_COUNT = 12;

const DataSeriesElement: React.FC<DataSeriesElementProps> = ({
  series,
  chartArea,
  yMin,
  yMax,
}) => {
  const { x, y, width, height } = chartArea;
  const yRange = yMax - yMin || 1;

  const visibleSeries = series.filter((s) => s.visible);
  const barSeriesCount = visibleSeries.filter((s) => s.chart_type === 'bar').length;

  let barGroupIndex = 0;

  return (
    <Group>
      {visibleSeries.map((s) => {
        const data = generatePlaceholderData(s.name, DATA_POINT_COUNT);

        if (s.chart_type === 'bar') {
          const currentBarIndex = barGroupIndex++;
          const totalBarWidth = width / DATA_POINT_COUNT;
          const singleBarWidth = (totalBarWidth * 0.7) / Math.max(barSeriesCount, 1);
          const barOffset = currentBarIndex * singleBarWidth - (barSeriesCount * singleBarWidth) / 2 + singleBarWidth / 2;

          return (
            <Group key={s.name}>
              {data.map((val, i) => {
                const bx = x + (i / (DATA_POINT_COUNT - 1)) * width + barOffset - singleBarWidth / 2;
                const barHeight = ((val - yMin) / yRange) * height;
                const by = y + height - barHeight;
                return (
                  <Rect
                    key={i}
                    x={bx}
                    y={by}
                    width={singleBarWidth}
                    height={barHeight}
                    fill={s.color}
                    opacity={0.8}
                  />
                );
              })}
            </Group>
          );
        }

        // Line chart
        const points: number[] = [];
        data.forEach((val, i) => {
          const px = x + (i / (DATA_POINT_COUNT - 1)) * width;
          const py = y + height - ((val - yMin) / yRange) * height;
          points.push(px, py);
        });

        return (
          <Line
            key={s.name}
            points={points}
            stroke={s.color}
            strokeWidth={s.line_width}
            lineCap="round"
            lineJoin="round"
            tension={0.3}
          />
        );
      })}
    </Group>
  );
};

export default DataSeriesElement;
