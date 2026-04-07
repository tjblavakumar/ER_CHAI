import React from 'react';
import { Group, Line, Rect } from 'react-konva';
import type { SeriesConfig } from '../../types';

interface DataSeriesElementProps {
  series: SeriesConfig[];
  chartArea: { x: number; y: number; width: number; height: number };
  yMin: number;
  yMax: number;
  datasetRows?: Record<string, unknown>[] | null;
}

/**
 * Extract numeric values for a series column from dataset rows.
 */
function extractSeriesData(
  rows: Record<string, unknown>[],
  column: string,
): number[] {
  return rows.map((row) => {
    const val = row[column];
    if (val === null || val === undefined || val === '') return NaN;
    const num = Number(val);
    return isNaN(num) ? NaN : num;
  });
}

/**
 * Fallback: generate placeholder data when no real data is available.
 */
function generatePlaceholderData(seriesName: string, count: number): number[] {
  let seed = 0;
  for (let i = 0; i < seriesName.length; i++) {
    seed += seriesName.charCodeAt(i);
  }
  const data: number[] = [];
  let val = 30 + (seed % 40);
  for (let i = 0; i < count; i++) {
    val += Math.sin(seed + i * 0.7) * 8 + Math.cos(seed * 0.3 + i) * 5;
    val = Math.max(5, Math.min(95, val));
    data.push(val);
  }
  return data;
}

const DataSeriesElement: React.FC<DataSeriesElementProps> = ({
  series,
  chartArea,
  yMin,
  yMax,
  datasetRows,
}) => {
  const { x, y, width, height } = chartArea;
  const yRange = yMax - yMin || 1;

  const visibleSeries = series.filter((s) => s.visible);
  const barSeriesCount = visibleSeries.filter((s) => s.chart_type === 'bar').length;

  let barGroupIndex = 0;

  return (
    <Group>
      {visibleSeries.map((s) => {
        // Use real data if available, otherwise placeholder
        const data =
          datasetRows && datasetRows.length > 0
            ? extractSeriesData(datasetRows, s.column)
            : generatePlaceholderData(s.name, 12);

        const dataCount = data.length;
        // Filter out NaN for valid rendering
        const validData = data.map((v, i) => ({ value: v, index: i })).filter((d) => !isNaN(d.value));

        if (s.chart_type === 'bar') {
          const currentBarIndex = barGroupIndex++;
          const totalBarWidth = width / Math.max(dataCount, 1);
          const singleBarWidth = (totalBarWidth * 0.7) / Math.max(barSeriesCount, 1);
          const barOffset =
            currentBarIndex * singleBarWidth -
            (barSeriesCount * singleBarWidth) / 2 +
            singleBarWidth / 2;

          return (
            <Group key={s.name}>
              {validData.map((d) => {
                const bx =
                  x +
                  (d.index / Math.max(dataCount - 1, 1)) * width +
                  barOffset -
                  singleBarWidth / 2;
                const barHeight = ((d.value - yMin) / yRange) * height;
                const by = y + height - barHeight;
                return (
                  <Rect
                    key={d.index}
                    x={bx}
                    y={by}
                    width={singleBarWidth}
                    height={Math.max(barHeight, 0)}
                    fill={s.color}
                    opacity={0.8}
                  />
                );
              })}
            </Group>
          );
        }

        // Line or area chart
        const points: number[] = [];
        validData.forEach((d) => {
          const px = x + (d.index / Math.max(dataCount - 1, 1)) * width;
          const py = y + height - ((d.value - yMin) / yRange) * height;
          points.push(px, py);
        });

        if (s.chart_type === 'area' && validData.length > 0) {
          // Area chart: closed polygon filled to baseline
          const areaPoints = [...points];
          // Close the polygon along the baseline
          const lastX = x + (validData[validData.length - 1].index / Math.max(dataCount - 1, 1)) * width;
          const firstX = x + (validData[0].index / Math.max(dataCount - 1, 1)) * width;
          areaPoints.push(lastX, y + height); // bottom-right
          areaPoints.push(firstX, y + height); // bottom-left
          return (
            <React.Fragment key={s.name}>
              <Line
                points={areaPoints}
                fill={s.color}
                opacity={0.3}
                closed
              />
              <Line
                points={points}
                stroke={s.color}
                strokeWidth={s.line_width}
                lineCap="round"
                lineJoin="round"
              />
            </React.Fragment>
          );
        }

        return (
          <Line
            key={s.name}
            points={points}
            stroke={s.color}
            strokeWidth={s.line_width}
            lineCap="round"
            lineJoin="round"
          />
        );
      })}
    </Group>
  );
};

export default DataSeriesElement;
